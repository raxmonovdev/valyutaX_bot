import logging
import time

import requests

from config import API_TIMEOUT, API_URL, CACHE_TTL_SECONDS

log = logging.getLogger(__name__)

UNAVAILABLE = "⏳ Hozir kurslarni olib bo'lmadi. Birozdan keyin urinib ko'ring."


class RateServiceError(Exception):
    pass


class CurrencyNotFound(Exception):
    pass


class MemoryRateCache:
    def __init__(self):
        self._data: dict[str, tuple[float, dict, str]] = {}

    def get(self, base: str, ttl: int):
        cached = self._data.get(base)
        if not cached:
            return None
        fetched_at, rates, updated = cached
        if time.monotonic() - fetched_at >= ttl:
            return None
        return rates, updated

    def put(self, base: str, rates: dict, updated: str) -> None:
        self._data[base] = (time.monotonic(), rates, updated)


class RateService:
    def __init__(self, timeout: float = API_TIMEOUT, ttl: int = CACHE_TTL_SECONDS, cache=None):
        self.timeout = timeout
        self.ttl = ttl
        self.cache = cache if cache is not None else MemoryRateCache()

    def get_rates(self, base: str) -> tuple[dict, str]:
        base = base.upper()
        cached = self.cache.get(base, self.ttl)
        if cached:
            return cached

        try:
            response = requests.get(API_URL.format(base=base), timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            log.exception("Kurs API so'rovi muvaffaqiyatsiz: %s", base)
            raise RateServiceError(UNAVAILABLE) from exc

        if data.get("result") != "success" or not isinstance(data.get("rates"), dict):
            if data.get("error-type") == "unsupported-code":
                raise CurrencyNotFound(base)
            log.error("Kurs API kutilmagan javob: %s", data)
            raise RateServiceError(UNAVAILABLE)

        updated = str(data.get("time_last_update_utc") or "")
        self.cache.put(base, data["rates"], updated)
        return data["rates"], updated

    def convert(self, amount: float, from_cur: str, to_cur: str) -> tuple[float, str]:
        rates, updated = self.get_rates(from_cur)
        rate = rates.get(to_cur)
        if rate is None:
            raise CurrencyNotFound(to_cur)
        return amount * float(rate), updated
