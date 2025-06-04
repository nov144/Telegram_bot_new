import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import setup_application

# Получаем токен и webhook URL из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # должен заканчиваться на /webhook

# Хендлер на /start
async def handle_start(message: types.Message):
    await message.answer("Привет!")

# Основная функция
async def main():
    # Создаем aiohttp приложение
    app = web.Application()

    # Используем async with для Bot
    async with Bot(BOT_TOKEN) as bot:
        dp = Dispatcher()
        dp.message.register(handle_start, Command("start"))

        # Установка webhook
        async def on_startup(app):
            await bot.set_webhook(WEBHOOK_URL)
            print("✅ Webhook установлен:", WEBHOOK_URL)

        async def on_shutdown(app):
            await bot.delete_webhook()
            print("🛑 Webhook удалён")

        app.on_startup.append(on_startup)
        app.on_shutdown.append(on_shutdown)

        # Подключаем aiogram к aiohttp
        setup_application(app, dp, bot=bot)

        # Запускаем сервер
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.getenv("PORT", 8080))  # Render указывает свой порт
        site = web.TCPSite(runner, host="0.0.0.0", port=port)
        await site.start()

        print(f"🚀 Сервер запущен на порту {port}")

        # Бесконечное ожидание, чтобы бот не завершился
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
