import os
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from aiogram_calendar import SimpleCalendar


# FSM
class BookingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_phone = State()

# ENV
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")


# Bot init
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Google Sheets setup
from google.oauth2.service_account import Credentials
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("/etc/secrets/credentials.json", scopes=scopes)
gclient = gspread.authorize(creds)
# 🔍 Проверка доступа к таблице
try:
    spreadsheet = gclient.open_by_key(SPREADSHEET_ID)
    print("✅ Таблица открыта успешно:", spreadsheet.title)
except Exception as e:
    print("❌ Ошибка при открытии таблицы:", e)
sheet = gclient.open_by_key(SPREADSHEET_ID).sheet1




# Handlers
@dp.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await message.answer("Как вас зовут?")
    await state.set_state(BookingStates.waiting_for_name)

@dp.message(BookingStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Выберите дату записи:")
    await state.set_state(BookingStates.waiting_for_date)
    await message.answer(
        "Пожалуйста, выберите дату:",
        reply_markup=await SimpleCalendar().start_calendar()
    )

@dp.callback_query_handler(lambda c: c.data.startswith("CALENDAR"), state=BookingStates.waiting_for_date)
async def process_date(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if not selected:
        return
    await state.update_data(date=str(date))
    await callback_query.message.answer(f"Вы выбрали: {date.strftime('%d.%m.%Y')}")
    await callback_query.answer()
    await state.set_state(BookingStates.waiting_for_phone)
    await callback_query.message.answer("Введите номер телефона:")

@dp.message(BookingStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text
    await state.update_data(phone=phone)

    data = await state.get_data()
    name = data["name"]
    date = data["date"]

    summary = f"\n\n<b>Запись подтверждена!</b>\nИмя: {name}\nДата: {date}\nТелефон: {phone}"

    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    sheet.append_row([name, date, phone, timestamp])

    await message.answer(summary)
    await bot.send_message(-1002293928496, summary)
    await state.clear()

# Webhook server
async def on_startup(_: web.Application):
    await bot.set_webhook("https://telegram-bot-new-6o20.onrender.com/webhook")

app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
setup_application(app, dp, bot=bot)
app.on_startup.append(on_startup)

if __name__ == '__main__':
    web.run_app(app, port=8000)

