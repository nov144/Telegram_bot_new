import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.web.middlewares import SimpleRequestHandler, setup_application
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # пример: https://your-app.onrender.com/

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Обработчик команды /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("Привет, я бот!")

# Webhook: при запуске
async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)

# Webhook: при завершении
async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    await bot.session.close()

# Настройка приложения aiohttp
def setup_app(app: web.Application):
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    setup_application(app, dp)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/")

# Точка входа
async def create_app():
    app = web.Application()
    setup_app(app)
    return app

if __name__ == "__main__":
    web.run_app(create_app())
