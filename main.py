
import os
import json
import base64
from datetime import datetime

import gspread
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from google.oauth2.service_account import Credentials
from aiogram_calendar import SimpleCalendar

# ENV
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
creds_base64 = os.getenv("GOOGLE_CREDS_BASE64")

# Google Sheets Auth
creds_json = json.loads(base64.b64decode(creds_base64))
credentials = Credentials.from_service_account_info(creds_json, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# FSM States
class BookingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_phone = State()

# Setup
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# Start Command
@router.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await message.answer("Как вас зовут?")
    await state.set_state(BookingStates.waiting_for_name)

@router.message(BookingStates.waiting_for_name)
async def ask_date(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Выберите дату:", reply_markup=await SimpleCalendar().start_calendar())
    await state.set_state(BookingStates.waiting_for_date)

@router.callback_query(F.data.startswith("CALENDAR"))
async def select_date(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    print(f"📌 State: {current_state}")
    print(f"📌 Callback: {callback.data}")

    if current_state != BookingStates.waiting_for_date.state:
        await state.set_state(BookingStates.waiting_for_date)
        print("🔄 FSM state recovered to 'waiting_for_date'")

    selected, date = await SimpleCalendar().process_selection(callback)
    if not selected:
        return

    await state.update_data(date=str(date))
    await callback.message.answer(f"Вы выбрали: {date.strftime('%d.%m.%Y')}")
    await callback.message.answer("Введите номер телефона:")
    await state.set_state(BookingStates.waiting_for_phone)
    await callback.answer()

@router.message(BookingStates.waiting_for_phone)
async def ask_phone(message: Message, state: FSMContext):
    data = await state.update_data(phone=message.text)
    data = await state.get_data()

    name = data["name"]
    date = data["date"]
    phone = data["phone"]
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    sheet.append_row([name, date, phone, timestamp])
    await message.answer(f"<b>Запись подтверждена!</b>")

Имя: {name}
Дата: {date}
Телефон: {phone}", parse_mode="HTML")
    await state.clear()

# Webhook init
async def on_startup(app: web.Application):
    await bot.set_webhook(WEBHOOK_URL)

app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/")
setup_application(app, dp, bot=bot)
app.on_startup.append(on_startup)

if __name__ == "__main__":
    web.run_app(app, port=8000)



