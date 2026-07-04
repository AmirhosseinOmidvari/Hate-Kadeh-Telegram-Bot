from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import or_
from bot.database import SessionLocal
from bot.models import PendingMessage, Reply, ChannelMessage
from bot.utils import logger
from bot.security import encrypt_value
from bot.handlers.channel import build_reply_link

SENDING_MESSAGE = 1
WAITING_FOR_REPLY = 2


def _main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📩 ارسال پیام ناشناس", callback_data="send_anonymous")],
    
        [InlineKeyboardButton("📚 راهنما", callback_data="help_menu"), InlineKeyboardButton("🛡 قوانین", callback_data="rules_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def _main_menu_text(user_first_name: str | None = None) -> str:
    greeting = f"👋 سلام {user_first_name}!\n\n" if user_first_name else "👋 سلام!\n\n"
    return (
        f"{greeting}✨ به **Hate Kadeh** خوش اومدی.\n\n"
        "از اینجا می‌تونی:\n"
        "• پیام ناشناس بفرستی\n"
        "• روی پست‌های کانال پاسخ بدی\n"
        "• بعد از تایید ادمین، پاسخت را زیر همان پیام ببینی\n\n"
        "دکمه‌های پایین برای دسترسی سریع‌تر هستند."
    )


def _resolve_reply_target(db, payload_value: int) -> int | None:
    channel_message = (
        db.query(ChannelMessage)
        .filter(
            or_(
                ChannelMessage.channel_msg_id == payload_value,
                ChannelMessage.original_pending_id == payload_value,
            )
        )
        .first()
    )
    if channel_message:
        return channel_message.channel_msg_id
    return payload_value

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        payload = context.args[0] if context.args else ""

        if payload.startswith("reply_"):
            try:
                channel_msg_id = int(payload.split("_", 1)[1])
            except (IndexError, ValueError):
                channel_msg_id = None

            if channel_msg_id:
                db = SessionLocal()
                try:
                    resolved_channel_msg_id = _resolve_reply_target(db, channel_msg_id)
                finally:
                    db.close()

                context.user_data["replying_to_channel_msg_id"] = channel_msg_id
                if resolved_channel_msg_id:
                    context.user_data["replying_to_channel_msg_id"] = resolved_channel_msg_id
                await update.message.reply_text(
                    "💬 پاسخ آماده است.\n\n"
                    "فقط یکی از این‌ها را بفرست:\n"
                    "• متن\n"
                    "• عکس\n"
                    "• ویدیو\n"
                    "• فایل\n"
                    "• ویس\n\n"
                    "بعد از ثبت، پاسخ وارد صف تایید می‌شود و پس از تایید زیر همان پیام اصلی نمایش داده می‌شود.\n\n"
                    "برای لغو /cancel را بزن.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت به منو", callback_data="back_home")]])
                )
                return WAITING_FOR_REPLY
    except Exception as e:
        logger.exception("خطا در هندلر start:")
        try:
            if update.message:
                await update.message.reply_text("⚠️ خطایی رخ داد، لطفاً دوباره تلاش کن.")
        except Exception:
            pass
        return ConversationHandler.END

    await update.message.reply_text(
        _main_menu_text(user.first_name),
        reply_markup=_main_menu_keyboard(),
        parse_mode='Markdown'
    )
    return SENDING_MESSAGE


async def open_reply_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    try:
        if not query.data:
            await query.answer()
            return

        try:
            channel_msg_id = int(query.data.split("_", 1)[1])
        except (IndexError, ValueError):
            await query.answer("لینک پاسخ نامعتبر است.", show_alert=True)
            return

        reply_link = build_reply_link(channel_msg_id)
        if not reply_link:
            await query.answer("برای فعال شدن پاسخ، BOT_USERNAME باید تنظیم شده باشد.", show_alert=True)
            return

        await query.answer("برای پاسخ دادن، دکمه را دوباره بزن یا لینک را باز کن.", show_alert=False)
    except Exception as e:
        logger.exception("خطا در open_reply_link:")
        try:
            await query.answer("⚠️ خطایی رخ داد، دوباره تلاش کن.", show_alert=True)
        except Exception:
            pass
        return

async def send_anonymous_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✍️ پیام ناشناس خودت را بفرست.\n\n"
        "می‌تونی یکی از این موارد را ارسال کنی:\n"
        "• متن\n"
        "• عکس\n"
        "• ویدیو\n"
        "• فایل\n"
        "• ویس\n\n"
        "بعد از ارسال، پیام وارد صف تایید می‌شود و فقط بعد از تایید ادمین در کانال منتشر می‌شود.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت به منوی اصلی", callback_data="back_home")]])
    )
    return SENDING_MESSAGE


async def back_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        _main_menu_text(query.from_user.first_name),
        reply_markup=_main_menu_keyboard(),
        parse_mode='Markdown'
    )
    return SENDING_MESSAGE


async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📚 راهنما\n\n"
        "1. روی «ارسال پیام ناشناس» بزن و محتوای خودت را بفرست.\n"
        "2. برای جواب دادن به پیام‌های کانال، از دکمه پاسخ همان پست استفاده کن.\n"
        "3. اگر عکس، ویدیو، فایل یا ویس بفرستی، ادمین قبل از تایید محتوا را می‌بیند.\n"
        "4. همه پاسخ‌ها بعد از تایید ادمین منتشر می‌شوند.\n\n"
        "برای برگشت از دکمه زیر استفاده کن.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت به منوی اصلی", callback_data="back_home")]])
    )
    return SENDING_MESSAGE


async def rules_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🛡 قوانین\n\n"
        "• پیام‌های توهین‌آمیز، اسپم یا محتوای مخرب ممکن است حذف شوند.\n"
        "• برای حفظ ناشناس بودن، اطلاعات شخصی نفرست.\n"
        "• رسانه‌ها و پاسخ‌ها بعد از بررسی منتشر می‌شوند.\n\n"
        "برگشت به منوی اصلی:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت به منوی اصلی", callback_data="back_home")]])
    )
    return SENDING_MESSAGE

async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message

    message_type = "text"
    file_id = None
    content = ""

    if msg.text:
        message_type = "text"
        content = msg.text.strip()
    elif msg.photo:
        message_type = "photo"
        file_id = msg.photo[-1].file_id
        content = msg.caption.strip() if msg.caption else "📸 عکس"
    elif msg.video:
        message_type = "video"
        file_id = msg.video.file_id
        content = msg.caption.strip() if msg.caption else "🎥 ویدیو"
    elif msg.document:
        message_type = "document"
        file_id = msg.document.file_id
        content = msg.caption.strip() if msg.caption else f"📄 فایل: {msg.document.file_name}"
    elif msg.voice:
        message_type = "voice"
        file_id = msg.voice.file_id
        content = "🎙 پیام صوتی"
    else:
        await update.message.reply_text("❌ این نوع پیام پشتیبانی نمی‌شه.")
        return SENDING_MESSAGE

    if not content and message_type == "text":
        await update.message.reply_text("❌ پیام خالی نمی‌تونه باشه.")
        return SENDING_MESSAGE

    db = SessionLocal()
    pending = PendingMessage(
        sender_id=user_id,
        message_text=encrypt_value(content[:1000]),
        message_type=message_type,
        file_id=encrypt_value(file_id),
    )
    db.add(pending)
    db.commit()
    msg_id = pending.id
    db.close()

    logger.info(f"پیام جدید از کاربر {user_id} - نوع: {message_type} - آیدی: {msg_id}")
    await update.message.reply_text(
        f"✅ پیامت با موفقیت دریافت شد! (آیدی: {msg_id})\n"
        "بعد از تایید ادمین در کانال منتشر میشه."
    )
    return ConversationHandler.END


async def receive_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        channel_msg_id = context.user_data.get("replying_to_channel_msg_id")

        if not channel_msg_id:
            await update.message.reply_text("❌ برای ثبت پاسخ، دوباره از دکمه پاسخ در کانال استفاده کن.")
            return ConversationHandler.END

        msg = update.message
        message_type = "text"
        file_id = None
        content = ""

        if msg.text:
            content = msg.text.strip()
        elif msg.photo:
            message_type = "photo"
            file_id = msg.photo[-1].file_id
            content = msg.caption.strip() if msg.caption else "📸 عکس"
        elif msg.video:
            message_type = "video"
            file_id = msg.video.file_id
            content = msg.caption.strip() if msg.caption else "🎥 ویدیو"
        elif msg.document:
            message_type = "document"
            file_id = msg.document.file_id
            content = msg.caption.strip() if msg.caption else f"📄 فایل: {msg.document.file_name}"
        elif msg.voice:
            message_type = "voice"
            file_id = msg.voice.file_id
            content = "🎙 پیام صوتی"
        else:
            await update.message.reply_text("❌ این نوع پاسخ پشتیبانی نمی‌شه.")
            return WAITING_FOR_REPLY

        if not content and message_type == "text":
            await update.message.reply_text("❌ پاسخ خالی نمی‌تونه باشه.")
            return WAITING_FOR_REPLY

        db = SessionLocal()
        reply = Reply(
            channel_msg_id=channel_msg_id,
            replier_id=user_id,
            reply_text=encrypt_value(content[:1000]),
            reply_type=message_type,
            file_id=encrypt_value(file_id),
            is_approved=False,
        )
        db.add(reply)
        db.commit()
        reply_id = reply.id
        db.close()

        context.user_data.pop("replying_to_channel_msg_id", None)

        await update.message.reply_text(
            f"✅ پاسخ شما ثبت شد و برای تایید ادمین ارسال شد. (آیدی: {reply_id})\n"
            "بعد از تایید، پاسخ دقیقاً زیر همان پیام در کانال نمایش داده می‌شود."
        )
        return ConversationHandler.END
    except Exception as e:
        logger.exception("خطا در receive_reply:")
        try:
            await update.message.reply_text("⚠️ خطایی رخ داد، لطفاً دوباره تلاش کن.")
        except Exception:
            pass
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("replying_to_channel_msg_id", None)
    await update.message.reply_text("❌ عملیات لغو شد. برای شروع دوباره /start رو بزن.")
    return ConversationHandler.END