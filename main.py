import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

# Вставь сюда свой токен
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("your_spreadsheet_id").sheet1  # замените на свой ID

# FSM
class Booking(StatesGroup):
    choosing_date = State()
    entering_name = State()
    entering_phone = State()

@dp.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await message.answer("Выберите дату:", reply_markup=await SimpleCalendar().start_calendar())
    await state.set_state(Booking.choosing_date)

@dp.callback_query(SimpleCalendarCallback.filter())
async def process_date(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    selected_date = callback_data.date
    await state.update_data(date=selected_date)
    await callback.message.answer(f"Вы выбрали: {selected_date.strftime('%d.%m.%Y')}\nВведите имя:")
    await state.set_state(Booking.entering_name)

@dp.message(Booking.entering_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите номер телефона:")
    await state.set_state(Booking.entering_phone)

@dp.message(Booking.entering_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()

    # Сохраняем в Google Таблицу
    sheet.append_row([str(datetime.now()), data["date"].strftime("%d.%m.%Y"), data["name"], data["phone"]])

    summary = (
        f"<b>Запись подтверждена!</b>\n"
        f"Имя: {data['name']}\n"
        f"Дата: {data['date'].strftime('%d.%m.%Y')}\n"
        f"Телефон: {data['phone']}"
    )
    await message.answer(summary)
    await state.clear()

if __name__ == "__main__":
    import asyncio
    from aiogram.webhook.aiohttp_server import setup_application
    from aiohttp import web

    async def on_startup(dispatcher: Dispatcher, bot: Bot):
        logging.info("Bot started.")

    async def main():
        app = web.Application()
        dp.startup.register(on_startup)
        await setup_application(app, dispatcher=dp, bot=bot)
        return app

    web.run_app(main(), port=8000)
