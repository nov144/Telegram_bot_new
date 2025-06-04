import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram_calendar.simple_calendar import SimpleCalendar, SimpleCalendarCallback
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.webhook.aiohttp_server import setup_application
from aiohttp import web
import asyncio
import os

# FSM состояние
from aiogram.fsm.state import State, StatesGroup

class AppointmentState(StatesGroup):
    choosing_date = State()

# Токен и Webhook
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://your-app-name.onrender.com{WEBHOOK_PATH}"

# Инициализация
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# Старт
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(AppointmentState.choosing_date)
    calendar = SimpleCalendar()
    markup = await calendar.start_calendar()
    await message.answer("Выберите дату:", reply_markup=markup)

# Обработка выбора даты
@router.callback_query(SimpleCalendarCallback.filter())
async def process_date(callback: CallbackQuery, state: FSMContext):
    calendar = SimpleCalendar()
    selected, date = await calendar.process_selection(callback)
    if selected:
        await state.update_data(appointment_date=str(date))
        await callback.message.answer(f"Вы выбрали дату: {date.strftime('%d.%m.%Y')}")
        await callback.answer()

# Webhook сервер
async def on_startup(app: web.Application):
    await bot.set_webhook(WEBHOOK_URL)

def create_app():
    app = web.Application()
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    web.run_app(app, port=8000)
