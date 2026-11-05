import math
import re

CURRENCY_RE = re.compile(r"^[A-Za-z]{3}$")

FORMAT_CONVERT = "📝 Format: /convert 100 USD UZS"
FORMAT_RATE = "📝 Format: /rate USD yoki /rate Yaponiya"
AMOUNT_ERROR = "⚠️ Miqdor musbat son bo'lishi kerak."
CURRENCY_ERROR = "❗ Valyuta kodi noto'g'ri. /currencies bilan ro'yxatni ko'ring."


class UserInputError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class ConversionRequest:
    def __init__(self, amount: float, from_cur: str, to_cur: str):
        self.amount = amount
        self.from_cur = from_cur
        self.to_cur = to_cur


def parse_amount(raw: str) -> float:
    text = raw.strip().replace(" ", "")
    if text.count(",") > 1 or ("," in text and "." in text):
        raise UserInputError(AMOUNT_ERROR)
    if "," in text:
        text = text.replace(",", ".")
    try:
        value = float(text)
    except ValueError as exc:
        raise UserInputError(AMOUNT_ERROR) from exc
    if not math.isfinite(value) or value <= 0:
        raise UserInputError(AMOUNT_ERROR)
    return value


def parse_currency(raw: str) -> str:
    code = raw.strip()
    if not CURRENCY_RE.fullmatch(code):
        raise UserInputError(CURRENCY_ERROR)
    return code.upper()


def _strip_command(parts: list[str], command: str) -> list[str]:
    if parts and parts[0].split("@", 1)[0].lower() == command:
        return parts[1:]
    return parts


def parse_convert(text: str) -> ConversionRequest:
    parts = _strip_command(text.strip().split(), "/convert")
    if len(parts) != 3:
        raise UserInputError(FORMAT_CONVERT)
    return ConversionRequest(
        parse_amount(parts[0]),
        parse_currency(parts[1]),
        parse_currency(parts[2]),
    )


def parse_rate(text: str) -> str:
    parts = _strip_command(text.strip().split(), "/rate")
    if len(parts) != 1:
        raise UserInputError(FORMAT_RATE)
    return parse_currency(parts[0])


def is_free_form(text: str | None) -> bool:
    if not text or text.startswith("/"):
        return False
    parts = text.split()
    if len(parts) != 3:
        return False
    amount = re.fullmatch(r"\d+(?:[.,]\d+)?", parts[0])
    codes = all(CURRENCY_RE.fullmatch(part) for part in parts[1:])
    return bool(amount and codes)


def format_money(value: float) -> str:
    sign = "-" if value < 0 else ""
    whole, frac = f"{abs(value):.2f}".split(".")
    groups = []
    while whole:
        groups.append(whole[-3:])
        whole = whole[:-3]
    return sign + " ".join(reversed(groups)) + "," + frac


def format_quote(value: float) -> str:
    sign = "-" if value < 0 else ""
    number = abs(value)
    if number >= 1 or number == 0:
        return sign + format_money(number)
    if number >= 0.01:
        raw = f"{number:.4f}".rstrip("0").rstrip(".")
    elif number >= 0.0001:
        raw = f"{number:.6f}".rstrip("0").rstrip(".")
    else:
        raw = f"{number:.8f}".rstrip("0").rstrip(".")
    whole, frac = raw.split(".")
    if len(frac) < 2:
        frac = frac.ljust(2, "0")
    return sign + whole + "," + frac
