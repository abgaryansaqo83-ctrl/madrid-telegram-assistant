import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("🤖 Madrid assistant is online, hermano Saqo!")

@dp.message(F.text)
async def echo(message: types.Message):
    await message.answer("Քեզ լսում եմ, Սաքո։ Ինչ պետք ա՝ ասա։")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
