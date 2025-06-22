import logging
from aiogram import Bot, Dispatcher, executor, types
import os

API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

WELCOME_MESSAGE = (
    "👋 Привет! Я — AgentHelpBot.\n"
    "Этот бот создан для помощи авиаагентам в расшифровке GDS-сегментов, маршрутов, дат, кодов и других данных.\n\n"
    "Бот пока работает *абсолютно бесплатно* и доступен 24/7.\n"
    "Просто пришлите мне текст бронирования — и я всё объясню по-человечески.\n\n"
    "===========================\n"
    "👋 Hello! I’m AgentHelpBot.\n"
    "This bot is designed to help travel agents decode GDS segments, routes, dates, airline codes and more.\n\n"
    "The bot is currently *completely free* and available 24/7.\n"
    "Just send me the booking text — and I’ll explain it in plain language!"
)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply(WELCOME_MESSAGE, parse_mode="Markdown")

@dp.message_handler()
async def echo(message: types.Message):
    await message.answer("🔍 Обрабатываю запрос... (будет расшифровка)")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
