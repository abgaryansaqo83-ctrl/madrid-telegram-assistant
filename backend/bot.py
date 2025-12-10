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
from dotenv import load_dotenv

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

from backend.ai.response import QuestionAutoResponder
from backend.ai.traffic import madrid_morning_traffic
from backend.news import (
    build_city_overview_message,
    build_cinema_message,
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
bot_responder = QuestionAutoResponder(timeout=300)

# ==========================
#  KEYBOARDS
# ==========================

# Գլխավոր մենյու (3 կոճակ)
main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🤖 Бот")],
        [KeyboardButton(text="📰 Новости")],
        [KeyboardButton(text="👨‍💼 Админ")],
    ],
    resize_keyboard=True,
)

# Новости ենթամենյու
news_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎬 Кино"), KeyboardButton(text="🎭 Театр")],
        [KeyboardButton(text="🍷 Бары и рестораны")],
        [KeyboardButton(text="🎉 Мероприятия")],
        [KeyboardButton(text="⬅️ В меню")],
    ],
    resize_keyboard=True,
)

# ==========================
#  STATES
# ==========================

class BotMode(StatesGroup):
    chat = State()      # ռեժիմ, որտեղ user-ը գրում է հարցեր «Бот»-ին

class FeedbackMode(StatesGroup):
    waiting_text = State()   # ռեժիմ, որտեղ սպասում ենք admin-ին նամակին


# ==========================
#  HELPERS
# ==========================

def is_trade_question(text: str) -> bool:
    trade_keywords = [
        "купить",
        "продать",
        "товар",
        "объявление",
        "куплю",
        "продаю",
        "акция",
        "скидка",
        "перепродажа",
        "срочно",
        "цена",
    ]
    return any(word in text.lower() for word in trade_keywords)


# ==========================
#  /START & BASIC COMMANDS
# ==========================

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    # Կարող ես LANG["ru"]["start"]‑ը փոխել, բայց reply_markup-ը թող սա լինի
    lang = detect_lang(message.from_user.language_code)
    text = (
        "🇪🇸 Добро пожаловать в Madrid Community Bot!\n\n"
        "Выберите режим:\n"
        "🤖 Бот — задайте любой городской вопрос\n"
        "📰 Новости — кино, театр, бары, мероприятия\n"
        "👨‍💼 Админ — написать администратору"
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

@dp.message(F.text == "🤖 Бот")
async def bot_mode_on(message: types.Message, state: FSMContext):
    await state.set_state(BotMode.chat)
    await message.answer(
        "Вы в режиме 🤖 Бот.\n"
        "Задайте вопрос, например: «Где можно покушать пиццу?»\n\n"
        "Чтобы вернуться в меню, нажмите любой из пунктов: 📰 Новости или 👨‍💼 Админ.",
        reply_markup=main_menu_keyboard,
    )


@dp.message(BotMode.chat)
async def bot_mode_chat(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    question_id = str(message.message_id)
    text = message.text

    # Այստեղ ընդհանուր քաղաքային հարցերի համար օգտագործում ենք search_type="city"
    bot_responder.add_question(user_id, text, question_id, search_type="city")

    await message.answer("Ищу для вас варианты и подсказки…")


# ==========================
#  📰 НОВОСТИ — EVENTS / КИНО / ТЕАТР / БАРЫ / МЕРОПРИЯТИЯ
# ==========================

@dp.message(F.text == "📰 Новости")
async def news_menu(message: types.Message):
    await message.answer(
        "Выберите раздел новостей:", reply_markup=news_keyboard
    )

@dp.message(F.text == "⬅️ В меню")
async def back_to_menu(message: types.Message):
    await message.answer(
        "Главное меню:", reply_markup=main_menu_keyboard
    )

# Կարճ /news command թողնենք, որ ուղիղ սրանից օգտվի
@dp.message(Command("news"))
async def news_cmd(message: types.Message):
    try:
        overview = build_city_overview_message()
        cinema = build_cinema_message(max_items=2)
        news_text = f"{overview}\n\n{cinema}"
        await message.answer(
            news_text, parse_mode="Markdown", disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"News error: {e}")
        await message.answer("📰 Новости временно недоступны")
    logger.info(f"User {message.from_user.id} requested news")


@dp.message(F.text == "🎬 Кино")
async def news_cinema(message: types.Message):
    try:
        cinema = build_cinema_message(max_items=5)
        await message.answer(
            cinema, parse_mode="Markdown", disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Cinema news error: {e}")
        await message.answer("🎬 Раздел «Кино» временно недоступен.")


@dp.message(F.text == "🎭 Театр")
async def news_theatre(message: types.Message):
    # Կարող ես նոր builder անել կամ reuse անել events.py-ից
    try:
        # placeholder — փոխես քո իրական ֆունկցիայով
        holidays = build_holidays_message(max_items=5)
        text = "🎭 *Театр и сцена Мадрида:*\n\n" + holidays
        await message.answer(
            text, parse_mode="Markdown", disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Theatre news error: {e}")
        await message.answer("🎭 Раздел «Театр» временно недоступен.")


@dp.message(F.text == "🍷 Бары и рестораны")
async def news_bars(message: types.Message):
    try:
        restaurants = build_restaurant_message(max_items=5)
        await message.answer(
            restaurants, parse_mode="Markdown", disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Restaurant news error: {e}")
        await message.answer("🍷 Раздел «Бары и рестораны» временно недоступен.")


@dp.message(F.text == "🎉 Мероприятия")
async def news_events(message: types.Message):
    try:
        holidays = build_holidays_message(max_items=5)
        text = "🎉 *Городские мероприятия и праздники:*\n\n" + holidays
        await message.answer(
            text, parse_mode="Markdown", disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Events news error: {e}")
        await message.answer("🎉 Раздел «Мероприятия» временно недоступен.")


# ==========================
#  🍽 COMIDA / FOOD SEARCH (Թողնում ենք, որ «Բոտ»-ին օգնի)
# ==========================

@dp.message(F.text.regexp(
    r"(бургер|пицца|суши|хачапури|паста|рамен|шаурма|плов|салат|стейк|гриль|мясо|рыба|бар|кофе|чай|вино|хинкали|шашлык|фалафель|тако|паэлья|енсалада|тамале|маки|роллы|гёдза|бонито|окономияки|блины|креветки|мидии|коктейль|завтрак|ужин|обед|фрукт|овощ|еда|ресторан|кафе|pizza|pasta|sushi|burger|ramen|steak|salad|bar|wine|coffee|tapas|paella|ensalada|shawarma|falafel|bistro|teriyaki|noodle|grill|bruschetta|curry|fish|meat|cheese|breakfast|dinner|lunch|fruit|vegetable|food|restaurant|cafe)"
))
async def food_search(message: types.Message):
    from backend.ai.food_reply import find_food_place

    query = message.text
    result = find_food_place(query)

    if not result or "name" not in result or not result["name"]:
        alt_reply = (
            "😥 По вашему запросу ничего не найдено.\n"
            "Попробуйте другой тип еды или поищите что-нибудь вкусненькое рядом!\n"
            "Например: 'пицца', 'суши', 'бургер', 'хачапури', 'паста'."
        )
        await message.answer(alt_reply)
        return

    name = result.get("name", "Неизвестно")
    address = result.get("address", "Без адреса")
    rating = result.get("rating", "Нет оценки")
    place_url = result.get("url", None)

    if not place_url:
        maps_url = (
            f"https://www.google.com/maps/search/?api=1&query={address.replace(' ', '+')}"
        )
    else:
        maps_url = place_url

    reply_text = (
        f"🍽 **Ресторан: {name}**\n"
        f"📍 **Адрес:** {address}\n"
        f"⭐ **Оценка:** {rating}\n"
        f"🗺 **Смотреть на карте:** {maps_url}"
    )
    await message.answer(reply_text, parse_mode="Markdown", disable_web_page_preview=True)

    if result.get("alternatives"):
        tips = "\n".join([f"- {alt}" for alt in result["alternatives"]])
        await message.answer(f"💡 **Вот еще несколько вариантов рядом:**\n{tips}")


# ==========================
#  👨‍💼 АДМИН — FEEDBACK
# ==========================

@dp.message(F.text == "👨‍💼 Админ")
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
#  FALLBACK MESSAGE HANDLER
# ==========================

@dp.message(F.text)
async def handle_message(message: types.Message):
    # Սա աշխատում է միայն եթե չենք BotMode.chat / FeedbackMode-ում
    keywords = save_message_with_analysis(message.from_user.id, message.text)
    question_id = str(message.message_id)
    user_id = message.from_user.id

    # Auto-responder logic
    if is_trade_question(message.text):
        bot_responder.add_question(
            user_id, message.text, question_id, search_type="item"
        )
    if "еда" in message.text.lower() or "food" in message.text.lower():
        bot_responder.add_question(
            user_id, message.text, question_id, search_type="food"
        )

    # Housing matching
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

    from backend.scheduler import start_scheduler  # lazy import
    start_scheduler(bot)

    logger.info("🚀 Starting Madrid Community Bot...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())

