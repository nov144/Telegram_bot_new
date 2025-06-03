import os
print("=== START FILE ===")

import gspread
from datetime import datetime
import base64
import json
import asyncio

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from aiogram_calendar import SimpleCalendar
from google.oauth2.service_account import Credentials

# ENV Variables
print("\ud83d\ude80 BOT LAUNCH STARTED")

BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

print("\ud83d\udd11 BOT_TOKEN present:", BOT_TOKEN is not None)
print("\ud83d\uddc2\ufe0f  SPREADSHEET_ID present:", SPREADSHEET_ID is not None)
print("\ud83c\udf10 WEBHOOK_URL present:", WEBHOOK_URL is not None)

# Google Sheets Setup
try:
    creds_base64 = os.getenv("GOOGLE_CREDS_BASE64")
    print("\ud83d\udd0d GOOGLE_CREDS_BASE64 present:", creds_base64 is not None)
    creds_json = json.loads(base64.b64decode(creds_base64))
    credentials = Credentials.from_service_account_info(creds_json, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gclient = gspread.authorize(credentials)

    print("DEBUG SPREADSHEET_ID =", SPREADSHEET_ID)
    spreadsheet = gclient.open_by_key(SPREADSHEET_ID)
    sheet = spreadsheet.sheet1
    print("\u2705 \u0422\u0430\u0431\u043b\u0438\u0446\u0430 \u043e\u0442\u043a\u0440\u044b\u0442\u0430 \u0443\u0441\u043f\u0435\u0448\u043d\u043e:", spreadsheet.title)
except Exception as e:
    print("\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0435 Google Sheets:", e)


# FSM States
class BookingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_phone = State()

# Bot Setup
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Handlers
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await message.answer("Как вас зовут?")
    await state.set_state(BookingStates.waiting_for_name)


@router.message(BookingStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Пожалуйста, выберите дату:", reply_markup=await SimpleCalendar().start_calendar())
    await state.set_state(BookingStates.waiting_for_date)


@router.callback_query(F.data.startswith("CALENDAR"))
async def process_date(callback: CallbackQuery, state: FSMContext):
    print("\ud83d\uddd3\ufe0f CALENDAR CALLBACK TRIGGERED:", callback.data)
    current_state = await state.get_state()
    if current_state != BookingStates.waiting_for_date.state:
        return

    selected, date = await SimpleCalendar().process_selection(callback, callback.data)
    if not selected:
        return

    await state.update_data(date=str(date))
    await callback.message.answer(f"Вы выбрали: {date.strftime('%d.%m.%Y')}")
    await state.set_state(BookingStates.waiting_for_phone)
    await callback.answer()
    await callback.message.answer("Введите номер телефона:")


@router.message(BookingStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text
    await state.update_data(phone=phone)
    data = await state.get_data()

    name = data["name"]
    date = data["date"]
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    summary = f"<b>Запись подтверждена!</b>\nИмя: {name}\nДата: {date}\nТелефон: {phone}"

    try:
        sheet.append_row([name, date, phone, timestamp])
    except Exception as e:
        await message.answer(f"\u274c Ошибка при записи в таблицу: {e}")
        return

    await message.answer(summary)
    await bot.send_message(chat_id=-1002293928496, text=summary)
    await state.clear()


# Webhook Setup
async def on_startup(_: web.Application):
    await bot.set_webhook(WEBHOOK_URL)

async def print_webhook_info(app: web.Application):
    await asyncio.sleep(2)
    info = await bot.get_webhook_info()
    print("\ud83d\udcec Webhook Info:")
    print(f"\ud83d\udd17 URL: {info.url}")
    print(f"\ud83d\udccc Has certificate: {info.has_custom_certificate}")
    print(f"\u23f3 Pending updates: {info.pending_update_count}")

app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/")
setup_application(app, dp, bot=bot)
app.on_startup.append(on_startup)
app.on_startup.append(print_webhook_info)

if __name__ == "__main__":
    web.run_app(app, port=8000)

