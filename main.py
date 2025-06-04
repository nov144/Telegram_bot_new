import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import setup_application

# Команда /start
async def handle_start(message: types.Message):
    await message.answer("Привет!")

# Главная async-функция
async def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Обязательно с /webhook
    PORT = int(os.getenv("PORT", 8080))

    app = web.Application()

    async with Bot(BOT_TOKEN) as bot:
        dp = Dispatcher()
        dp.message.register(handle_start, Command("start"))

        # Webhook
        async def on_startup(app):
            await bot.set_webhook(WEBHOOK_URL)
            print("✅ Webhook установлен")

        async def on_shutdown(app):
            await bot.delete_webhook()
            print("🛑 Webhook удалён")

        app.on_startup.append(on_startup)
        app.on_shutdown.append(on_shutdown)

        setup_application(app, dp, bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()

        print(f"🚀 Сервер запущен на порту {PORT}")
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
