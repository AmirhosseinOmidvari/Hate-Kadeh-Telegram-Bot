from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from bot.config import Config
from bot.database import SessionLocal
from bot.models import ChannelMessage, Reply
from bot.utils import logger
from bot.security import decrypt_value, encrypt_value
import asyncio
from typing import Callable, Any

_send_semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_SENDS)


async def _with_retry(callable_fn: Callable[..., Any], *args, **kwargs):
    """Call an async send function with retries and exponential backoff."""
    last_exc = None
    for attempt in range(1, max(1, Config.SEND_RETRIES) + 1):
        try:
            async with _send_semaphore:
                return await callable_fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            logger.warning(f"ارسال به تلگرام ناموفق (attempt {attempt}): {e}")
            backoff = float(Config.SEND_BACKOFF_BASE) * (2 ** (attempt - 1))
            await asyncio.sleep(backoff)
    logger.error(f"ارسال به تلگرام بعد از {Config.SEND_RETRIES} تلاش ناموفق بود: {last_exc}")
    raise last_exc


def build_reply_link(channel_msg_id: int) -> str:
    bot_username = (Config.BOT_USERNAME or "").lstrip("@")
    if not bot_username:
        return ""
    return f"https://t.me/{bot_username}?start=reply_{channel_msg_id}"


def _reply_keyboard(channel_msg_id: int):
    reply_link = build_reply_link(channel_msg_id)
    if reply_link:
        return InlineKeyboardMarkup([[InlineKeyboardButton("💬 پاسخ در ربات", url=reply_link)]])
    return InlineKeyboardMarkup([[InlineKeyboardButton("💬 پاسخ به این پیام", callback_data=f"reply_{channel_msg_id}")]])

async def send_to_channel(pending, bot: Bot):
    try:
        caption = f"📢 پیام ناشناس:\n\n{decrypt_value(pending.message_text) or ''}"
        file_id = decrypt_value(pending.file_id) if pending.file_id else None

        if pending.message_type == "text":
            sent = await _with_retry(bot.send_message,
                chat_id=Config.CHANNEL_ID,
                text=caption,
            )
        elif pending.message_type == "photo":
            sent = await _with_retry(bot.send_photo,
                chat_id=Config.CHANNEL_ID,
                photo=file_id,
                caption=caption,
            )
        elif pending.message_type == "video":
            sent = await _with_retry(bot.send_video,
                chat_id=Config.CHANNEL_ID,
                video=file_id,
                caption=caption,
            )
        elif pending.message_type == "document":
            sent = await _with_retry(bot.send_document,
                chat_id=Config.CHANNEL_ID,
                document=file_id,
                caption=caption,
            )
        elif pending.message_type == "voice":
            sent = await _with_retry(bot.send_voice,
                chat_id=Config.CHANNEL_ID,
                voice=file_id,
                caption=caption,
            )
        elif pending.message_type == "sticker":
            sent = await _with_retry(bot.send_sticker,
                chat_id=Config.CHANNEL_ID,
                sticker=file_id,
            )
        elif pending.message_type == "animation":
            sent = await _with_retry(bot.send_animation,
                chat_id=Config.CHANNEL_ID,
                animation=file_id,
                caption=caption,
            )
        elif pending.message_type == "video_note":
            sent = await _with_retry(bot.send_video_note,
                chat_id=Config.CHANNEL_ID,
                video_note=file_id,
            )
        else:
            sent = await _with_retry(bot.send_message,
                chat_id=Config.CHANNEL_ID,
                text=caption,
            )

        db = SessionLocal()
        try:
            ch_msg = ChannelMessage(
                channel_msg_id=sent.message_id,
                original_sender_id=pending.sender_id,
                original_pending_id=pending.id,
                message_text=pending.message_text,
                message_type=pending.message_type,
                file_id=pending.file_id
            )
            db.add(ch_msg)
            db.commit()
        finally:
            db.close()

        try:
            await bot.edit_message_reply_markup(
                chat_id=Config.CHANNEL_ID,
                message_id=sent.message_id,
                reply_markup=_reply_keyboard(sent.message_id),
            )
        except Exception as edit_error:
            logger.warning(f"امکان به‌روزرسانی دکمه پاسخ برای پیام {sent.message_id} نبود: {edit_error}")

        logger.info(f"پیام {pending.id} به کانال ارسال شد - message_id: {sent.message_id}")
        return sent.message_id
    except Exception as e:
        logger.error(f"خطا در ارسال به کانال: {e}")
        return None


async def send_reply_to_channel(reply: Reply, bot: Bot):
    """Send an approved reply to the channel, falling back to no-reply if the
    original message was deleted."""
    try:
        caption = decrypt_value(reply.reply_text) or ""
        file_id = decrypt_value(reply.file_id)

        send_methods = {
            "text": lambda kw: bot.send_message(
                chat_id=Config.CHANNEL_ID,
                text=f"💬 پاسخ تایید شده:\n\n{caption}",
                **kw,
            ),
            "photo": lambda kw: bot.send_photo(
                chat_id=Config.CHANNEL_ID,
                photo=file_id,
                caption=caption,
                **kw,
            ),
            "video": lambda kw: bot.send_video(
                chat_id=Config.CHANNEL_ID,
                video=file_id,
                caption=caption,
                **kw,
            ),
            "document": lambda kw: bot.send_document(
                chat_id=Config.CHANNEL_ID,
                document=file_id,
                caption=caption,
                **kw,
            ),
            "voice": lambda kw: bot.send_voice(
                chat_id=Config.CHANNEL_ID,
                voice=file_id,
                caption=caption,
                **kw,
            ),
            "sticker": lambda kw: bot.send_sticker(
                chat_id=Config.CHANNEL_ID,
                sticker=file_id,
                **kw,
            ),
            "animation": lambda kw: bot.send_animation(
                chat_id=Config.CHANNEL_ID,
                animation=file_id,
                caption=caption,
                **kw,
            ),
            "video_note": lambda kw: bot.send_video_note(
                chat_id=Config.CHANNEL_ID,
                video_note=file_id,
                **kw,
            ),
        }

        sender = send_methods.get(reply.reply_type, send_methods["text"])
        kwargs = {"reply_to_message_id": reply.channel_msg_id}

        try:
            sent = await _with_retry(sender, kwargs)
        except Exception as e:
            if "Message to be replied not found" in str(e):
                logger.warning(
                    f"پیام مرجع برای پاسخ {reply.id} پیدا نشد، ارسال بدون ریپلای انجام می‌شود."
                )
                sent = await _with_retry(sender, {})
            else:
                raise

        logger.info(f"پاسخ {reply.id} در کانال منتشر شد - message_id: {sent.message_id}")
        return sent.message_id
    except Exception as e:
        logger.error(f"خطا در ارسال پاسخ به کانال: {e}")
        return None