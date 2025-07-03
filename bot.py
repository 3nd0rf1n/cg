import asyncio
import datetime
import logging
import os
import requests
from collections import defaultdict
from telegram import ReplyKeyboardMarkup, Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

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
        "🆕 *НОВИЙ ФУНКЦІОНАЛ:*\n"
        "Команда /rozklad тепер надсилає коротку інструкцію у чат, а детальна інструкція з вибором напрямку маршруток приходить у ваші особисті повідомлення.\n"
        "⚠️ Використання команди обмежено до 2 разів на день для уникнення навантаження.\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Порада:*\n"
        "Напишіть боту будь-яке повідомлення у особисті, щоб отримувати інструкції та розклад маршруток без проблем.\n"
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

async def rozklad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Якщо команда викликана не в особистих — ввічливо нагадаємо
    if update.effective_chat.type != "private":
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "ℹ️ Щоб отримати розклад маршруток, напишіть боту в особисті повідомлення 🤖\n\n"
                "Ця команда працює тільки в особистому чаті з ботом — це потрібно, щоб він міг надіслати вам розклад."
            )
        )
        return

    # Коротке пояснення
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "✅ Ви звернулись до розкладу маршруток.\n\n"
            "📩 Інструкція та вибір напрямку будуть у цьому чаті."
        )
    )

    # Перевірка обмежень (2 рази/день)
    today = datetime.date.today()
    last_date, count = command_usage[user_id]
    if last_date != today:
        command_usage[user_id] = [today, 1]
    elif count >= 2:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Ви вже використали цю команду 2 рази сьогодні.\nЗавітайте завтра 🕒"
        )
        return
    else:
        command_usage[user_id][1] += 1

    # Відправка клавіатури з вибором
    keyboard = [["🚍 Шептицький → Львів"], ["🚍 Львів → Шептицький"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="🚌 Виберіть напрямок маршрутки, щоб отримати актуальний розклад:",
            reply_markup=reply_markup
        )
    except Exception:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ Щоб отримати розклад, спочатку напишіть боту хоча б одне повідомлення в особисті.\n"
                "Telegram не дозволяє ботам починати діалог першими."
            )
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🚍 Шептицький → Львів":
        schedule = ["05:50", "06:05", "06:15", "06:37", "06:49", "07:10", "07:37", "08:09",
            "08:41", "09:04", "09:37", "09:53", "10:15", "10:25", "10:41", "11:13",
            "11:37", "12:09", "12:41", "12:57", "13:29", "14:01", "14:41", "15:15",
            "15:29", "15:45", "16:09", "16:37", "16:57", "17:25", "17:37", "18:01",
            "19:01", "19:40", "21:00"]
        direction = "Шептицький → Львів"
    elif text == "🚍 Львів → Шептицький":
        schedule = ["06:00", "06:15", "06:50", "06:50", "07:10", "07:30", "07:40", "08:00",
            "08:30", "09:00", "09:32", "10:04", "10:20", "10:25", "11:32", "12:00",
            "12:04", "12:36", "12:52", "13:10", "13:24", "13:30", "13:40", "13:55",
            "14:12", "14:28", "14:30", "14:52", "15:16", "15:48", "15:50", "16:20",
            "17:00", "17:14", "17:24", "17:30", "18:18", "18:32", "18:52", "19:15",
            "20:05", "20:15", "20:50"]
        direction = "Львів → Шептицький"
    else:
        return
    times = "\n".join([f"🕒 {t}" for t in schedule])
    await update.message.reply_text(f"✅ Ви обрали напрямок: {direction}\n\n🚌 Відправлення:\n{times}")

async def main():
    logging.basicConfig(level=logging.INFO)
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(send_minute_of_silence, 'cron', hour=9, minute=0)
    scheduler.add_job(check_air_alerts, 'interval', seconds=60)
    scheduler.start()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("rozklad", rozklad_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    asyncio.create_task(start_web())
    asyncio.create_task(send_startup_notification())
    logging.info("✅ Бот запускається...")
    await application.run_polling()

if __name__ == '__main__':
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        print("❌ Бот зупинено вручну")
    finally:
        loop.close()

