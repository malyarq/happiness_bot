import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from datetime import datetime
from database import Database
from config import TOKEN

db = Database()


async def send_quotes():
    users = db.get_all_users()
    for user in users:
        user_id, username, user_time = user
        current_time = datetime.now().strftime("%H:%M")
        if current_time == user_time:
            logging.info(
                f"Настало время ({user_time}) отправить цитату пользователю @{username}({user_id})"
            )
            quote_data = db.get_random_quote(user_id)
            if quote_data:
                bot = Bot(TOKEN)
                await bot.send_message(
                    chat_id=user_id,
                    text=f'*"{quote_data[0]}"* — _{quote_data[1]}_',
                    parse_mode="MarkdownV2",
                )


def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_quotes, "interval", minutes=1)
    scheduler.start()
