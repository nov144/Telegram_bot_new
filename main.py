import logging
import os
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram import Router
from aiogram.fsm.state import State, StatesGroup
from simple_calendar import SimpleCalendar, simple_cal_callback
from aiogram.client.default import DefaultBotProperties

# === Логи ===
logging.basicConfig(level=logging.INFO)

# === Google Sheets ===
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# === Бот и диспетчер ===
bot = Bot(token=os.getenv("BOT_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# === Состояния ===
class BookingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_phone = State()

# === /start ===
@router.message(F.text == "/start")
async def start_handler(message: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Записаться")]],
        resize_keyboard=True
    )
    await message.answer("Привет! Я бот для записи к мастеру. Выберите действие:", reply_markup=kb)

# === Запись ===
@router.message(F.text == "Записаться")
async def start_booking(message: types.Message, state: FSMContext):
    await state.set_state(BookingStates.waiting_for_name)
    await message.answer("Как вас зовут?")

@router.message(BookingStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(BookingStates.waiting_for_date)
    await message.answer("Пожалуйста, выберите дату:", reply_markup=ReplyKeyboardRemove())
    await message.answer("\U0001F4C5", reply_markup=await SimpleCalendar().start_calendar())

@router.callback_query(simple_cal_callback.filter(), BookingStates.waiting_for_date)
async def process_date(callback: CallbackQuery, callback_data: dict, state: FSMContext):
    logging.info("\U0001F514 Обработчик календаря вызван")
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
    name = data["name"]
    date = data["date"]
    phone = data["phone"]
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    sheet.append_row([name, date, phone, timestamp])

    summary = f"Запись подтверждена!\n\nИмя: {name}\nДата: {date}\nТелефон: {phone}"
    await message.answer(summary)

    await bot.send_message(-1002293928496, summary)  # группа
    await bot.send_message(300466559, summary)       # мастер

    await state.clear()

# === Запуск ===
if __name__ == "__main__":
    import asyncio
    from aiogram.webhook.aiohttp_server import setup_application
    from aiohttp import web

    async def main():
        app = web.Application()
        app['bot'] = bot
        await setup_application(app, dp)

        webhook_url = os.getenv("WEBHOOK_URL")
        await bot.set_webhook(webhook_url)

        logging.info("Starting webhook on /")
        return app

    web.run_app(main())
