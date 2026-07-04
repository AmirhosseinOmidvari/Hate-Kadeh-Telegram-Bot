import logging
import warnings
import sys
from pathlib import Path
from telegram.warnings import PTBUserWarning
from telegram import BotCommand, MenuButtonCommands

warnings.filterwarnings("ignore", category=PTBUserWarning)

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)
from telegram.request import HTTPXRequest
from bot.config import Config
from bot.handlers.user import (
    start,
    send_anonymous_callback,
    back_home,
    help_menu,
    rules_menu,
    open_reply_link,
    receive_message,
    cancel,
    SENDING_MESSAGE,
    WAITING_FOR_REPLY,
    receive_reply,
)
from bot.handlers.admin import (
    admin_panel,
    list_pending,
    list_replies,
    approve,
    reject,
    detail,
    approve_reply,
    reject_reply,
    detail_reply,
)
from bot.database import Base, engine
from bot.models import PendingMessage, ChannelMessage, Reply, Admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_bot(application):
    await application.bot.set_my_commands([
        BotCommand("start", "نمایش منوی اصلی"),
        BotCommand("admin", "باز کردن پنل ادمین"),
        BotCommand("cancel", "لغو عملیات جاری"),
    ])
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())


def main():
    Base.metadata.create_all(engine)

    proxy_url = Config.PROXY_URL
    if proxy_url:
        request = HTTPXRequest(proxy_url=proxy_url, connection_pool_size=25, connect_timeout=30.0, read_timeout=30.0)
        logger.info(f"استفاده از پروکسی: {proxy_url}")
        app = ApplicationBuilder().token(Config.BOT_TOKEN).request(request).post_init(setup_bot).build()
    else:
        request = HTTPXRequest(connection_pool_size=1, connect_timeout=30.0, read_timeout=30.0)
        logger.info("بدون پروکسی، اتصال مستقیم برقرار می‌شود")
        app = ApplicationBuilder().token(Config.BOT_TOKEN).request(request).post_init(setup_bot).build()

    conv_send = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(send_anonymous_callback, pattern="^send_anonymous$"),
            CallbackQueryHandler(back_home, pattern="^back_home$"),
            CallbackQueryHandler(help_menu, pattern="^help_menu$"),
            CallbackQueryHandler(rules_menu, pattern="^rules_menu$"),
        ],
        states={
            SENDING_MESSAGE: [
                MessageHandler(filters.ALL & ~filters.COMMAND, receive_message)
            ],
            WAITING_FOR_REPLY: [
                MessageHandler(filters.ALL & ~filters.COMMAND, receive_reply)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_send)
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(list_pending, pattern="^admin_pending$"))
    app.add_handler(CallbackQueryHandler(list_replies, pattern="^admin_replies$"))
    app.add_handler(CallbackQueryHandler(approve, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject, pattern="^reject_"))
    app.add_handler(CallbackQueryHandler(detail, pattern="^detail_"))
    app.add_handler(CallbackQueryHandler(approve_reply, pattern="^reply_approve_"))
    app.add_handler(CallbackQueryHandler(reject_reply, pattern="^reply_reject_"))
    app.add_handler(CallbackQueryHandler(detail_reply, pattern="^reply_detail_"))
    app.add_handler(CallbackQueryHandler(open_reply_link, pattern="^reply_\\d+$"))

    logger.info("🤖 ربات Hate Kadeh با پروکسی روشن شد...")
    app.run_polling(
    drop_pending_updates=True,
    close_loop=False
    )



if __name__ == "__main__":
    main()