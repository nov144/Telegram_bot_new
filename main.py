import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Хендлер на /start
async def handle_start(message: types.Message):
    await message.answer("Привет!")

# Хендлер для проверки живости сервера
async def health(request):
    return web.Response(text="OK")

# Главная функция
async def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.getenv("PORT", 8080))

    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.message.register(handle_start, Command("start"))

    app = web.Application()

    # Регистрируем /health ручку
    app.router.add_get("/health", health)

    # Подключаем webhook-обработчик
    setup_application(app, dp, bot=bot)

    # Устанавливаем webhook при запуске
    async def on_startup(app):
        await bot.set_webhook(WEBHOOK_URL)
        print("✅ Webhook установлен")

    # Удаляем webhook и закрываем сессию при остановке
    async def on_shutdown(app):
        await bot.delete_webhook()
        await bot.session.close()
        print("🛑 Webhook удалён")

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print(f"🚀 Сервер запущен на порту {PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
