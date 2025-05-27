import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram_calendar import SimpleCalendar, simple_cal_callback
from aiohttp import web

from states import BookingStates

import gspread
from google.oauth2.service_account import Credentials

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://yourapp.onrender.com/webhook

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# === Google Таблица ===
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_key("130eO8Wl9ezkXEgbM6CnHt6C2k_lFKYKttbDqfN69mxg").sheet1

# === Хендлеры ===
@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("Записаться"))
    await message.answer("Привет! Я бот для записи к мастеру. Выберите действие:", reply_markup=kb)

@dp.message_handler(lambda msg: msg.text == "Записаться")
async def ask_name(message: types.Message):
    await message.answer("Как вас зовут?")
    await BookingStates.waiting_for_name.set()

@dp.message_handler(state=BookingStates.waiting_for_name)
async def ask_date(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Выберите дату:", reply_markup=await SimpleCalendar().start_calendar())
    await BookingStates.waiting_for_date.set()

@dp.callback_query_handler(simple_cal_callback.filter(), state=BookingStates.waiting_for_date)
async def process_calendar(callback: types.CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback, callback_data)
    if not selected:
        return
    await state.update_data(date=str(date))
    await callback.message.answer(f"Вы выбрали: {date.strftime('%d.%m.%Y')}")
    await callback.message.answer("Введите номер телефона:")
    await BookingStates.waiting_for_phone.set()

@dp.message_handler(state=BookingStates.waiting_for_phone)
async def finalize(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()

    summary = (
        f"Запись подтверждена!\n\n"
        f"Имя: {data['name']}\n"
        f"Дата: {data['date']}\n"
        f"Телефон: {data['phone']}"
    )

    # Отправка сообщений
    await message.answer(summary)
    await bot.send_message(-1002293928496, summary)  # Владелец/группа
    await bot.send_message(300466559, summary)        # Личка

    # Сохраняем в Google Таблицу
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    sheet.append_row([data["name"], data["date"], data["phone"], now])

    await state.finish()

# === Webhook-часть ===
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

app = web.Application()
app.router.add_post("/webhook", dp.webhook_handler)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, port=10000)

