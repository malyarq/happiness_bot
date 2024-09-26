import re
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import ContextTypes, ConversationHandler
from admin import check_admin, ADMIN_IDS
from database import Database, escape_markdown

db = Database()
AWAIT_TIME, AWAIT_QUOTE = 1, 1


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == "начать":
        await start(update, context)
    if text.lower() == "случайная цитата":
        await quote(update, context)
    if text.lower() == "отмена":
        await cancel(update, context)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    existing_user = db.get_user(user.id)
    if existing_user is None:
        db.add_user(user.id, user.username, "09:00")
        await update.message.reply_text(
            "Привет! Я - бот, который по расписанию будет присылать тебе цитаты, в основном мотивирующие.\n\n"
            "Время для отправки по умолчанию - 09:00. Ты можешь настроить время отправки цитат с помощью кнопки снизу. "
            "Также, ты всегда можешь получить случайную цитату или предложить свою.\n\n"
            "/help - посмотреть список доступных команд.",
            reply_markup=ReplyKeyboardMarkup(
                [["Установить время", "Случайная цитата"], ["Предложить цитату"]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
    else:
        await update.message.reply_text(
            f"Привет! Мы с тобой уже знакомы. Твоё текущее время для отправки цитат: {existing_user[2]}.\n\n"
            "Чтобы начать настройку заново напиши /reset.",
            reply_markup=ReplyKeyboardMarkup(
                [["Установить время", "Случайная цитата"], ["Предложить цитату"]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    existing_user = db.get_user(user.id)
    if existing_user:
        db.delete_user(user.id)
        await update.message.reply_text(
            "Я удалил все твои данные, теперь можем начать заново!\n\n"
            "Для этого напиши /start или нажми кнопку ниже.",
            reply_markup=ReplyKeyboardMarkup(
                [["Начать"]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )


async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    existing_user = db.get_user(user.id)
    if existing_user:
        await update.message.reply_text(
            "Пожалуйста, укажи время в формате ЧЧ:ММ.",
            reply_markup=ReplyKeyboardMarkup(
                [["09:00", "18:00"], ["Отмена"]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        return AWAIT_TIME


async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    existing_user = db.get_user(user.id)
    if existing_user:
        time = update.message.text

        if time.lower() == "отмена":
            await cancel(update, context)

        try:
            hours, minutes = map(int, time.split(":"))
            if not (0 <= hours < 24 and 0 <= minutes < 60):
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "Неправильный формат времени. Используй ЧЧ:ММ."
            )
            return AWAIT_TIME

        db.update_user_time(user.id, time)
        await update.message.reply_text(
            f"Время для получения цитат обновлено на {time}.",
            reply_markup=ReplyKeyboardMarkup(
                [["Установить время", "Случайная цитата"], ["Предложить цитату"]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    existing_user = db.get_user(user.id)
    if existing_user:
        await update.message.reply_text(
            "Ввод отменен.",
            reply_markup=ReplyKeyboardMarkup(
                [["Установить время", "Случайная цитата"], ["Предложить цитату"]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        return ConversationHandler.END


async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    existing_user = db.get_user(user.id)
    if existing_user:
        quote_data = db.get_random_quote(user.id)
        if quote_data:
            await update.message.reply_text(
                f'*"{quote_data[0]}"* — _{quote_data[1]}_',
                parse_mode="MarkdownV2",
                reply_markup=ReplyKeyboardMarkup(
                    [["Установить время", "Случайная цитата"], ["Предложить цитату"]],
                    one_time_keyboard=True,
                    resize_keyboard=True,
                ),
            )
        else:
            await update.message.reply_text("Цитаты отсутствуют.")


async def propose_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    existing_user = db.get_user(user.id)
    if existing_user:
        await update.message.reply_text(
            "Пожалуйста, введи цитату в формате: <цитата> - <автор> (дефис обязателен)",
            reply_markup=ReplyKeyboardMarkup(
                [["Отмена"]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        return AWAIT_QUOTE


async def receive_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    existing_user = db.get_user(user.id)
    if existing_user:
        text = update.message.text.strip()

        if text.lower() == "отмена":
            await cancel(update, context)

        quote_pattern = re.compile(r'["“]?(.*?)["”]?\s*-\s*(.*)')

        match = quote_pattern.search(text)

        if match:
            quote, author = match.group(1).strip(), match.group(2).strip()

            if not quote or not author:
                await update.message.reply_text(
                    "Неправильный формат. Пожалуйста, используй формат: <цитата> - <автор> (дефис обязателен)"
                )
                return AWAIT_QUOTE

            quote_id = db.add_pending_quote(user.id, quote, author)

            escaped_quote, escaped_author = escape_markdown((quote, author))

            admin_chat_id = ADMIN_IDS[0]
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=f'{user.username} предлагает цитату: *"{escaped_quote}"* — _{escaped_author}_',
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Принять",
                                callback_data=f"accept_{user.id}_{quote_id}",
                            ),
                            InlineKeyboardButton(
                                "Отклонить",
                                callback_data=f"reject_{user.id}_{quote_id}",
                            ),
                        ]
                    ]
                ),
            )

            await update.message.reply_text(
                "Цитата отправлена на рассмотрение.",
                reply_markup=ReplyKeyboardMarkup(
                    [["Установить время", "Случайная цитата"], ["Предложить цитату"]],
                    one_time_keyboard=True,
                    resize_keyboard=True,
                ),
            )
        else:
            await update.message.reply_text(
                "Неправильный формат. Пожалуйста, используй формат: <цитата> - <автор> (дефис обязателен)"
            )
            return AWAIT_QUOTE

        return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    existing_user = db.get_user(user.id)
    if existing_user:
        if not await check_admin(update):
            help_text = (
                "Доступные команды:\n"
                "/settime - Установить время для получения цитат\n"
                "/quote - Получить случайную цитату\n"
                "/propose - Предложить свою цитату\n"
                "/help - Показать это сообщение"
            )
        else:
            help_text = (
                "Доступные команды:\n"
                "/settime - Установить время для получения цитат\n"
                "/quote - Получить случайную цитату\n"
                "/propose - Предложить свою цитату\n"
                "/help - Показать это сообщение\n"
                "/addquote <цитата> <автор> - Добавить новую цитату (админ)\n"
                "/listquotes - Просмотреть все цитаты (админ)\n"
                "/deletequote <номер цитаты> - Удалить цитату (админ)\n"
                "/disable - Отключить бота (админ)\n"
                "/enable - Включить бота (админ)"
            )

        await update.message.reply_text(
            help_text,
            reply_markup=ReplyKeyboardMarkup(
                [["Установить время", "Случайная цитата"], ["Предложить цитату"]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
