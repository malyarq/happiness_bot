import logging
from log_config import setup_logging

setup_logging()
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    CallbackQueryHandler,
)
from admin import (
    add_quote,
    list_quotes,
    delete_quote,
    handle_quote_decision,
    disable_bot,
    enable_bot,
)
from handlers import (
    start,
    reset,
    set_time,
    quote,
    help_command,
    button_handler,
    receive_time,
    propose_quote,
    receive_quote,
    cancel,
    AWAIT_TIME,
    AWAIT_QUOTE,
)
from scheduler import start_scheduler
from config import TOKEN


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("quote", quote))
    app.add_handler(CommandHandler("addquote", add_quote))
    app.add_handler(CommandHandler("listquotes", list_quotes))
    app.add_handler(CommandHandler("deletequote", delete_quote))
    app.add_handler(CommandHandler("disable", disable_bot))
    app.add_handler(CommandHandler("enable", enable_bot))
    app.add_handler(CommandHandler("help", help_command))

    time_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("settime", set_time),
            MessageHandler(filters.Regex("^(Установить время)$"), set_time),
        ],
        states={
            AWAIT_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(time_conv_handler)

    propose_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("propose", propose_quote),
            MessageHandler(filters.Regex("^(Предложить цитату)$"), propose_quote),
        ],
        states={
            AWAIT_QUOTE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quote),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(propose_conv_handler)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

    app.add_handler(CallbackQueryHandler(handle_quote_decision))

    start_scheduler()

    logging.info("Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    main()
