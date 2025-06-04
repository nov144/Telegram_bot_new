import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import setup_application

# Хендлер на /start
async def handle_start(message: types.Message):
    await message.answer("Привет!")

async def main():
    # Создаём aiohttp-приложение
    app = web.Application()

    # Загружаем переменные окружения
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://your-render-url/webhook
    PORT = int(os.getenv("PORT", 8080))

    # Контекстно создаём бота
    async with Bot(BOT_TOKEN) as bot:
        # Регистрируем диспетчер и хендлер
        dp = Dispatcher()
        dp.message.register(handle_start, Command("start"))

        # Webhook setup
        async def on_startup(app):
            await bot.set_webhook(WEBHOOK_URL)
            print(f"✅ Webhook установлен: {WEBHOOK_URL}")

        async def on_shutdown(app):
            await bot.delete_webhook()
            print("🛑 Webhook удалён")

        app.on_startup.append(on_startup)
        app.on_shutdown.append(on_shutdown)

        # Привязываем aiogram к aiohttp
        setup_application(app, dp, bot=bot)

        # Запуск web-сервера
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        print(f"🚀 Сервер запущен на порту {PORT}")

        # Бесконечное ожидание (чтобы бот не завершался)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
