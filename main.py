import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import setup_application

# Хендлер на /start
async def handle_start(message: types.Message):
    await message.answer("Привет!")

# 👇 ДОБАВИ ЭТУ ФУНКЦИЮ
async def health(request):
    return web.Response(text="OK")

async def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.getenv("PORT", 8080))

    app = web.Application()

    # 👇 Регистрируем /health ручку ДО setup_application
    app.router.add_get("/health", health)

    async with Bot(BOT_TOKEN) as bot:
        dp = Dispatcher()
        dp.message.register(handle_start, Command("start"))

        async def on_startup(app):
            await bot.set_webhook(WEBHOOK_URL)

        async def on_shutdown(app):
            await bot.delete_webhook()

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
