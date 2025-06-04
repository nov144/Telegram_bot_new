import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Получаем токены и URL из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Например: https://mybot.onrender.com/webhook

# Создаём бота и диспетчер
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Хендлер на /start
@dp.message(Command("start"))
async def handle_start(message: types.Message):
    await message.answer("Привет!")

# Настройка aiohttp-сервера
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

# Создаём aiohttp-приложение
app = web.Application()
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)
setup_application(app, dp, bot=bot)

# Запуск
if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

