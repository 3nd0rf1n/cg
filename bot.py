import asyncio
import datetime
import logging
import os
import requests
from collections import defaultdict
from telegram import Bot
from telegram.ext import Application
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web
import nest_asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

bot = Bot(token=BOT_TOKEN)
command_usage = defaultdict(lambda: [None, 0])
last_alert_status = None

async def send_startup_notification():
    message = (
        "🇺🇦 *Шановні мешканці Червонограда та Шептицького!*\n\n"
        "Раді повідомити, що наш Telegram-бот працює для вас цілодобово та допомагає бути в курсі важливих подій.\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔔 *Основний функціонал бота:*\n"
        "• 🛑 Оповіщення про повітряну тривогу у Львівській області\n"
        "• 🕯️ Щоденне нагадування о 09:00 — Всеукраїнська хвилина мовчання\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "ℹ️ Команда /rozklad тимчасово була видалена з цього бота.\n"
        "⚠️ Незабаром вона буде доступна в окремому боті з покращеним функціоналом.\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Порада:*\n"
        "Напишіть боту будь-яке повідомлення у особисті, щоб отримувати актуальну інформацію.\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "З повагою,\n"
        "*Ваш помічник з безпеки та транспорту 💙💛*"
    )
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")

async def send_minute_of_silence():
    now = datetime.datetime.now()
    invasion_start = datetime.datetime(2022, 2, 24)
    days_since_invasion = (now - invasion_start).days + 1
    crimea_occupation_start = datetime.datetime(2014, 2, 20)
    days_since_crimea = (now - crimea_occupation_start).days + 1
    message = (
        f"🕯️ {now.strftime('%d.%m.%Y')} о 09:00 — Всеукраїнська хвилина мовчання.\n\n"
        f"У цей час вшановуємо памʼять усіх громадян України — військовослужбовців та цивільних, які трагічно загинули "
        f"внаслідок збройної агресії Російської Федерації проти України.\n\n"
        f"Світла памʼять полеглим. Честь і слава Героям! 🇺🇦\n\n"
        f"📅 Сьогодні — {days_since_invasion}-й день від початку повномасштабного вторгнення.\n"
        f"📅 Минуло {days_since_crimea} днів з моменту початку тимчасової окупації Автономної Республіки Крим."
    )
    await bot.send_message(chat_id=CHAT_ID, text=message)

async def check_air_alerts():
    global last_alert_status
    try:
        r = requests.get("https://alerts.com.ua/api/states", timeout=10)
        if r.status_code == 200:
            states = r.json().get("states", [])
            lviv = next((r for r in states if r["id"] == 12), None)
            if lviv:
                status = lviv.get("alert", False)
                if last_alert_status != status:
                    last_alert_status = status
                    if status:
                        text = (
                            "🚨 *Увага! Повітряна тривога у Львівській області!*\n\n"
                            "🔴 Залишайтесь у безпечному місці або негайно прямуйте до найближчого укриття.\n"
                            "❗ Дотримуйтесь правил безпеки, не ігноруйте сигнали тривоги.\n"
                            "📢 Інформацію про ситуацію уточнюйте в офіційних джерелах.\n\n"
                            "Разом вистоїмо. Слава Україні! 🇺🇦"
                        )
                    else:
                        text = (
                            "✅ *Відбій повітряної тривоги у Львівській області!*\n\n"
                            "☀️ Наразі загроза з повітря відсутня. Ви можете повернутись до звичних справ.\n"
                            "🙏 Дякуємо всім за пильність, відповідальність та дотримання правил безпеки.\n\n"
                            "Разом до перемоги! 💙💛"
                        )
                    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"[ПОМИЛКА] Перевірка тривоги: {e}", exc_info=True)

async def handle(request):
    return web.Response(text="Bot is running")

async def start_web():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    while True:
        await asyncio.sleep(3600)

async def main():
    logging.basicConfig(level=logging.INFO)
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(send_minute_of_silence, 'cron', hour=9, minute=0)
    scheduler.add_job(check_air_alerts, 'interval', seconds=60)
    scheduler.start()

    application = Application.builder().token(BOT_TOKEN).build()

    asyncio.create_task(start_web())
    asyncio.create_task(send_startup_notification())

    logging.info("✅ Бот запускається...")
    await application.run_polling()

if __name__ == '__main__':
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
