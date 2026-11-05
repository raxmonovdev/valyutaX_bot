import unittest

from countries import PLACES, quotes_from_usd_table, render_price, render_world_rates, search


class CountrySearchTests(unittest.TestCase):
    def test_country_names_in_several_languages(self):
        self.assertEqual(search("Germaniya")[0].currency, "EUR")
        self.assertEqual(search("Япония")[0].currency, "JPY")
        self.assertEqual(search("o'zbekiston")[0].currency, "UZS")
        self.assertEqual(search("Qozog'iston")[0].currency, "KZT")
        self.assertEqual(search("United States")[0].currency, "USD")

    def test_currency_code_and_typo(self):
        self.assertEqual(search("jpy")[0].kind, "currency")
        self.assertEqual(search("germanya")[0].name, "Germaniya")

    def test_ambiguous_congo_and_noise(self):
        names = {place.name for place in search("Kongo")}
        self.assertEqual(names, {"Kongo", "Kongo DR"})
        self.assertEqual(search("salom"), [])

    def test_world_coverage(self):
        self.assertGreaterEqual(len(PLACES), 190)

    def test_price_card_uses_live_cross_rate(self):
        place = search("Yaponiya")[0]
        pair = quotes_from_usd_table({"USD": 1, "UZS": 12000, "JPY": 150}, "JPY")
        self.assertIsNotNone(pair)
        per_uzs, per_usd = pair
        self.assertEqual(per_uzs, 80)
        text = render_price(place, per_uzs, per_usd, "Tue, 03 Nov 2026")
        self.assertIn("Yaponiya", text)
        self.assertIn("80,00 UZS", text)
        self.assertIn("Hozirgi narx", text)

    def test_world_rates_include_every_code(self):
        table = {"USD": 1, "UZS": 12000, "JPY": 150, "EUR": 0.9, "KZT": 480}
        pages = render_world_rates(table, "Tue, 03 Nov 2026")
        text = "\n".join(pages)
        for code in ("USD", "JPY", "EUR", "KZT"):
            self.assertIn(code, text)
        self.assertTrue(all(len(page) <= 4000 for page in pages))


if __name__ == "__main__":
    unittest.main()
