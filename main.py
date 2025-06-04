import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram_calendar import SimpleCalendar
from aiohttp import web
import gspread
from google.oauth2.service_account import Credentials
import base64
import json
import os

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# === FSM ===
class BookingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_phone = State()

# === Логгер ===
logging.basicConfig(level=logging.INFO)

# === Google Sheets через base64 ===
creds_base64 = os.getenv("GOOGLE_CREDS_BASE64")
creds_dict = json.loads(base64.b64decode(creds_base64))
credentials = Credentials.from_service_account_info(creds_dict, scopes=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
])
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(os.getenv("SHEET_ID")).sheet1

# === Бот и Диспетчер ===
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
router = dp

# === Хэндлеры ===

@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(BookingStates.waiting_for_name)
    await message.answer("Введите ваше имя:")

@router.message(BookingStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(BookingStates.waiting_for_date)
    calendar = SimpleCalendar()
    await message.answer("Выберите дату:", reply_markup=await calendar.start_calendar())

@router.callback_query(F.data.startswith("simple_calendar"))
async def process_date(callback: CallbackQuery, state: FSMContext):
    if await state.get_state() != BookingStates.waiting_for_date.state:
        await callback.answer()
        return

    calendar = SimpleCalendar()
    selected, date = await calendar.process_selection(callback)

    if not selected:
        await callback.answer()
        return

    await state.update_data(date=str(date))
    await callback.message.answer(f"Вы выбрали: {date.strftime('%d.%m.%Y')}")
    await callback.message.answer("Введите номер телефона:")
    await state.set_state(BookingStates.waiting_for_phone)
    await callback.answer()

@router.message(BookingStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()

    # Запись в таблицу
    sheet.append_row([data["name"], data["date"], data["phone"]])

    text = (
        f"<b>Запись подтверждена!</b>\n\n"
        f"<b>Имя:</b> {data['name']}\n"
        f"<b>Дата:</b> {data['date']}\n"
        f"<b>Телефон:</b> {data['phone']}"
    )
    await message.answer(text)
    await state.clear()

# === Webhook ===
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

app = web.Application()
app["bot"] = bot
dp.startup.register(on_startup)
dp.shutdown.register(on_shutdown)
app.router.add_post(WEBHOOK_PATH, dp.webhook_handler())

if __name__ == "__main__":
    web.run_app(app, port=8000)
