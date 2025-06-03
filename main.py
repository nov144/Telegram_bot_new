import os
import json
import base64
from datetime import datetime
import asyncio

import gspread
from google.oauth2.service_account import Credentials

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from aiogram_calendar import SimpleCalendar

# ENV
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
creds_base64 = os.getenv("GOOGLE_CREDS_BASE64")

# Google Sheets
credentials = Credentials.from_service_account_info(
    json.loads(base64.b64decode(creds_base64)),
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gclient = gspread.authorize(credentials)
sheet = gclient.open_by_key(SPREADSHEET_ID).sheet1

# FSM
class BookingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_phone = State()

# Bot
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

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
    # Для теста временно убираем проверку FSM-состояния
    selected, date = await SimpleCalendar().process_selection(callback, callback.data)
    print("DEBUG CALENDAR selected:", selected, date)

    if not selected:
        await callback.answer()
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

    summary = f"Запись подтверждена!\nИмя: {name}\nДата: {date}\nТелефон: {phone}"

    try:
        sheet.append_row([name, date, phone, timestamp])
    except Exception as e:
        await message.answer(f"Ошибка при записи в таблицу: {e}")
        return

    await message.answer(summary)
    await bot.send_message(chat_id=-1002293928496, text=summary)
    await state.clear()

# Для отладки — перехватываем все callback
@router.callback_query()
async def catch_all_callbacks(callback: CallbackQuery):
    print("📥 Callback data:", callback.data)
    await callback.answer()

# Webhook
async def on_startup(_: web.Application):
    await bot.set_webhook(WEBHOOK_URL)

async def print_webhook_info(app: web.Application):
    await asyncio.sleep(2)
    info = await bot.get_webhook_info()
    print("Webhook:", info.url)

app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/")
setup_application(app, dp, bot=bot)
app.on_startup.append(on_startup)
app.on_startup.append(print_webhook_info)

if __name__ == "__main__":
    web.run_app(app, port=8000)

