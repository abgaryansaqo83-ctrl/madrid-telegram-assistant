import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F
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
    is_housing_request
)
from backend.scheduler import start_scheduler, stop_scheduler
from backend.ai.response import QuestionAutoResponder
from backend.ai.traffic import madrid_morning_traffic
# ՆՈՐ NEWS BUILDER-ՆԵՐ
from backend.news import (
    build_city_overview_message,
    build_cinema_message,
    build_restaurant_message,
    build_holidays_message
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN missing in environment variables")

bot = Bot(TOKEN)
dp = Dispatcher()

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗓 Noticias culturales")],
        [KeyboardButton(text="🍽️ Comida")],
        [KeyboardButton(text="📨 Sugerencias y reclamaciones")]
    ],
    resize_keyboard=True
)

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
bot_responder = QuestionAutoResponder(timeout=300)

# Պարզ checker առևտրային հարցերի համար
def is_trade_question(text):
    trade_keywords = ["купить", "продать", "товар", "объявление", "куплю", "продаю", "акция", "скидка", "перепродажа", "срочно", "Цена"]
    return any(word in text.lower() for word in trade_keywords)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    await message.answer(LANG[lang]["start"], reply_markup=menu_keyboard)
    logger.info(f"User {message.from_user.id} started bot")

@dp.message(Command("news"))
async def news_cmd(message: types.Message):
    # Փոխվել է format_manual_news-ից դեպի նոր builder
    try:
        overview = build_city_overview_message()
        cinema = build_cinema_message(max_items=2)
        news_text = f"{overview}\n\n{cinema}"
        await message.answer(news_text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"News error: {e}")
        await message.answer("📰 Новости временно недоступны")
    logger.info(f"User {message.from_user.id} requested news")

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    await message.answer(LANG[lang]["help"])
    logger.info(f"User {message.from_user.id} requested help")

@dp.message(F.text == "🗓 Noticias culturales")
async def culture_news(message: types.Message):
    # Նույնը, ինչ /news, բայց կենտրոնացած cultural events-ի վրա
    try:
        cinema = build_cinema_message(max_items=3)
        holidays = build_holidays_message(max_items=2)
        news_text = f"🎭 **Cultural Events**\n\n{cinema}\n\n{holidays}"
        await message.answer(news_text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Cultural news error: {e}")
        await message.answer("🎭 Cultural events temporarily unavailable")
    logger.info(f"User {message.from_user.id} requested cultural news")

@dp.message(F.text == "🍽️ Comida")
async def food_help(message: types.Message):
    await message.answer("¿Qué quieres comer? Escribe el nombre del plato o tipo de comida (ejemplo: sushi, paella, pizza, бургер, паста, шаурма).")

@dp.message(F.text.regexp(
    r"(бургер|пицца|суши|хачапури|паста|рамен|шаурма|плов|салат|стейк|гриль|мясо|рыба|бар|кофе|чай|вино|хинкали|шашлык|фалафель|тако|паэлья|енсалада|тамале|маки|роллы|гёдза|бонито|окономияки|блины|креветки|мидии|коктейль|завтрак|ужин|обед|фрукт|овощ|еда|ресторан|кафе|pizza|pasta|sushi|burger|ramen|steak|salad|bar|wine|coffee|tapas|paella|ensalada|shawarma|falafel|bistro|teriyaki|noodle|grill|bruschetta|curry|fish|meat|cheese|breakfast|dinner|lunch|fruit|vegetable|food|restaurant|cafe)"
))
async def food_search(message: types.Message):
    from backend.ai.food_reply import find_food_place
    query = message.text
    result = find_food_place(query)
    if not result or 'name' not in result or not result['name']:
        alt_reply = (
            "😥 По вашему запросу ничего не найдено.\n"
            "Попробуйте другой тип еды или просто поищите что-нибудь вкусненькое рядом!\n"
            "Например: 'пицца', 'суши', 'бургер', 'хачапури', 'паста'."
        )
        await message.answer(alt_reply)
        return
    name = result.get('name', 'Неизвестно')
    address = result.get('address', 'Без адреса')
    rating = result.get('rating', 'Нет оценки')
    place_url = result.get('url', None)
    if not place_url:
        maps_url = f"https://www.google.com/maps/search/?api=1&query={address.replace(' ', '+')}"
    else:
        maps_url = place_url
    reply_text = (
        f"🍽 **Ресторан: {name}**\n"
        f"📍 **Адрес:** {address}\n"
        f"⭐ **Оценка:** {rating}\n"
        f"🗺 **Смотреть на карте:** {maps_url}"
    )
    await message.answer(reply_text, parse_mode="Markdown", disable_web_page_preview=True)
    if result.get('alternatives'):
        tips = "\n".join([f"- {alt}" for alt in result['alternatives']])
        await message.answer(f"💡 **Вот еще несколько вариантов рядом:**\n{tips}")

@dp.message(F.text == "📨 Sugerencias y reclamaciones")
async def feedback(message: types.Message):
    await message.answer("Пожалуйста, напишите вашу жалобу или предложение. Оно будет отправлено напрямую администратору и не будет видно группе.")

@dp.message(F.text.regexp(r'^.{10,}$'))
async def forward_feedback(message: types.Message):
    if message.text == "📨 Sugerencias y reclamaciones":
        return
    if ADMIN_CHAT_ID:
        await bot.send_message(ADMIN_CHAT_ID, f"💬 **Сообщение из группы**\n\n{message.text}")
    await message.answer("✅ Ваше сообщение отправлено администратору.")

@dp.message(F.text.startswith("/offer "))
async def offer_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    text = message.text.replace("/offer ", "").strip()
    if not text:
        await message.answer(LANG[lang].get("empty_offer", "Please provide offer details"))
        return
    add_offer(message.from_user, text)  # Այժմ user object է փոխանցում
    await message.answer(LANG[lang]["offer_saved"])
    logger.info(f"User {message.from_user.id} added offer: {text[:50]}")

@dp.message(F.text.startswith("/request "))
async def request_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    text = message.text.replace("/request ", "").strip()
    if not text:
        await message.answer(LANG[lang].get("empty_request", "Please provide request details"))
        return
    add_request(message.from_user, text)  # Այժմ user object է փոխանցում
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
    for req, off in matches[:5]:  # Limit to 5 matches
        msg += f"👤 **Request:** {req['text'][:100]}...\n💼 **Offer:** {off['text'][:100]}...\n---\n"
    await message.answer(msg, parse_mode="Markdown")
    logger.info(f"User {message.from_user.id} checked matches: {len(matches)} found")

@dp.message(F.new_chat_members)
async def welcome_new_member(message: types.Message):
    for new_member in message.new_chat_members:
        if new_member.id == (await bot.get_me()).id:
            continue
        username = new_member.username if new_member.username else new_member.first_name
        mention = f"@{username}" if new_member.username else new_member.first_name
        welcome_text = (
            f"🎉 **Добро пожаловать, {mention}!**\n\n"
            f"Мы рады приветствовать нового участника! "
            f"Надеемся, что наша группа будет полезна для вас и вы найдёте здесь всё, что ищете.\n\n"
            f"💬 **Не стесняйтесь задавать вопросы**\n"
            f"🤝 **Делитесь опытом с другими участниками**\n"
            f"📢 **Следите за полезными новостями**\n\n"
            f"Спасибо, что присоединились к нам! 🇪🇸"
        )
        await message.answer(welcome_text, parse_mode="Markdown")
        logger.info(f"Welcomed new member: {username} (ID: {new_member.id})")

@dp.message(F.text)
async def handle_message(message: types.Message):
    keywords = save_message_with_analysis(message.from_user.id, message.text)
    question_id = str(message.message_id)
    user_id = message.from_user.id
    
    # Auto-responder logic
    if is_trade_question(message.text):
        bot_responder.add_question(user_id, message.text, question_id, search_type="item")
    if "еда" in message.text.lower() or "food" in message.text.lower():
        bot_responder.add_question(user_id, message.text, question_id, search_type="food")
    
    # Housing matching
    if keywords.get('housing'):
        if is_housing_offer(message.text):
            offer_data = parse_housing_offer(message.text)
            matches = find_matching_requests(offer_data)
            if matches:
                match_count = len(matches)
                await message.reply(
                    f"🏠 **{match_count} пользователей ищут похожее жильё!**\n\n"
                    f"Администратор свяжет вас с заинтересованными.",
                    parse_mode="Markdown"
                )
        elif is_housing_request(message.text):
            request_data = parse_housing_offer(message.text)
            matches = find_matching_offers(request_data)
            if matches:
                match_count = len(matches)
                await message.reply(
                    f"🏠 **{match_count} предложений по вашим параметрам найдено!**\n\n"
                    f"Администратор свяжет вас с владельцами.",
                    parse_mode="Markdown"
                )

async def main():
    # Initialize all DBs
    init_db()
    init_jobs_schema()  # Նոր jobs schema init
    start_scheduler(bot)
    logger.info("🚀 Starting Madrid Community Bot...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
