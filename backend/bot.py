import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from dotenv import load_dotenv

from backend.languages import LANG, detect_lang
from backend.jobs import add_offer, add_request, find_matches
from backend.news import format_manual_news
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

# --- АИ модуль
from backend.ai.response import QuestionAutoResponder
from backend.ai.traffic import madrid_morning_traffic

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

# --- Telegram menu в группе: на испанском!
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗓 Noticias culturales")],
        [KeyboardButton(text="🍽️ Comida")],
        [KeyboardButton(text="📨 Sugerencias y reclamaciones")]
    ],
    resize_keyboard=True
)

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))  # прописать свой id

bot_responder = QuestionAutoResponder(timeout=300)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    await message.answer(LANG[lang]["start"], reply_markup=menu_keyboard)
    logger.info(f"User {message.from_user.id} started bot")

@dp.message(Command("news"))
async def news_cmd(message: types.Message):
    news_text = format_manual_news()
    await message.answer(news_text, parse_mode="HTML")
    logger.info(f"User {message.from_user.id} requested news")

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    await message.answer(LANG[lang]["help"])
    logger.info(f"User {message.from_user.id} requested help")

# --- MENU HANDLERS

@dp.message(F.text == "🗓 Noticias culturales")
async def culture_news(message: types.Message):
    news = format_manual_news()
    await message.answer(news, parse_mode="HTML")

@dp.message(F.text == "🍽️ Comida")
async def food_help(message: types.Message):
    await message.answer("¿Qué quieres comer? Escribe el nombre del plato o tipo de comida (ejemplo: sushi, paella, pizza).")

@dp.message(F.text.regexp(r"(sushi|pizza|paella|hamburguesa|tapas|barbacoa|jamón|ensalada|бургер|пицца|суши|хачапури)"))
async def food_search(message: types.Message):
    from backend.ai.food_reply import find_food_place
    reply = find_food_place(message.text)
    await message.answer(reply)

@dp.message(F.text == "📨 Sugerencias y reclamaciones")
async def feedback(message: types.Message):
    await message.answer("[translate:Пожалуйста, напишите вашу жалобу или предложение. Оно будет отправлено напрямую администратору и не будет видно группе.]")

@dp.message(F.text.regexp(r'^.{10,}$'))  # feedback forwarding
async def forward_feedback(message: types.Message):
    if message.text == "📨 Sugerencias y reclamaciones":
        return  # чтобы не сработало на саму кнопку
    if ADMIN_CHAT_ID:
        await bot.send_message(ADMIN_CHAT_ID, f"[translate:Сообщение из группы]\n\n{message.text}")
    await message.answer("[translate:Ваше сообщение отправлено администратору.]")

# --- ОСТАЛЬНОЕ стандартное: offer/request/match/housing/etc

@dp.message(F.text.startswith("/offer "))
async def offer_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    text = message.text.replace("/offer ", "").strip()
    if not text:
        await message.answer(LANG[lang].get("empty_offer", "Please provide offer details"))
        return
    add_offer(message.from_user.id, text)
    await message.answer(LANG[lang]["offer_saved"])
    logger.info(f"User {message.from_user.id} added offer: {text[:50]}")

@dp.message(F.text.startswith("/request "))
async def request_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    text = message.text.replace("/request ", "").strip()
    if not text:
        await message.answer(LANG[lang].get("empty_request", "Please provide request details"))
        return
    add_request(message.from_user.id, text)
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
    for req, off in matches:
        msg += f"👤 Request: {req['text']}\n💼 Offer: {off['text']}\n---\n"
    await message.answer(msg)
    logger.info(f"User {message.from_user.id} checked matches: {len(matches)} found")

@dp.message(F.new_chat_members)
async def welcome_new_member(message: types.Message):
    for new_member in message.new_chat_members:
        if new_member.id == bot.id:
            continue
        username = new_member.username if new_member.username else new_member.first_name
        mention = f"@{username}" if new_member.username else new_member.first_name
        welcome_text = (
            f"[translate:🎉 Добро пожаловать, {mention}!\n"
            f"Мы рады приветствовать нового участника! "
            f"Надеемся, что наша группа будет полезна для вас и вы найдёте здесь всё, что ищете.\n"
            f"💬 Не стесняйтесь задавать вопросы\n"
            f"🤝 Делитесь опытом с другими участниками\n"
            f"📢 Следите за полезными новостями\n\n"
            f"Спасибо, что присоединились к нам! 🇪🇸]"
        )
        await message.answer(welcome_text, parse_mode="HTML")
        logger.info(f"Welcomed new member: {username} (ID: {new_member.id})")

@dp.message(F.text)
async def handle_message(message: types.Message):
    keywords = save_message_with_analysis(message.from_user.id, message.text)
    question_id = str(message.message_id)
    user_id = message.from_user.id
    from backend.matching import is_housing_offer, is_housing_request
    if is_trade_question(message.text):
        bot_responder.add_question(user_id, message.text, question_id, search_type="item")
    if is_food_question(message.text):
        bot_responder.add_question(user_id, message.text, question_id, search_type="food")
    if keywords.get('housing'):
        if is_housing_offer(message.text):
            offer_data = parse_housing_offer(message.text)
            matches = find_matching_requests(offer_data)
            if matches:
                match_count = len(matches)
                await message.reply(
                    f"[translate:🏠 {match_count} пользователей ищут похожее жильё!]\n\n"
                    f"[translate:Администратор свяжет вас с заинтересованными.]",
                    parse_mode="HTML"
                )
        elif is_housing_request(message.text):
            request_data = parse_housing_offer(message.text)
            matches = find_matching_offers(request_data)
            if matches:
                match_count = len(matches)
                await message.reply(
                    f"[translate:🏠 {match_count} предложений по вашим параметрам найдено!]\n\n"
                    f"[translate:Администратор свяжет вас с владельцами.]",
                    parse_mode="HTML"
                )

async def main():
    init_db()
    start_scheduler(bot)
    logger.info("Starting bot...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
