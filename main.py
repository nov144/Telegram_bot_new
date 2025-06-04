import os
import json
import base64
from datetime import datetime

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from aiogram_calendar import SimpleCalendar
import gspread
from google.oauth2.service_account import Credentials

# ENV
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Google Sheets
creds_json = json.loads(base64.b64decode(os.getenv("GOOGLE_CREDS_BASE64")))
credentials = Credentials.from_service_account_info(
    creds_json,
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
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Handlers
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(BookingStates.waiting_for_name)
    await message.answer("Как вас зовут?")

@router.message(BookingStates.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(BookingStates.waiting_for_date)
    await message.answer("Выберите дату:", reply_markup=await SimpleCalendar().start_calendar())

@router.callback_query(F.data.startswith("simple_calendar"))
async def process_date(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != BookingStates.waiting_for_date.state:
        return

    calendar = SimpleCalendar()
    result = await calendar.process_selection(callback, callback.data)

    if isinstance(result, tuple):
        selected, date = result
        if selected:
            await state.update_data(date=str(date))
            await state.set_state(BookingStates.waiting_for_phone)
            await callback.message.answer(f"Вы выбрали: {date.strftime('%d.%m.%Y')}")
            await callback.message.answer("Введите номер телефона:")
        await callback.answer()

@router.message(BookingStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = message.text

    row = [data["name"], data["date"], phone, datetime.now().strftime("%d.%m.%Y %H:%M:%S")]
    try:
        sheet.append_row(row)
    except Exception as e:
        await message.answer(f"Ошибка при записи в таблицу: {e}")
        return

    await message.answer(f"<b>Запись подтверждена!</b>\nИмя: {data['name']}\nДата: {data['date']}\nТелефон: {phone}")
    await state.clear()

# Webhook
async def on_startup(_: web.Application):
    await bot.set_webhook(WEBHOOK_URL)

app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/")
setup_application(app, dp, bot=bot)
app.on_startup.append(on_startup)

if __name__ == "__main__":
    web.run_app(app, port=8000)
