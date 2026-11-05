# Valyuta kursi boti

Telegram boti summani bir valyutadan boshqasiga o‘giradi. Kurslar `https://open.er-api.com/v6/latest/{VALYUTA}` manzilidan olinadi va MySQL da keshlanadi.

Stack: Python, aiogram, MySQL, mysql-connector-python, Docker Compose.

## Docker Compose

```bash
cp .env.example .env
```

`.env` ichidagi `BOT_TOKEN` ga @BotFather bergan tokenni yozing, so‘ng:

```bash
docker compose up --build
```

Compose MySQL ni `mysql` hostida ko‘taradi va botni u tayyor bo‘lgach ishga tushiradi. Ma’lumot `mysql_data` volume da qoladi. Port `3306` lokal mashinada ochiq.

## Buyruqlar

- `/convert 100 USD UZS` yoki `100 USD UZS`
- `/rate USD` — 1 birlikning so‘mga kursi
- `/currencies` — kodlar ro‘yxati
- `/history` — shu foydalanuvchining so‘nggi 5 ta konvertatsiyasi
- `/start`, `/help`

Mashhur valyuta tugmalari kursni UZS ga nisbatan chiqaradi.

## Ma’lumotlar

- `users` — Telegram foydalanuvchisi
- `rate_cache` — kurslar, `CACHE_TTL_SECONDS` (standart 10 daqiqa) ichida qayta so‘ralmaydi
- `conversions` — konvertatsiya tarixi
