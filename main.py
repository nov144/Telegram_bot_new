import os
import json
import base64
import asyncio
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

from aiogram_calendar import SimpleCalendar
from google.oauth2.service_account import Credentials

# ==== BOT STARTUP ====
print("🚀 BOT LAUNCH STARTED")

BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
creds_base64 = os.getenv("GOOGLE_CREDS_BASE64")

print("🔑 BOT_TOKEN present:", BOT_TOKEN is not None)
print("🗂️  SPREADSHEET_ID present:", SPREADSHEET_ID is not None)
print("🌐 WEBHOOK_URL present:", WEBHOOK_URL is not None)
print("🔐 GOOGLE_CREDS_BASE64 present:", creds_base64 is not None)

# ==== GOOGLE SHEETS SETUP ====
try:
    creds_json = json.loads(base64.b64decode(creds_base64))
    credentials = Credentials.from_service_account_info(creds_json, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gclient = gspread.authorize(credentials)
    spreadsheet = gclient.open_by_key(SPREADSHEET_ID)
    sheet = spreadsheet.sheet1
    print("✅ Таблица открыта успешно:", spreadsheet.title)
except Exception as e:
    print("❌ Ошибка при настройке Google Sheets:", e)

# ==== FSM STATES ====
class BookingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_phone = State()

# ==== AIOGRAM SETUP ====
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# ==== COMMAND /start ====
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await message.answer("Как вас зовут?")
    await state.set_state(BookingStates.waiting_for_name)

# ==== NAME ====
@router.message(BookingStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Пожалуйста, выберите дату:", reply_markup=await SimpleCalendar().start_calendar())
    await state.set_state(BookingStates.waiting_for_date)

# ==== CALENDAR CALLBACK ====
@router.callback_query(F.data.startswith("simple_calendar"))
async def process_date(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != BookingStates.waiting_for_date.state:
        return

    selected, date = await SimpleCalendar().process_selection(callback, callback.data)
    if not selected:
        await callback.answer()  # чтобы убрать "часики"
        return

    await state.update_data(date=str(date))
    await callback.message.answer(f"Вы выбрали: {date.strftime('%d.%m.%Y')}")
    await state.set_state(BookingStates.waiting_for_phone)
    await callback.message.answer("Введите номер телефона:")


# ==== PHONE ====
@router.message(BookingStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("name")
    date = data.get("date")
    phone = message.text
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    try:
        sheet.append_row([name, date, phone, timestamp])
        await message.answer(f"<b>Запись подтверждена!</b>\nИмя: {name}\nДата: {date}\nТелефон: {phone}")
        await bot.send_message(chat_id=-1002293928496, text=f"<b>Запись подтверждена!</b>\nИмя: {name}\nДата: {date}\nТелефон: {phone}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при записи в таблицу: {e}")

    await state.clear()

# ==== WEBHOOK SETUP ====
async def on_startup(_: web.Application):
    await bot.set_webhook(WEBHOOK_URL)

async def print_webhook_info(_: web.Application):
    await asyncio.sleep(2)
    info = await bot.get_webhook_info()
    print("📬 Webhook Info:")
    print(f"🔗 URL: {info.url}")
    print(f"📎 Has certificate: {info.has_custom_certificate}")
    print(f"⏳ Pending updates: {info.pending_update_count}")

app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/")
setup_application(app, dp, bot=bot)
app.on_startup.append(on_startup)
app.on_startup.append(print_webhook_info)

if __name__ == "__main__":
    web.run_app(app, port=8000)
