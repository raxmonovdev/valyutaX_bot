import unittest

from api import CurrencyNotFound, RateService, RateServiceError
from utils import (
    AMOUNT_ERROR,
    CURRENCY_ERROR,
    FORMAT_CONVERT,
    FORMAT_RATE,
    UserInputError,
    format_money,
    format_quote,
    is_free_form,
    parse_convert,
    parse_rate,
)


class ParseTests(unittest.TestCase):
    def test_convert_command(self):
        request = parse_convert("/convert 100 USD UZS")
        self.assertEqual((request.amount, request.from_cur, request.to_cur), (100, "USD", "UZS"))

    def test_lowercase_and_bot_suffix(self):
        request = parse_convert("/convert@MyBot 100 usd eur")
        self.assertEqual(request.from_cur, "USD")
        self.assertEqual(request.to_cur, "EUR")

    def test_free_form_and_comma_decimal(self):
        request = parse_convert("25,5 gbp cny")
        self.assertEqual(request.amount, 25.5)
        self.assertEqual(request.from_cur, "GBP")

    def test_bad_format_is_not_amount_error(self):
        with self.assertRaises(UserInputError) as ctx:
            parse_convert("/convert 100 USD")
        self.assertEqual(str(ctx.exception), FORMAT_CONVERT)

    def test_non_number_amount(self):
        with self.assertRaises(UserInputError) as ctx:
            parse_convert("/convert abc USD EUR")
        self.assertEqual(str(ctx.exception), AMOUNT_ERROR)

    def test_negative_and_zero(self):
        for text in ("/convert -50 USD EUR", "/convert 0 USD EUR", "0 USD EUR"):
            with self.assertRaises(UserInputError) as ctx:
                parse_convert(text)
            self.assertEqual(str(ctx.exception), AMOUNT_ERROR)

    def test_bad_currency_before_api(self):
        with self.assertRaises(UserInputError) as ctx:
            parse_convert("/convert 100 US UZS")
        self.assertEqual(str(ctx.exception), CURRENCY_ERROR)

    def test_rate_command(self):
        self.assertEqual(parse_rate("/rate uzs"), "UZS")
        with self.assertRaises(UserInputError) as ctx:
            parse_rate("/rate")
        self.assertEqual(str(ctx.exception), FORMAT_RATE)

    def test_money_format(self):
        self.assertEqual(format_money(1280000), "1 280 000,00")
        self.assertEqual(format_money(25.5), "25,50")

    def test_quote_keeps_small_rates(self):
        self.assertEqual(format_quote(12800), "12 800,00")
        self.assertEqual(format_quote(0.000078), "0,000078")

    def test_free_form_detector(self):
        self.assertTrue(is_free_form("100 USD UZS"))
        self.assertFalse(is_free_form("salom dunyo bot"))
        self.assertFalse(is_free_form("/convert 100 USD UZS"))


class RateServiceTests(unittest.TestCase):
    def test_cache_avoids_second_request(self):
        calls = []

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "result": "success",
                    "rates": {"UZS": 12000, "USD": 1},
                    "time_last_update_utc": "Tue, 03 Nov 2026 00:02:31 +0000",
                }

        def fake_get(url, timeout):
            calls.append((url, timeout))
            return Response()

        service = RateService(timeout=3, ttl=600)
        import api

        original = api.requests.get
        api.requests.get = fake_get
        try:
            first, updated = service.convert(100, "USD", "UZS")
            second, _updated = service.convert(50, "USD", "UZS")
        finally:
            api.requests.get = original

        self.assertEqual(first, 1_200_000)
        self.assertEqual(second, 600_000)
        self.assertIn("2026", updated)
        self.assertEqual(len(calls), 1)

    def test_unsupported_code(self):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"result": "error", "error-type": "unsupported-code"}

        service = RateService()
        import api

        original = api.requests.get
        api.requests.get = lambda url, timeout: Response()
        try:
            with self.assertRaises(CurrencyNotFound):
                service.get_rates("XYZ")
        finally:
            api.requests.get = original

    def test_timeout_becomes_service_error(self):
        import requests

        service = RateService()
        import api

        def boom(url, timeout):
            raise requests.Timeout("slow")

        original = api.requests.get
        api.requests.get = boom
        try:
            with self.assertRaises(RateServiceError):
                service.get_rates("USD")
        finally:
            api.requests.get = original


if __name__ == "__main__":
    unittest.main()
