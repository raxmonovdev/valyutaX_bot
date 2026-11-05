import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import mysql.connector

from config import (
    CACHE_TTL_SECONDS,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
    SCHEMA_PATH,
)

log = logging.getLogger(__name__)


def connect():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        autocommit=True,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
        connection_timeout=10,
    )


@contextmanager
def connection():
    conn = connect()
    try:
        cursor = conn.cursor()
        cursor.execute("SET time_zone = '+00:00'")
        cursor.close()
        yield conn
    finally:
        conn.close()


def init_schema() -> None:
    script = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = []
    for chunk in script.split(";"):
        lines = [line for line in chunk.splitlines() if not line.strip().startswith("--")]
        statement = "\n".join(lines).strip()
        if statement:
            statements.append(statement)
    with connection() as conn:
        cursor = conn.cursor()
        try:
            for statement in statements:
                cursor.execute(statement)
        finally:
            cursor.close()


def wait_until_ready(attempts: int = 30, delay: float = 2) -> None:
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            init_schema()
            log.info("MySQL tayyor: %s:%s/%s", MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE)
            return
        except mysql.connector.Error as exc:
            last_error = exc
            log.warning("MySQL kutilmoqda (%s/%s): %s", attempt, attempts, exc)
            time.sleep(delay)
    raise SystemExit(f"MySQL ga ulanib bo'lmadi: {last_error}")


def upsert_user(telegram_id: int, username: str | None, first_name: str | None) -> None:
    sql = """
        INSERT INTO users (telegram_id, username, first_name)
        VALUES (%s, %s, %s) AS new
        ON DUPLICATE KEY UPDATE
            username = new.username,
            first_name = new.first_name,
            last_seen_at = CURRENT_TIMESTAMP
    """
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, (telegram_id, username, first_name))
        finally:
            cursor.close()


def save_conversion(telegram_id: int, amount: float, from_code: str, to_code: str, result: float) -> None:
    sql = """
        INSERT INTO conversions (telegram_id, amount, from_code, to_code, result)
        VALUES (%s, %s, %s, %s, %s)
    """
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, (telegram_id, amount, from_code, to_code, result))
        finally:
            cursor.close()


def recent_conversions(telegram_id: int, limit: int = 5) -> list[dict]:
    sql = """
        SELECT amount, from_code, to_code, result, created_at
        FROM conversions
        WHERE telegram_id = %s
        ORDER BY id DESC
        LIMIT %s
    """
    with connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(sql, (telegram_id, limit))
            return list(cursor.fetchall())
        finally:
            cursor.close()


def _as_rates(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode()
    return json.loads(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MysqlRateCache:
    def get(self, base: str, ttl: int = CACHE_TTL_SECONDS):
        sql = """
            SELECT rates_json, source_updated_at, fetched_at
            FROM rate_cache
            WHERE base_code = %s
        """
        try:
            with connection() as conn:
                cursor = conn.cursor(dictionary=True)
                try:
                    cursor.execute(sql, (base,))
                    row = cursor.fetchone()
                finally:
                    cursor.close()
        except mysql.connector.Error:
            log.exception("Kurs keshini o'qib bo'lmadi: %s", base)
            return None
        if not row or not row.get("fetched_at"):
            return None
        fetched_at = row["fetched_at"]
        if getattr(fetched_at, "tzinfo", None) is not None:
            fetched_at = fetched_at.astimezone(timezone.utc).replace(tzinfo=None)
        if _utc_now() - fetched_at > timedelta(seconds=ttl):
            return None
        return _as_rates(row["rates_json"]), str(row["source_updated_at"] or "")

    def put(self, base: str, rates: dict, updated: str) -> None:
        sql = """
            INSERT INTO rate_cache (base_code, rates_json, source_updated_at, fetched_at)
            VALUES (%s, %s, %s, UTC_TIMESTAMP()) AS new
            ON DUPLICATE KEY UPDATE
                rates_json = new.rates_json,
                source_updated_at = new.source_updated_at,
                fetched_at = UTC_TIMESTAMP()
        """
        try:
            with connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(sql, (base, json.dumps(rates), updated))
                finally:
                    cursor.close()
        except mysql.connector.Error:
            log.exception("Kurs keshini yozib bo'lmadi: %s", base)
