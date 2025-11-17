import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F

from news import fetch_madrid_news
from jobs import add_offer, add_request, find_matches

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(TOKEN)
dp = Dispatcher()

# /start
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("🤖 Madrid assistant is online, Սաքո։ Ինչ պետք է՝ ասա։")

# /news
@dp.message(Command("news"))
async def news_cmd(message: types.Message):
    news = fetch_madrid_news()
    await message.answer(f"🌇 Madrid News:\n\n{news}")

# /offer (user gives job offer)
@dp.message(F.text.startswith("/offer "))
async def offer_cmd(message: types.Message):
    text = message.text.replace("/offer ", "")
    add_offer(message.from_user.id, text)
    await message.answer("📌 Գործի առաջարկը պահվեց, Սաքո։")

# /request (user needs a job)
@dp.message(F.text.startswith("/request "))
async def request_cmd(message: types.Message):
    text = message.text.replace("/request ", "")
    add_request(message.from_user.id, text)
    await message.answer("🔎 Գործի որոնումն ավելացված է, Սաքո։")

# /match (find job matches)
@dp.message(Command("match"))
async def match_cmd(message: types.Message):
    matches = find_matches()
    if not matches:
        await message.answer("🤷‍♂️ Համապատասխանություններ չկան։")
        return

    msg = "🎯 Matches Found:\n\n"
    for req, off in matches:
        msg += f"👤 Request: {req['text']}\n💼 Offer: {off['text']}\n---\n"
    await message.answer(msg)

# echo fallback
@dp.message(F.text)
async def echo(message: types.Message):
    await message.answer("Քեզ լսում եմ, Սաքո։")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
