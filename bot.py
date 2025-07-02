import asyncio
import datetime
import logging
import os
import requests
from collections import defaultdict
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

BOT_TOKEN = os.getenv("BOT_TOKEN", "7450692138:AAHiERBibay9XI56FhpSwFFclfKZmZNWoVM")
CHAT_ID = int(os.getenv("CHAT_ID", "-1001383482902"))

bot = Bot(token=BOT_TOKEN)
last_alert_status = None
waiting_for_schedule_choice = set()
command_usage = defaultdict(lambda: [None, 0])

async def send_startup_notification():
    message = (
        "🇺🇦 *Шановні мешканці Червонограда та Шептицького!*\n\n"
        "З радістю повідомляємо, що інформативний Telegram-бот *працює для вас цілодобово* 💪\n"
        "Його мета — допомогти вам бути в курсі важливих подій та змін.\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔔 *Основний функціонал бота:*\n"
        "• 🛑 _Оповіщення про повітряну тривогу у Львівській області_\n"
        "• 🕯️ _Щоденне нагадування о 09:00 — Всеукраїнська хвилина мовчання_\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🆕 *НОВА МОЖЛИВІСТЬ:*\n"
        "Команда /rozklad — відкриває розклад маршруток між Шептицьким та Львовом 🚌\n"
        "⚠️ _Обмеження: не більше 2 разів на день, щоб уникнути навантаження_\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Порада:*\n"
        "Додайте цього бота в «Обране» та увімкніть сповіщення, щоб не пропустити важливе\n"
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
        f"У цей час вшановуємо памʼять усіх громадян України — військовослужбовців та цивільних, "
        f"які трагічно загинули внаслідок збройної агресії Російської Федерації проти України.\n\n"
        f"Світла памʼять полеглим. Честь і слава Героям! 🇺🇦\n\n"
        f"📅 Сьогодні — {days_since_invasion}-й день від початку повномасштабного вторгнення.\n"
        f"📅 Минуло {days_since_crimea} днів з моменту початку тимчасової окупації Автономної Республіки Крим."
    )
    await bot.send_message(chat_id=CHAT_ID, text=message)

async def check_air_alerts():
    global last_alert_status
    try:
        r = requests.get("https://alerts.com.ua/api/states", timeout=10)
        if r.status_code == 200 and r.text.strip():
            data = r.json()
            states = data.get("states", [])
            lviv = next((region for region in states if region["id"] == 12), None)
            if lviv:
                status = lviv.get("alert", False)
                if last_alert_status != status:
                    last_alert_status = status
                    if status:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=(
                                "🚨 *Увага! Повітряна тривога у Львівській області!*\n\n"
                                "Просимо всіх негайно пройти до найближчого укриття.\n"
                                "Дотримуйтесь правил безпеки та не нехтуйте сигналами оповіщення.\n\n"
                                "Слава Україні! 🇺🇦"
                            ),
                            parse_mode='Markdown'
                        )
                    else:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=(
                                "✅ *Відбій повітряної тривоги у Львівській області!*\n\n"
                                "Наразі загроза з повітря відсутня.\n"
                                "Дякуємо всім за пильність та дотримання заходів безпеки.\n\n"
                                "Разом до перемоги! 💙💛"
                            ),
                            parse_mode='Markdown'
                        )
    except Exception as e:
        logging.error(f"[ПОМИЛКА] Перевірка тривоги: {e}", exc_info=True)

async def check_air_alerts_wrapper():
    await check_air_alerts()

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
    else:
        if count >= 2:
            await update.message.reply_text("⚠️ Ви вже використали цю команду 2 рази сьогодні.")
            return
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
    text = update.message.text
    waiting_message = await update.message.reply_text("⏳ Зачекайте, шукаю розклад…")
    await asyncio.sleep(2)
    await context.bot.delete_message(chat_id=chat_id, message_id=waiting_message.message_id)
    if text == "🚍 Шептицький → Львів":
        schedule = [
            "05:50", "06:05", "06:15", "06:37", "06:49", "07:10", "07:37", "08:09", "08:41", "09:04",
            "09:37", "09:53", "10:15", "10:25", "10:41", "11:13", "11:37", "12:09", "12:41", "12:57",
            "13:29", "14:01", "14:41", "15:15", "15:29", "15:45", "16:09", "16:37", "16:57", "17:25",
            "17:37", "18:01", "19:01", "19:40", "21:00"
        ]
        direction = "Шептицький → Львів"
    elif text == "🚍 Львів → Шептицький":
        schedule = [
            "06:00", "06:15", "06:50", "06:50", "07:10", "07:30", "07:40", "08:00", "08:30", "09:00",
            "09:32", "10:04", "10:20", "10:25", "11:32", "12:00", "12:04", "12:36", "12:52", "13:10",
            "13:24", "13:30", "13:40", "13:55", "14:12", "14:28", "14:30", "14:52", "15:16", "15:48",
            "15:50", "16:20", "17:00", "17:14", "17:24", "17:30", "18:18", "18:32", "18:52", "19:15",
            "20:05", "20:15", "20:50"
        ]
        direction = "Львів → Шептицький"
    else:
        await update.message.reply_text("⚠️ Невідомий вибір.", reply_markup=ReplyKeyboardRemove())
        return
    lines = [f"🕒 {time}" for time in schedule]
    cols = 5
    rows = [lines[i:i+cols] for i in range(0, len(lines), cols)]
    response = "\n".join(["    ".join(row) for row in rows])
    await update.message.reply_text(
        f"✅ Ви обрали напрямок: 🚍 {direction}\n\n🚌 Відправлення:\n{response}",
        reply_markup=ReplyKeyboardRemove()
    )

async def main():
    logging.basicConfig(level=logging.INFO)
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(send_minute_of_silence, 'cron', hour=9, minute=0)
    scheduler.add_job(check_air_alerts_wrapper, 'interval', seconds=60)
    scheduler.start()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("rozklad", send_schedule_buttons))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_schedule_choice))
    await application.initialize()
    await application.start()
    await send_startup_notification()
    http_task = asyncio.create_task(start_http_server())
    polling_task = asyncio.create_task(application.updater.start_polling())
    await asyncio.gather(http_task, polling_task)

if __name__ == '__main__':
    asyncio.run(main())
