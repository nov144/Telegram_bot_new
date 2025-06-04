import os
import logging

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.enums import ParseMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# === Настройка логов ===
logging.basicConfig(level=logging.INFO)

# === Инициализация бота и диспетчера ===
bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# === Обработка команды /start ===
@router.message(F.text == "/start")
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[KeyboardButton(text="Записаться")]])
    await message.answer("Привет! Я бот для записи. Нажмите 'Записаться', чтобы продолжить.", reply_markup=keyboard)

# === Ответ на кнопку 'Записаться' ===
@router.message(F.text == "Записаться")
async def booking_handler(message: types.Message):
    await message.answer("Вы хотите записаться. Функционал скоро будет доступен!")

# === Webhook: Запуск приложения ===
async def on_startup(bot: Bot):
    webhook_url = os.getenv("WEBHOOK_URL")
    await bot.set_webhook(webhook_url)

async def create_app():
    app = web.Application()
    dp.startup.register(on_startup)
    from aiogram.web.middlewares import SimpleRequestHandler, setup_application
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/")
    setup_application(app, dp)
    return app

if __name__ == "__main__":
    web.run_app(create_app())
