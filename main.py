import os
import logging
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.enums import ParseMode
from aiogram.web.middlewares import SimpleRequestHandler, setup_application
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

# === Логгирование ===
logging.basicConfig(level=logging.INFO)

# === Инициализация бота ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

# === Обработчик /start ===
@router.message(F.text == "/start")
async def start_handler(message: types.Message):
    await message.answer("Привет!")

# === Webhook setup ===
async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    await bot.session.close()

def setup_app(app: web.Application):
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    setup_application(app, dp)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/")

async def create_app() -> web.Application:
    app = web.Application()
    setup_app(app)
    return app

if __name__ == "__main__":
    web.run_app(create_app())

