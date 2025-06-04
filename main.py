import os
import json
import base64
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_calendar import SimpleCalendar
from aiogram_calendar.simple_calendar import SimpleCalendarCallback
from aiohttp import web
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Логирование ===
logging.basicConfig(level=logging.INFO)

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = "/webhook"
PORT = int(os.getenv("PORT", default=8000))

# === FSM Состояния ===
class BookingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_phone = State()

# === Авторизация Google Sheets через base64 ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_data = json.loads(base64.b64decode(os.getenv("GOOGLE_CREDS_BASE64")).decode("utf-8"))
credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_data, scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(os.getenv("SHEET_ID")).sheet1

# === Инициализация бота и диспетчера ===
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = dp

# === Команда /start ===
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(BookingStates.waiting_for_name)
    await message.answer("Введите ваше имя:")

# === Имя ===
@router.message(BookingStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(BookingStates.waiting_for_date)
    calendar = SimpleCalendar()
    await message.answer("Выберите дату:", reply_markup=await calendar.start_calendar())

# === Дата ===
@router.callback_query(F.data.startswith("simple_calendar"))
async def process_date(callback: CallbackQuery, state: FSMContext):
    if await state.get_state() != BookingStates.waiting_for_date.state:
        await callback.answer()
        return

    calendar = SimpleCalendar()
    callback_data = SimpleCalendarCallback.unpack(callback.data)
    selected, date = await calendar.process_selection(callback, callback_data)

    if not selected:
        await callback.answer()
        return

    await state.update_data(date=str(date))
    await callback.message.answer(f"Вы выбрали: {date.strftime('%d.%m.%Y')}")
    await callback.message.answer("Введите номер телефона:")
    await state.set_state(BookingStates.waiting_for_phone)
    await callback.answer()

# === Телефон ===
@router.message(BookingStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    sheet.append_row([data["name"], data["date"], data["phone"]])

    summary = (
        f"<b>Запись подтверждена!</b>\n\n"
        f"<b>Имя:</b> {data['name']}\n"
        f"<b>Дата:</b> {data['date']}\n"
        f"<b>Телефон:</b> {data['phone']}"
    )
    await message.answer(summary)
    await state.clear()

# === Webhook запуск ===
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
    web.run_app(app, port=PORT)
