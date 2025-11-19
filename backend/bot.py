from .languages import LANG, detect_lang
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F

from .news import fetch_madrid_news
from .jobs import add_offer, add_request, find_matches

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN missing in environment variables")

bot = Bot(TOKEN)
dp = Dispatcher()

# /start
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    await message.answer(LANG[lang]["start"])

# /news
@dp.message(Command("news"))
async def news_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    news = fetch_madrid_news()
    await message.answer(f"{LANG[lang]['news']}\n\n{news}")

# /offer
@dp.message(F.text.startswith("/offer "))
async def offer_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    text = message.text.replace("/offer ", "")
    add_offer(message.from_user.id, text)
    await message.answer(LANG[lang]["offer_saved"])

# /request
@dp.message(F.text.startswith("/request "))
async def request_cmd(message: types.Message):
    lang = detect_lang(message.from_user.language_code)
    text = message.text.replace("/request ", "")
    add_request(message.from_user.id, text)
    await message.answer(LANG[lang]["request_saved"])

# /match
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

# fallback
@dp.message(F.text)
async def echo(message: types.Message):
    await message.answer("Քեզ լսում եմ, Սաքո։")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
