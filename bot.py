import asyncio
import datetime
import logging
import os
import requests
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BOT_TOKEN = os.getenv("BOT_TOKEN", "7450692138:AAHiERBibay9XI56FhpSwFFclfKZmZNWoVM")
CHAT_ID = int(os.getenv("CHAT_ID", "-4811736259"))  

bot = Bot(token=BOT_TOKEN)
last_alert_status = None

async def send_minute_of_silence():
    now = datetime.datetime.now()

    invasion_start = datetime.datetime(2022, 2, 24)
    days_since_invasion = (now - invasion_start).days + 1

    crimea_occupation_start = datetime.datetime(2014, 2, 20)
    days_since_crimea = (now - crimea_occupation_start).days + 1

    message = (
        f"🕯️ {now.strftime('%d.%m.%Y')} — Всеукраїнська хвилина мовчання.\n\n"
        f"Схиляємо голови перед памʼяттю усіх українців — військових та цивільних, "
        f"які загинули внаслідок збройної агресії Російської Федерації проти України.\n\n"
        f"Вічна слава Героям! 🇺🇦\n\n"
        f"📅 Сьогодні — {days_since_invasion}-й день повномасштабного вторгнення.\n"
        f"📅 Минуло {days_since_crimea} днів з моменту окупації Криму."
    )

    await bot.send_message(chat_id=CHAT_ID, text=message)
    logging.info("Відправлено хвилину мовчання")

async def check_air_alerts():
    global last_alert_status
    try:
        r = requests.get("https://alerts.com.ua/api/states/14", timeout=10)
        if r.status_code == 200 and r.text.strip():
            data = r.json()
            status = data.get("alert")

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
                    logging.info("Відправлено повідомлення про повітряну тривогу")
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
                    logging.info("Відправлено повідомлення про відбій тривоги")
        else:
            logging.warning(f"Помилка API або пустий вміст, status_code={r.status_code}")
    except Exception as e:
        logging.error(f"[ПОМИЛКА] Перевірка тривоги: {e}", exc_info=True)

async def check_air_alerts_wrapper():
    await check_air_alerts()

async def main():
    logging.basicConfig(level=logging.INFO)
    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")

    scheduler.add_job(send_minute_of_silence, 'cron', hour=9, minute=00)
    scheduler.add_job(check_air_alerts_wrapper, 'interval', seconds=60)

    scheduler.start()
    logging.info("🤖 Бот запущено...")

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Бот зупинено")

if __name__ == '__main__':
    asyncio.run(main())
