import asyncio
import logging
from html import escape

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
)

from api import CurrencyNotFound, RateService, RateServiceError
from config import BOT_TOKEN, POPULAR
from countries import (
    Place,
    currency_place,
    quotes_from_usd_table,
    render_choices,
    render_price,
    render_world_rates,
    search,
)
from db import MysqlRateCache, recent_conversions, save_conversion, upsert_user, wait_until_ready
from utils import (
    CURRENCY_ERROR,
    FORMAT_RATE,
    UserInputError,
    format_money,
    format_quote,
    is_free_form,
    parse_amount,
    parse_convert,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("currency_bot")

START_TEXT = (
    "✨ <b>Valyuta kursi boti</b>\n\n"
    "Salom! Summani bir zumda boshqa valyutaga o'giraman.\n\n"
    "🔄 <b>O'girish</b>\n"
    "<code>100 USD UZS</code>\n"
    "yoki <code>/convert 100 USD EUR</code>\n\n"
    "🌍 <b>Davlat bo'yicha narx</b>\n"
    "Nomini yozing: <code>Yaponiya</code>, <code>Germaniya</code>, <code>Turkiya</code>\n\n"
    "🌐 <b>Butun dunyo</b>\n"
    "<code>/currencies</code> — har bir valyutaning hozirgi narxi\n\n"
    "📊 <code>/rate USD</code> — bitta kurs\n"
    "🕘 <code>/history</code> — so'nggi amallar\n"
    "ℹ️ <code>/malumotlar</code> — bot haqida"
)
ABOUT_TEXT = (
    "ℹ️ <b>Ma'lumotlar</b>\n\n"
    "💱 Bu bot summani bir valyutadan boshqasiga o'giradi.\n"
    "Kurslar ochiq manbadan olinadi va qisqa muddat saqlanadi.\n\n"
    "🌍 <b>Istalgan davlat</b>\n"
    "<code>Yaponiya</code> deb yozing — o'sha valyutaning hozirgi narxi chiqadi.\n\n"
    "🌐 <b>Butun dunyo</b>\n"
    "<code>/currencies</code> barcha valyutalarni so'mda ko'rsatadi.\n\n"
    "🔄 Misol: <code>100 USD UZS</code>\n"
    "📊 Misol: <code>/rate EUR</code>"
)
SHORT_DESCRIPTION = "🌍 Butun dunyo valyutasi. Davlat yozing yoki summani o'giring."
DESCRIPTION = (
    "✨ Valyuta kursi boti\n\n"
    "🌍 Davlat nomini yozing — hozirgi narx chiqadi.\n"
    "Yaponiya, Germaniya, Turkiya, Qozog'iston.\n\n"
    "🌐 /currencies — butun dunyo valyutasining hozirgi narxi\n"
    "🔄 100 USD UZS\n"
    "📊 /rate USD\n"
    "🕘 /history — so'nggi 5 ta amal"
)
BOT_COMMANDS = (
    BotCommand(command="start", description="✨ Botni ochish va qanday ishlatish"),
    BotCommand(command="malumotlar", description="ℹ️ Bot haqida qisqa ma'lumot"),
    BotCommand(command="rate", description="📊 Davlat yoki valyuta kursini ko'rish"),
    BotCommand(command="convert", description="🔄 Summani boshqa valyutaga o'girish"),
    BotCommand(command="currencies", description="🌍 Butun dunyo valyutasining hozirgi narxi"),
    BotCommand(command="history", description="🕘 So'nggi o'girishlaringiz"),
    BotCommand(command="help", description="❓ Yordam va misollar"),
)
HELP_TEXT = (
    "❓ <b>Yordam</b>\n\n"
    "🌍 Davlat nomini yozing: <code>Yaponiya</code>, <code>Germaniya</code>, <code>Misr</code>\n"
    "Hozirgi narx so'm va dollarda chiqadi.\n\n"
    "🌐 <code>/currencies</code> — butun dunyo, har bir valyutaning hozirgi narxi\n\n"
    "🔄 <code>/convert 100 USD EUR</code>\n"
    "miqdor, qaysi valyutadan va qaysi valyutaga\n\n"
    "📊 <code>/rate USD</code> — 1 birlik necha so'm\n"
    "🕘 <code>/history</code> — so'nggi 5 ta konvertatsiya\n"
    "ℹ️ <code>/malumotlar</code> — bot haqida\n"
    "✏️ Kurs ostidagi tugma — yozgan soningizni shu valyutaga o'giradi\n\n"
    "⚠️ Miqdor musbat son bo'lishi kerak.\n"
    "O'nlik uchun nuqta yoki vergul: <code>25.5</code> yoki <code>25,5</code>.\n"
    "Valyuta kodi 3 harf: <b>USD</b>, <b>EUR</b>, <b>UZS</b>."
)
GENERIC_ERROR = "⚠️ Xatolik yuz berdi. Birozdan keyin qayta urinib ko'ring."
FLAGS = {
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
    "RUB": "🇷🇺",
    "UZS": "🇺🇿",
    "GBP": "🇬🇧",
    "CNY": "🇨🇳",
}

class ConvertState(StatesGroup):
    amount = State()


class ClearConvertOnCommand(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        if (event.text or "").startswith("/"):
            state: FSMContext | None = data.get("state")
            if state is not None:
                await state.clear()
        return await handler(event, data)


router = Router()
router.message.middleware(ClearConvertOnCommand())
rates = RateService(cache=MysqlRateCache())


def amount_keyboard(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✏️ Summani {code} ga o'girish",
                    callback_data=f"conv:{code}",
                )
            ]
        ]
    )


def conversion_sides(code: str) -> tuple[str, str]:
    if code == "UZS":
        return "USD", "UZS"
    return "UZS", code


def result_text(amount: float, from_cur: str, result: float, to_cur: str, updated: str) -> str:
    updated_line = f"\n🕒 <i>Yangilangan:</i> {escape(updated)}" if updated else ""
    unit = result / amount if amount else 0
    return (
        "✅ <b>Natija</b>\n\n"
        f"<b>{format_money(amount)} {escape(from_cur)}</b>"
        "  →  "
        f"<b>{format_money(result)} {escape(to_cur)}</b>\n"
        f"📊 Hozirgi kurs: 1 {escape(from_cur)} = <b>{format_quote(unit)}</b> {escape(to_cur)}"
        f"{updated_line}"
    )


def popular_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=f"{FLAGS.get(code, '💱')} {code}", callback_data=f"rate:{code}")
        for code in POPULAR
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons[:3], buttons[3:]])


async def remember_user(message_or_query) -> None:
    user = message_or_query.from_user
    if user is None:
        return
    try:
        await asyncio.to_thread(upsert_user, user.id, user.username, user.first_name)
    except Exception:
        log.exception("Foydalanuvchini saqlab bo'lmadi")


async def reply_rate(message: Message, code: str) -> None:
    await answer_place(message, currency_place(code))


async def answer_place(message: Message, place: Place) -> None:
    try:
        table, updated = await asyncio.to_thread(rates.get_rates, "USD")
    except RateServiceError as exc:
        await message.answer(str(exc))
        return
    except Exception:
        log.exception("Davlat kursi kutilmagan xato")
        await message.answer(GENERIC_ERROR)
        return
    pair = quotes_from_usd_table(table, place.currency)
    if pair is None:
        await message.answer(render_price(place, None, None, ""))
        return
    per_uzs, per_usd = pair
    await message.answer(
        render_price(place, per_uzs, per_usd, updated),
        reply_markup=amount_keyboard(place.currency),
    )


async def answer_lookup(message: Message, query: str) -> None:
    found = search(query)
    if not found:
        await message.answer("❓ Davlat topilmadi.\nMisol: <code>Yaponiya</code> yoki <code>/rate USD</code>")
        return
    if len(found) > 1:
        await message.answer(render_choices(found))
        return
    await answer_place(message, found[0])


async def send_world_rates(message: Message) -> None:
    try:
        table, updated = await asyncio.to_thread(rates.get_rates, "USD")
    except RateServiceError as exc:
        await message.answer(str(exc))
        return
    except Exception:
        log.exception("Dunyo kurslarida kutilmagan xato")
        await message.answer(GENERIC_ERROR)
        return
    pages = render_world_rates(table, updated)
    for page in pages:
        await message.answer(page)
    await message.answer(
        "✏️ Bitta kursni oching, masalan <code>Yaponiya</code>.\n"
        "Pastdagi tugma yozgan soningizni shu valyutaga o'giradi."
    )


async def reply_convert(message: Message, text: str) -> None:
    try:
        request = parse_convert(text)
        result, updated = await asyncio.to_thread(
            rates.convert, request.amount, request.from_cur, request.to_cur
        )
    except UserInputError as exc:
        await message.answer(str(exc))
        return
    except CurrencyNotFound:
        await message.answer(CURRENCY_ERROR)
        return
    except RateServiceError as exc:
        await message.answer(str(exc))
        return
    except Exception:
        log.exception("Konvertatsiya kutilmagan xato")
        await message.answer(GENERIC_ERROR)
        return

    if message.from_user is not None:
        try:
            await asyncio.to_thread(
                save_conversion,
                message.from_user.id,
                request.amount,
                request.from_cur,
                request.to_cur,
                result,
            )
        except Exception:
            log.exception("Konvertatsiya tarixini saqlab bo'lmadi")

    await message.answer(
        result_text(request.amount, request.from_cur, result, request.to_cur, updated),
        reply_markup=amount_keyboard(request.to_cur),
    )


async def send_start(message: Message) -> None:
    await remember_user(message)
    await message.answer(START_TEXT, reply_markup=ReplyKeyboardRemove())
    await message.answer(
        "⚡ <b>Tezkor kurslar</b>\nButun dunyo uchun <code>/currencies</code> ni bosing.",
        reply_markup=popular_keyboard(),
    )


async def send_history(message: Message, user_id: int) -> None:
    try:
        rows = await asyncio.to_thread(recent_conversions, user_id, 5)
    except Exception:
        log.exception("Tarixni o'qib bo'lmadi")
        await message.answer(GENERIC_ERROR)
        return
    if not rows:
        await message.answer(
            "📭 <b>Hali konvertatsiya yo'q.</b>\n"
            "Misol: <code>/convert 100 USD UZS</code>"
        )
        return
    lines = ["🕘 <b>So'nggi konvertatsiyalar</b>", ""]
    for row in rows:
        when = row["created_at"].strftime("%Y-%m-%d %H:%M")
        lines.append(
            f"▫️ <i>{escape(when)}</i>\n"
            f"<b>{format_money(row['amount'])} {escape(str(row['from_code']))}</b>"
            "  →  "
            f"<b>{format_money(row['result'])} {escape(str(row['to_code']))}</b>"
        )
    await message.answer("\n".join(lines))


@router.message(CommandStart())
async def start(message: Message) -> None:
    await send_start(message)


@router.message(Command("about", "malumotlar"))
async def about_cmd(message: Message) -> None:
    await remember_user(message)
    await message.answer(ABOUT_TEXT)


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    await remember_user(message)
    await message.answer(HELP_TEXT)


@router.message(Command("cancel"))
async def cancel_cmd(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🚫 Bekor qilindi. Kursni qayta oching yoki davlat nomini yozing.")


@router.callback_query(F.data.startswith("conv:"))
async def ask_amount(query: CallbackQuery, state: FSMContext) -> None:
    code = (query.data or "").split(":", 1)[1].upper()
    if len(code) != 3 or not code.isalpha():
        await query.answer("Valyuta topilmadi", show_alert=True)
        return
    source, target = conversion_sides(code)
    await state.set_state(ConvertState.amount)
    await state.update_data(source=source, target=target)
    await query.answer()
    if query.message is not None:
        await query.message.answer(
            f"✏️ <b>Summani yozing</b>\n\n"
            f"Siz yozgan son hozirgi kurs bo'yicha "
            f"<b>{escape(source)}</b> dan <b>{escape(target)}</b> ga o'giriladi.\n\n"
            "Masalan: <code>100</code> yoki <code>25,5</code>\n"
            "Bekor qilish: /cancel"
        )


@router.message(StateFilter(ConvertState.amount), F.text)
async def take_amount(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if raw.startswith("/"):
        return
    data = await state.get_data()
    source = str(data.get("source") or "")
    target = str(data.get("target") or "")
    try:
        amount = parse_amount(raw)
    except UserInputError:
        await message.answer("⚠️ Musbat son yuboring. Masalan: <code>100</code> yoki <code>25,5</code>")
        return
    if len(source) != 3 or len(target) != 3:
        await state.clear()
        await message.answer(GENERIC_ERROR)
        return
    try:
        result, updated = await asyncio.to_thread(rates.convert, amount, source, target)
    except CurrencyNotFound:
        await state.clear()
        await message.answer(CURRENCY_ERROR)
        return
    except RateServiceError as exc:
        await message.answer(str(exc))
        return
    except Exception:
        log.exception("Tugma orqali konvertatsiya kutilmagan xato")
        await message.answer(GENERIC_ERROR)
        return
    await remember_user(message)
    if message.from_user is not None:
        try:
            await asyncio.to_thread(
                save_conversion,
                message.from_user.id,
                amount,
                source,
                target,
                result,
            )
        except Exception:
            log.exception("Konvertatsiya tarixini saqlab bo'lmadi")
    await state.clear()
    await message.answer(
        result_text(amount, source, result, target, updated),
        reply_markup=amount_keyboard(target),
    )


@router.message(Command("convert"))
async def convert_cmd(message: Message) -> None:
    await remember_user(message)
    await reply_convert(message, message.text or "")


@router.message(Command("rate"))
async def rate_cmd(message: Message) -> None:
    await remember_user(message)
    parts = (message.text or "").split(maxsplit=1)
    query = parts[1].strip() if len(parts) > 1 else ""
    if not query:
        await message.answer(FORMAT_RATE)
        return
    await answer_lookup(message, query)


@router.message(Command("currencies"))
async def currencies_cmd(message: Message) -> None:
    await remember_user(message)
    await send_world_rates(message)


@router.message(Command("history"))
async def history_cmd(message: Message) -> None:
    await remember_user(message)
    if message.from_user is None:
        return
    await send_history(message, message.from_user.id)


@router.message(F.text.func(is_free_form))
async def free_form(message: Message) -> None:
    await remember_user(message)
    await reply_convert(message, message.text or "")


@router.message(F.text)
async def country_message(message: Message) -> None:
    text = (message.text or "").strip()
    if not text or text.startswith("/") or is_free_form(text):
        return
    found = search(text)
    if not found:
        return
    await remember_user(message)
    if len(found) > 1:
        await message.answer(render_choices(found))
        return
    await answer_place(message, found[0])


@router.callback_query(F.data.startswith("rate:"))
async def popular_rate(query: CallbackQuery) -> None:
    await remember_user(query)
    code = (query.data or "").split(":", 1)[1]
    await query.answer()
    if query.message is not None:
        await reply_rate(query.message, code)


async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi. .env.example faylini .env ga nusxalang va tokenni yozing.")
    await asyncio.to_thread(wait_until_ready)
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.set_my_commands(list(BOT_COMMANDS))
    await bot.set_my_short_description(SHORT_DESCRIPTION)
    await bot.set_my_description(DESCRIPTION)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(router)
    log.info("Bot ishga tushdi")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
