import os
import logging
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from aiohttp import web

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, CallbackQuery
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from simple_calendar import SimpleCalendar, simple_cal_callback

# === Логгирование ===
logging.basicConfig(level=logging.INFO)

# === Google Sheets ===
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# === Бот и Диспетчер ===
bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# === Состояния ===
class BookingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_phone = State()

# === Обработчики ===
@router.message(F.text == "/start")
async def start_handler(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[KeyboardButton(text="Записаться")]])
    await message.answer("Привет! Я бот для записи к мастеру. Выберите действие:", reply_markup=kb)

@router.message(F.text == "Записаться")
async def start_booking(message: types.Message, state: FSMContext):
    await state.set_state(BookingStates.waiting_for_name)
    await message.answer("Как вас зовут?")

@router.message(BookingStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(BookingStates.waiting_for_date)
    await message.answer("Пожалуйста, выберите дату:", reply_markup=ReplyKeyboardRemove())
    await message.answer("📅", reply_markup=await SimpleCalendar().start_calendar())

@router.callback_query(simple_cal_callback.filter(), BookingStates.waiting_for_date)
async def process_date(callback: CallbackQuery, callback_data: dict, state: FSMContext):
    calendar = SimpleCalendar()
    selected, date = await calendar.process_selection(callback, callback_data)

    if not selected:
        await callback.answer()
        return

    await state.update_data(date=str(date))
    await callback.message.answer(f"Вы выбрали: {date.strftime('%d.%m.%Y')}")
    await callback.message.answer("Введите номер телефона:")
    await state.set_state(BookingStates.waiting_for_phone)
    await callback.answer()

@router.message(BookingStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    name, date, phone = data["name"], data["date"], data["phone"]
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    sheet.append_row([name, date, phone, timestamp])

    summary = f"Запись подтверждена!\n\nИмя: {name}\nДата: {date}\nТелефон: {phone}"
    await message.answer(summary)
    await bot.send_message(-1002293928496, summary)
    await bot.send_message(300466559, summary)
    await state.clear()

# === Webhook настройки ===
async def on_startup(bot: Bot):
    await bot.set_webhook(os.getenv("WEBHOOK_URL"))

def setup_app(app: web.Application):
    dp.startup.register(on_startup)
    app["bot"] = bot
    app["dispatcher"] = dp

    SimpleRequestHandler(dispatcher=dp, bot=bot, path="/").register(app)
    setup_application(app, dp)

async def create_app():
    app = web.Application()
    setup_app(app)
    return app

if __name__ == "__main__":
    web.run_app(create_app())
