import asyncio
import datetime
import logging
import os
import requests
from collections import defaultdict
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "-1001383482902"))

last_alert_status = None
waiting_for_schedule_choice = set()
command_usage = defaultdict(lambda: [None, 0])

async def send_startup_notification(application: Application):
    message = (
        "🇺🇦 *Шановні мешканці Червонограда та Шептицького!*\n\n"
        "З радістю повідомляємо, що інформативний Telegram-бот *працює для вас цілодобово* 💪\n"
        "..."
    )
    await application.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")

async def send_minute_of_silence(application: Application):
    now = datetime.datetime.now()
    invasion_start = datetime.datetime(2022, 2, 24)
    days_since_invasion = (now - invasion_start).days + 1
    crimea_occupation_start = datetime.datetime(2014, 2, 20)
    days_since_crimea = (now - crimea_occupation_start).days + 1
    message = (
        f"🕯️ {now.strftime('%d.%m.%Y')} о 09:00 — Всеукраїнська хвилина мовчання.\n\n"
        f"...\n"
        f"📅 Сьогодні — {days_since_invasion}-й день від початку повномасштабного вторгнення.\n"
        f"📅 Минуло {days_since_crimea} днів з моменту початку тимчасової окупації Криму."
    )
    await application.bot.send_message(chat_id=CHAT_ID, text=message)

async def check_air_alerts(application: Application):
    global last_alert_status
    try:
        r = requests.get("https://alerts.com.ua/api/states", timeout=10)
        if r.status_code == 200 and r.text.strip():
            data = r.json()
            lviv = next((region for region in data.get("states", []) if region["id"] == 12), None)
            if lviv:
                status = lviv.get("alert", False)
                if last_alert_status != status:
                    last_alert_status = status
                    if status:
                        await application.bot.send_message(
                            chat_id=CHAT_ID,
                            text="🚨 *Увага! Повітряна тривога у Львівській області!*",
                            parse_mode="Markdown"
                        )
                    else:
                        await application.bot.send_message(
                            chat_id=CHAT_ID,
                            text="✅ *Відбій повітряної тривоги у Львівській області!*",
                            parse_mode="Markdown"
                        )
    except Exception as e:
        logging.error(f"[ПОМИЛКА] Перевірка тривоги: {e}", exc_info=True)

async def handle(request):
    return web.Response(text="Bot is running")

async def start_http_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    while True:
        await asyncio.sleep(3600)

async def send_schedule_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = datetime.date.today()
    last_date, count = command_usage[user_id]
    if last_date != today:
        command_usage[user_id] = [today, 1]
    elif count >= 2:
        await update.message.reply_text("⚠️ Ви вже використали цю команду 2 рази сьогодні.")
        return
    else:
        command_usage[user_id][1] += 1

    keyboard = [["🚍 Шептицький → Львів"], ["🚍 Львів → Шептицький"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    waiting_for_schedule_choice.add(update.message.chat_id)
    await update.message.reply_text("🚌 Оберіть напрямок:", reply_markup=reply_markup)

async def handle_schedule_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in waiting_for_schedule_choice:
        return
    waiting_for_schedule_choice.remove(chat_id)

    direction = update.message.text
    waiting_message = await update.message.reply_text("⏳ Зачекайте, шукаю розклад…")
    await asyncio.sleep(2)
    await context.bot.delete_message(chat_id=chat_id, message_id=waiting_message.message_id)

    if direction == "🚍 Шептицький → Львів":
        schedule = ["05:50", "06:05", "06:15", "..."]
    elif direction == "🚍 Львів → Шептицький":
        schedule = ["06:00", "06:15", "06:50", "..."]
    else:
        await update.message.reply_text("⚠️ Невідомий вибір.", reply_markup=ReplyKeyboardRemove())
        return

    lines = [f"🕒 {time}" for time in schedule]
    cols = 5
    rows = [lines[i:i + cols] for i in range(0, len(lines), cols)]
    response = "\n".join(["    ".join(row) for row in rows])
    await update.message.reply_text(
        f"✅ Ви обрали напрямок: {direction}\n\n🚌 Відправлення:\n{response}",
        reply_markup=ReplyKeyboardRemove()
    )

async def main():
    logging.basicConfig(level=logging.INFO)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("rozklad", send_schedule_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule_choice))

    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(lambda: asyncio.create_task(send_minute_of_silence(app)), 'cron', hour=9, minute=0)
    scheduler.add_job(lambda: asyncio.create_task(check_air_alerts(app)), 'interval', seconds=60)
    scheduler.start()

    await app.initialize()
    await app.start()
    await send_startup_notification(app)

    await start_http_server()  # без task-а, т.к. run_polling — блокирующий
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
