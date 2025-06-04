import os
import json
import base64
import gspread
import asyncio

from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.client.default import DefaultBotProperties

from aiogram_calendar import SimpleCalendar

from google.oauth2.service_account import Credentials


BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

creds_json = json.loads(base64.b64decode(os.getenv("GOOGLE_CREDS_BASE64")))
credentials = Credentials.from_service_account_info(creds_json, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gclient = gspread.authorize(credentials)
spreadsheet = gclient.open_by_key(SPREADSHEET_ID)
sheet = spreadsheet.sheet1


class BookingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_phone = State()


bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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


@router.callback_query(F.data.startswith("simple_calendar"))
async def process_date(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != BookingStates.waiting_for_date.state:
        return

    calendar = SimpleCalendar()
    result = await calendar.process_selection(callback, callback.data)

    if result.selected:
        await state.update_data(date=str(result.date))
        await callback.message.answer(f"Вы выбрали: {result.date.strftime('%d.%m.%Y')}")
        await callback.message.answer("Введите номер телефона:")
        await state.set_state(BookingStates.waiting_for_phone)

    await callback.answer()


@router.message(BookingStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text
    await state.update_data(phone=phone)
    data = await state.get_data()

    name = data["name"]
    date = data["date"]
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    summary = f"<b>Запись подтверждена!</b>
Имя: {name}
Дата: {date}
Телефон: {phone}"

    try:
        sheet.append_row([name, date, phone, timestamp])
    except Exception as e:
        await message.answer(f"❌ Ошибка при записи в таблицу: {e}")
        return

    await message.answer(summary)
    await bot.send_message(chat_id=-1002293928496, text=summary)
    await state.clear()


async def on_startup(_: web.Application):
    await bot.set_webhook(WEBHOOK_URL)


app = web.Application()
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/")
setup_application(app, dp, bot=bot)
app.on_startup.append(on_startup)

if __name__ == "__main__":
    web.run_app(app, port=8000)
