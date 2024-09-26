import logging
import re
from telegram import Update
from telegram.ext import ContextTypes
from database import Database
from config import ADMIN_IDS

db = Database()


async def check_admin(update: Update, where=None) -> bool:
    user = update.effective_user
    if user.id not in ADMIN_IDS and where:
        logging.warning(
            f"Пользователь @{user.username}({user.id}) пытался выполнить административную команду: {where}."
        )
    return user.id in ADMIN_IDS


async def add_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, where="/addquote"):
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "Используй: /addquote <цитата> - <автор> (дефис обязателен)"
        )
        return

    text = " ".join(context.args)

    quote_pattern = re.compile(r'["“]?(.*?)["”]?\s*-\s*(.*)')

    match = quote_pattern.search(text)

    if match:
        quote_text = match.group(1).strip()
        author = match.group(2).strip()

        if not quote_text or not author:
            await update.message.reply_text(
                "Используй: /addquote <цитата> - <автор> (дефис обязателен)"
            )
            return

        db.add_quote(quote_text, author)
        await update.message.reply_text(f'Цитата добавлена: "{quote_text}" - {author}')
    else:
        await update.message.reply_text(
            "Используй: /addquote <цитата> - <автор> (дефис обязателен)"
        )


async def list_quotes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, where="/listquotes"):
        return

    quotes = db.get_all_quotes()
    if not quotes:
        await update.message.reply_text("Нет доступных цитат.")
        return

    response = ""
    count = 0

    for quote in quotes:
        response += f'{quote[0]}. "{quote[1]}" — {quote[2]}\n'
        count += 1

        if count == 40:
            await update.message.reply_text(response)
            response = ""
            count = 0

    if response:
        await update.message.reply_text(response)


async def delete_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, where="/deletequote"):
        return

    if not context.args:
        await update.message.reply_text("Используй: /deletequote <номер цитаты>")
        return

    try:
        quote_id = int(context.args[0])
        db.delete_quote(quote_id)
        await update.message.reply_text(f"Цитата с номером {quote_id} удалена.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при удалении цитаты: {e}")


async def handle_quote_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    action = data[0]
    user_id = data[1]
    quote_id = data[2]

    quote, author = db.get_pending_quote(quote_id)

    if action == "accept":
        db.add_quote(quote, author)

        await context.bot.send_message(
            chat_id=user_id,
            text=f'Твоя цитата: *"{quote}"* — _{author}_ добавлена\\!',
            parse_mode="MarkdownV2",
        )
        await query.edit_message_text(
            text=f'Цитата принята: *"{quote}"* — _{author}_',
            parse_mode="MarkdownV2",
        )

    elif action == "reject":
        db.delete_pending_quote(quote)

        await query.edit_message_text(
            text=f'Цитата отклонена: *"{quote}"* — _{author}_',
            parse_mode="MarkdownV2",
        )


async def disable_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, where="/disable"):
        return

    db.cursor.execute("UPDATE users SET active = 0")
    db.conn.commit()
    await update.message.reply_text(
        "Бот отключен. Все пользователи не будут получать цитаты."
    )


async def enable_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, where="/enable"):
        return

    db.cursor.execute("UPDATE users SET active = 1")
    db.conn.commit()
    await update.message.reply_text(
        "Бот включен. Все пользователи снова будут получать цитаты."
    )
