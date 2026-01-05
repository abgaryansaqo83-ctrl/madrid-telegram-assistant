# backend/bot.py

# ==========================
#  IMPORTS & INITIAL SETUP
# ==========================
import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

from backend.ai.bot_ai import ask_city_bot

from backend.languages import LANG, detect_lang
from backend.jobs import add_offer, add_request, find_matches, init_jobs_schema
from backend.database import init_db
from backend.memory import save_message_with_analysis
from backend.matching import (
    parse_housing_offer,
    find_matching_requests,
    find_matching_offers,
    is_housing_offer,
    is_housing_request,
)
from backend.events import get_upcoming_cinema_events
from backend.events import _get_conn
from backend.ai.response import QuestionAutoResponder
from backend.ai.traffic import madrid_morning_traffic
from backend.news import (
    build_city_overview_message,
    build_cinema_message,
    build_theatre_message,
    build_restaurant_message,
    build_holidays_message,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN missing in environment variables")

bot = Bot(TOKEN)
dp = Dispatcher()

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
bot_responder = QuestionAutoResponder(timeout=300)


# ==========================
#  KEYBOARDS
# ==========================

main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🤖 Старт‑бот / Iniciar bot")],
        [KeyboardButton(text="📰 Новости / Noticias")],
        [KeyboardButton(text="👨‍💼 Админ / Admin")],
    ],
    resize_keyboard=True,
)

news_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎬 Кино"), KeyboardButton(text="🎭 Шоу и театр в Мадриде")],
        [KeyboardButton(text="🍷 Бары и рестораны")],
        [KeyboardButton(text="🎉 Мероприятия")],
        [KeyboardButton(text="⬅️ Назад")],
    ],
    resize_keyboard=True,
)

def _build_madrid_show_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="🎭 Театр", callback_data="madrid_show:theatre"),
            InlineKeyboardButton(text="🎵 Мюзиклы", callback_data="madrid_show:musical"),
        ],
        [
            InlineKeyboardButton(text="👶 Для детей", callback_data="madrid_show:kids"),
            InlineKeyboardButton(text="🎪 Цирк", callback_data="madrid_show:circo"),
        ],
        [
            InlineKeyboardButton(text="💃 Фламенко", callback_data="madrid_show:flamenco"),
            InlineKeyboardButton(text="🎼 Опера и классика", callback_data="madrid_show:opera"),
        ],
        [
            InlineKeyboardButton(text="🩰 Танец и балет", callback_data="madrid_show:dance"),
            InlineKeyboardButton(text="😂 Юмор / монологи", callback_data="madrid_show:comedy"),
        ],
        [
            InlineKeyboardButton(text="🎩 Магия", callback_data="madrid_show:magic"),
            InlineKeyboardButton(text="🎟 Другие шоу", callback_data="madrid_show:other"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="madrid_show:back"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ==========================
#  STATES
# ==========================

class BotMode(StatesGroup):
    chat = State()


class FeedbackMode(StatesGroup):
    waiting_text = State()


# ==========================
#  HELPERS
# ==========================

def is_trade_question(text: str) -> bool:
    trade_keywords = [
        "купить", "продать", "товар", "объявление", "куплю",
        "продаю", "акция", "скидка", "перепродажа", "срочно", "цена",
    ]
    return any(word in text.lower() for word in trade_keywords)


# ==========================
#  /START & BASIC COMMANDS
# ==========================

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    text = (
        "🇪🇸 Добро пожаловать в Madrid Community Bot!\n\n"
        "Выберите режим:\n"
        "🤖 Старт‑бот / Iniciar bot — задать любой городской вопрос\n"
        "📰 Новости / Noticias — кино, театр, бары, мероприятия\n"
        "👨‍💼 Админ / Admin — написать администратору\n"
    )
    await message.answer(text, reply_markup=main_menu_keyboard)
    logger.info(f"User {message.from_user.id} started bot")


@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    await message.answer(LANG[lang]["help"])
    logger.info(f"User {message.from_user.id} requested help")


# ==========================
#  🤖 БОТ — AI / ՀԻՄՆԱԿԱՆ ՕԳՆԱԿԱՆ
# ==========================

@dp.message(F.text == "🤖 Старт‑бот / Iniciar bot")
async def bot_mode_on(message: types.Message, state: FSMContext):
    await state.set_state(BotMode.chat)
    await message.answer(
        "Вы в режиме 🤖 Старт‑бот / Iniciar bot.\n"
        "Задайте вопрос, например: «Где можно поесть пиццу в Мадриде?»\n\n"
        "Чтобы вернуться в меню, нажмите любой из пунктов: "
        "📰 Новости / Noticias или 👨‍💼 Админ / Admin.",
        reply_markup=main_menu_keyboard,
    )
    logger.info("User %s switched to Bot mode", message.from_user.id)


@dp.message(BotMode.chat)
async def bot_mode_chat(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    question_id = str(message.message_id)
    text = (message.text or "").strip()

    if text in (
        "📰 Новости / Noticias",
        "👨‍💼 Админ / Admin",
    ):
        await state.clear()
        await message.answer("Главное меню:", reply_markup=main_menu_keyboard)
        return

    bot_responder.add_question(user_id, text, question_id, search_type="city")

    logger.info(
        "BotMode.chat question: user_id=%s qid=%s text=%r",
        user_id,
        question_id,
        text,
    )

    await message.answer("Ищу для вас варианты и подсказки…")

    try:
        answer_text = await ask_city_bot(text)

        if answer_text:
            await message.answer(answer_text)
        else:
            await message.answer(
                "Пока не нашёл подходящих вариантов. "
                "Попробуйте сформулировать вопрос иначе."
            )
    except Exception as e:
        logger.error("AI error in BotMode.chat: %s", e, exc_info=True)
        await message.answer(
            "Произошла ошибка при получении ответа от бота. "
            "Попробуйте ещё раз чуть позже."
        )


# ==========================
#  📰 НОВОСТИ — EVENTS / КИНО / ТЕАТР / БАРЫ / МЕРОПРИЯТИЯ
# ==========================

@dp.message(F.text == "📰 Новости / Noticias")
async def news_menu(message: types.Message):
    await message.answer(
        "Выберите раздел новостей:",
        reply_markup=news_keyboard,
    )


@dp.message(F.text == "⬅️ Назад")
async def back_to_menu(message: types.Message):
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard,
    )


@dp.message(Command("news"))
async def news_cmd(message: types.Message):
    """
    Краткий обзор + кино (по 2 события максимум).
    """
    try:
        overview = build_city_overview_message()
        cinema = build_cinema_message(max_items=2)

        parts = []
        if overview:
            parts.append(overview)
        if cinema:
            parts.append(cinema)

        if not parts:
            await message.answer("📰 На сегодня нет событий для отображения.")
            return

        text = "\n\n".join(parts)
        await message.answer(
            text,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"News error: {e}", exc_info=True)
        await message.answer("📰 Новости временно недоступны.")
    logger.info(f"User {message.from_user.id} requested news")


@dp.message(F.text == "🎬 Кино")
async def news_cinema(message: types.Message):
    try:
        events = get_upcoming_cinema_events(limit=2)
        if not events:
            await message.answer("🎬 На сегодня не найдено событий категории «Кино».")
            return

        for e in events:
            title = (e.get("title") or "").strip()
            place = (e.get("place") or "").strip()
            address = (e.get("address") or "").strip()
            # Փորձենք նորմալ բաժանել՝ comma-ներով
            address_lines: list[str] = []
            if address:
                parts = [p.strip() for p in address.split(",") if p.strip()]
                if parts:
                    # Առաջին հատվածը՝ փողոցի անունը
                    first_line = parts[0]
                    address_lines.append(f"📍 {first_line}")
                    # Մնացածը՝ երկրորդ տողի մեջ (քաղաք, postal код, район...)
                    if len(parts) > 1:
                        rest = ", ".join(parts[1:])
                        address_lines.append(f"📍 {rest}")
            url = (e.get("url") or "").strip()
            image_url = (e.get("image_url") or "").strip()
            price = (e.get("price") or "").strip()   # հիմա դատարկ է, բայց թող տեղը լինի

            lines = []
            if title:
                lines.append(f"*{title}*")
            if place:
                lines.append(f"📍 {place}")
            for addr_line in address_lines:
                lines.append(addr_line)
            # եթե երբևէ կունենանք գին/ամսաթիվ, սրանք լրացնես
            if price:
                lines.append(f"💶 {price}")
            if url:
                lines.append(f"🔗 [Подробнее]({url})")

            caption = "\n".join(lines) if lines else "🎬 Кино"

            if image_url:
                await message.answer_photo(
                    photo=image_url,
                    caption=caption,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
            else:
                await message.answer(
                    caption,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )

    except Exception as e:
        logger.error(f"Cinema news error: {e}", exc_info=True)
        await message.answer("🎬 Раздел «Кино» временно недоступен.")

@dp.message(F.text == "🎭 Шоу и театр в Мадриде")
async def news_theatre(message: types.Message):
    text = (
        "🎭 *Шоу и театр в Мадриде*" 
        "Выберите категорию ниже, чтобы увидеть ближайшие события."
    )
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=_build_madrid_show_keyboard(),
    )

CATEGORY_LABELS = {
    "theatre": "🎭 Театр",
    "musical": "🎵 Мюзиклы",
    "kids": "👶 Для детей",
    "circo": "🎪 Цирк",
    "flamenco": "💃 Фламенко",
    "opera": "🎼 Опера и классика",
    "dance": "🩰 Танец и балет",
    "comedy": "😂 Юмор / монологи",
    "magic": "🎩 Магия",
    "other": "🎟 Другие шоу",
}

@dp.message(F.text == "🍷 Бары и рестораны / Bares y restaurantes")
async def news_bars(message: types.Message):
    try:
        restaurants = build_restaurant_message(max_items=2)
        if not restaurants:
            await message.answer(
                "🍷 На сегодня не найдено событий в барах и ресторанах."
            )
            return

        await message.answer(
            restaurants,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Restaurant news error: {e}", exc_info=True)
        await message.answer(
            "🍷 Раздел «Бары и рестораны» временно недоступен."
        )


@dp.message(F.text == "🎉 Мероприятия / Eventos")
async def news_events(message: types.Message):
    try:
        holidays = build_holidays_message(max_items=2)
        if not holidays:
            await message.answer(
                "🎉 На сегодня не найдено городских мероприятий и праздников."
            )
            return

        await message.answer(
            holidays,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Events news error: {e}", exc_info=True)
        await message.answer("🎉 Раздел «Мероприятия» временно недоступен.")


async def _fetch_events_by_category(category: str, limit: int = 3):
    sql = """
        SELECT title, place, date, start_time, source_url, address, price, image_url
        FROM madrid_events
        WHERE category = %s
        ORDER BY date, start_time
        LIMIT %s;
    """
    events = []
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(sql, (category, limit))
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Error fetching events for category={category}: {e}", exc_info=True)
        return events

    for title, place, date, start_time, source_url, address, price, image_url in rows:
        date_str = str(date)
        time_str = start_time or ""
        events.append(
            {
                "title": title or "",
                "place": place or "",
                "date": date_str,
                "time": time_str,
                "link": source_url or "",
                "address": address or "",
                "price": price or "",
                "image_url": image_url or "",
            }
        )
    return events

@dp.callback_query(F.data.startswith("madrid_show:"))
async def handle_madrid_show_callback(callback: types.CallbackQuery):
    _, slug = callback.data.split(":", 1)

    if slug == "back":
        text = (
            "🎭 *Шоу и театр в Мадриде*\n\n"
            "Выберите категорию ниже, чтобы увидеть ближайшие события."
        )
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=_build_madrid_show_keyboard(),
        )
        await callback.answer()
        return

    label = CATEGORY_LABELS.get(slug, "Шоу")
    events = await _fetch_events_by_category(slug, limit=3)

    if not events:
        await callback.answer("Пока нет событий в этой категории.", show_alert=True)
        return

    await callback.message.edit_text(
        f"{label}:",
        parse_mode="Markdown",
        reply_markup=_build_madrid_show_keyboard(),
    )

    for ev in events:
        title = ev["title"]
        place = ev["place"]
        date = ev["date"]
        time = ev["time"]
        address = ev["address"]
        price = ev["price"]
        link = ev["link"]
        image_url = ev["image_url"]

        lines = []
        if title:
            lines.append(f"*{title}*")
        if place:
            lines.append(f"📍 {place}")
        if address:
            lines.append(f"📍 {address}")
        if date or time:
            lines.append(f"📅 {date}  ⏰ {time}")
        if price:
            lines.append(f"💶 {price}")
        if link:
            lines.append(f"🔗 [Подробнее]({link})")

        caption = "\n".join(lines) if lines else label

        if image_url:
            await callback.message.answer_photo(
                photo=image_url,
                caption=caption,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        else:
            await callback.message.answer(
                caption,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )

    await callback.answer()

# ==========================
#  👨‍💼 АДМИН — FEEDBACK
# ==========================

@dp.message(F.text == "👨‍💼 Админ / Admin")
async def feedback_start(message: types.Message, state: FSMContext):
    await state.set_state(FeedbackMode.waiting_text)
    await message.answer(
        "Напишите вашу жалобу или предложение.\n"
        "Сообщение будет отправлено напрямую администратору и не будет видно группе."
    )

@dp.message(FeedbackMode.waiting_text)
async def feedback_receive(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text or len(text) < 5:
        await message.answer("Пожалуйста, напишите сообщение чуть подробнее.")
        return

    if ADMIN_CHAT_ID:
        user = message.from_user
        header = f"💬 Сообщение от пользователя @{user.username or user.id} (ID: {user.id}):\n\n"
        await bot.send_message(ADMIN_CHAT_ID, header + text)

    await state.clear()
    await message.answer(
        "✅ Ваше сообщение было отправлено администратору. Спасибо за ваше обращение!"
    )

# ==========================
#  JOBS / MATCHING ԿՈՄԱՆԴՆԵՐ
# ==========================

@dp.message(F.text.startswith("/offer "))
async def offer_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    text = message.text.replace("/offer ", "").strip()
    if not text:
        await message.answer(
            LANG[lang].get("empty_offer", "Please provide offer details")
        )
        return
    add_offer(message.from_user, text)
    await message.answer(LANG[lang]["offer_saved"])
    logger.info(f"User {message.from_user.id} added offer: {text[:50]}")

@dp.message(F.text.startswith("/request "))
async def request_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    text = message.text.replace("/request ", "").strip()
    if not text:
        await message.answer(
            LANG[lang].get("empty_request", "Please provide request details")
        )
        return
    add_request(message.from_user, text)
    await message.answer(LANG[lang]["request_saved"])
    logger.info(f"User {message.from_user.id} added request: {text[:50]}")

@dp.message(Command("match"))
async def match_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    matches = find_matches()
    if not matches:
        await message.answer(LANG[lang]["no_matches"])
        return

    msg = LANG[lang]["matches"] + "\n\n"
    for req, off in matches[:5]:
        msg += (
            f"👤 **Request:** {req['text'][:100]}...\n"
            f"💼 **Offer:** {off['text'][:100]}...\n---\n"
        )
    await message.answer(msg, parse_mode="Markdown")
    logger.info(f"User {message.from_user.id} checked matches: {len(matches)} found")

# ==========================
#  WELCOME ՆՈՐ ՄԱՍՆԱԿԻՑՆԵՐԻ
# ==========================

@dp.message(F.new_chat_members)
async def welcome_new_member(message: types.Message):
    for new_member in message.new_chat_members:
        if new_member.id == (await bot.get_me()).id:
            continue
        username = new_member.username if new_member.username else new_member.first_name
        mention = f"@{username}" if new_member.username else new_member.first_name
        welcome_text = (
            f"🎉 **Добро пожаловать, {mention}!**\n\n"
            f"Мы рады приветствовать нового участника!\n"
            f"Надеемся, что наша группа будет полезна для вас и вы найдёте здесь всё, что ищете.\n\n"
            f"💬 **Не стесняйтесь задавать вопросы**\n"
            f"🤝 **Делитесь опытом с другими участниками**\n"
            f"📢 **Следите за полезными новостями**\n\n"
            f"Спасибо, что присоединились к нам! 🇪🇸"
        )
        await message.answer(welcome_text, parse_mode="Markdown")
        logger.info(f"Welcomed new member: {username} (ID: {new_member.id})")

# ==========================
# OWNER PUBLISH TO GROUP
# ==========================

@dp.message(Command("publish"))
async def publish_to_group_command(message: types.Message):
    """
    Օգտագործում: Reply անես հաղորդագրության վրա /publish
    և այն կհրապարակվի խումբում
    """
    logger.info(
        f"/publish command received from user_id={message.from_user.id}, OWNER_ID={OWNER_ID}"
    )

    if message.from_user.id != OWNER_ID:
        logger.warning(f"Unauthorized /publish attempt by {message.from_user.id}")
        await message.answer("❌ Այս հրամանը հասանելի է միայն բոտի տիրոջը։")
        return

    logger.info("/publish: owner verified")

    if not message.reply_to_message:
        logger.info("/publish: no reply message")
        await message.answer(
            "💡 Օգտագործման եղանակը:\n"
            "1️⃣ Ուղարկիր ինձ ցանկացած հաղորդագրություն\n"
            "2️⃣ Reply արա դրան և գրիր /publish\n"
            "3️⃣ Հաղորդագրությունը կհրապարակվի խմբում"
        )
        return

    reply = message.reply_to_message
    logger.info("/publish: reply message found")

    group_chat_id = os.getenv("CHAT_ID", "")  # ← CHAT_ID փոխարեն GROUP_CHAT_ID
    logger.info(f"/publish: CHAT_ID={group_chat_id}")

    if not group_chat_id:
        logger.error("/publish: CHAT_ID is empty")
        await message.answer(
            "❌ CHAT_ID փոփոխականը չի գտնվել environment variables-ում։\n"
            "Մուտք գործիր Render dashboard → Environment և ավելացրու CHAT_ID=քո խմբի ID‑ն։"
        )
        return

    try:
        logger.info("/publish: attempting to send message to group")

        if reply.text:
            logger.info("/publish: sending text message")
            await bot.send_message(chat_id=group_chat_id, text=reply.text)
        elif reply.photo:
            logger.info("/publish: sending photo")
            await bot.send_photo(
                chat_id=group_chat_id,
                photo=reply.photo[-1].file_id,
                caption=reply.caption or "",
            )
        elif reply.video:
            logger.info("/publish: sending video")
            await bot.send_video(
                chat_id=group_chat_id,
                video=reply.video.file_id,
                caption=reply.caption or "",
            )
        elif reply.document:
            logger.info("/publish: sending document")
            await bot.send_document(
                chat_id=group_chat_id,
                document=reply.document.file_id,
                caption=reply.caption or "",
            )
        else:
            logger.warning("/publish: unsupported message type")
            await message.answer(
                "Այս տեսակի հաղորդագրությունը դեռ չեմ կարող հրապարակել "
                "(պետք է լինի text, photo, video կամ document)։"
            )
            return

        logger.info("/publish: message published successfully")
        await message.answer("✅ Հաղորդագրությունը հրապարակվեց Madrid խմբում։")

    except Exception as e:
        logger.exception(f"/publish error: {e}")
        await message.answer(f"❌ Սխալ հրապարակելիս:\n{e}")

# ==========================
#  FALLBACK MESSAGE HANDLER
# ==========================

@dp.message(F.text)
async def handle_message(message: types.Message):
    # ⬇️ ԿԱՐԵՎՈՐ — command-ները բաց թողնել
    if message.text.startswith("/"):
        return
    
    keywords = save_message_with_analysis(message.from_user.id, message.text)
    question_id = str(message.message_id)
    user_id = message.from_user.id

    if is_trade_question(message.text):
        bot_responder.add_question(
            user_id, message.text, question_id, search_type="item"
        )
    if "еда" in message.text.lower() or "food" in message.text.lower():
        bot_responder.add_question(
            user_id, message.text, question_id, search_type="food"
        )

    if keywords.get("housing"):
        if is_housing_offer(message.text):
            offer_data = parse_housing_offer(message.text)
            matches = find_matching_requests(offer_data)
            if matches:
                match_count = len(matches)
                await message.reply(
                    f"🏠 **{match_count} пользователей ищут похожее жильё!**\n\n"
                    f"Администратор свяжет вас с заинтересованными.",
                    parse_mode="Markdown",
                )
        elif is_housing_request(message.text):
            request_data = parse_housing_offer(message.text)
            matches = find_matching_offers(request_data)
            if matches:
                match_count = len(matches)
                await message.reply(
                    f"🏠 **{match_count} предложений по вашим параметрам найдено!**\n\n"
                    f"Администратор свяжет вас с владельцами.",
                    parse_mode="Markdown",
                )

# ==========================
#  MAIN & SCHEDULER START
# ==========================

async def main():
    init_db()
    init_jobs_schema()
    
    from backend.events import init_events_schema
    init_events_schema()

    from backend.scheduler import start_scheduler
    start_scheduler(bot)

    logger.info("🚀 Starting Madrid Community Bot...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
