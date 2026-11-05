import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def load_env(path: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None
    if load_dotenv is not None:
        load_dotenv(path)
        return
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_env(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "600"))
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "10"))

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "currency_bot")
MYSQL_USER = os.getenv("MYSQL_USER", "currency")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "currency_pass")

POPULAR = ("USD", "EUR", "RUB", "UZS", "GBP", "CNY")
API_URL = "https://open.er-api.com/v6/latest/{base}"
SCHEMA_PATH = BASE_DIR / "schema.sql"
