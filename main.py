import os
import logging
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Логи
logging.basicConfig(level=logging.INFO)

# Базовая настройка
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# Обработка /start
@router.message(F.text == "/start")
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[KeyboardButton(text="Записаться")]]
    )
    await message.answer("Привет! Я бот для записи к мастеру. Нажмите кнопку ниже:", reply_markup=kb)

# Обработка "Записаться"
@router.message(F.text == "Записаться")
async def booking(message: types.Message):
    await message.answer("Вы нажали кнопку записаться ✅")

# Webhook запуск
async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)

def setup_app(app: web.Application):
    dp.startup.register(on_startup)
    setup_application(app, dp, bot=bot)

async def create_app():
    app = web.Application()
    setup_app(app)
    return app

if __name__ == "__main__":
    web.run_app(create_app())
