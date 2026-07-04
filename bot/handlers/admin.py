from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import Config
from bot.database import SessionLocal
from bot.models import PendingMessage, Reply
from bot.utils import escape_markdown, format_tehran_datetime, is_admin, logger, now_tehran, truncate
from bot.handlers.channel import send_to_channel, send_reply_to_channel
from bot.security import decrypt_value
from datetime import datetime


async def _safe_result_message(query, text: str) -> None:
    try:
        await query.edit_message_text(text)
    except Exception:
        await query.message.reply_text(text)


def _message_preview_caption(title: str, sender_id: int, item_id: int, content_text: str, created_at: datetime, message_type: str) -> str:
    return (
        f"{title}\n\n"
        f"🆔 **آیدی:** {item_id}\n"
        f"👤 **فرستنده:** `{sender_id}`\n"
        f"📝 **متن:** {escape_markdown(truncate(content_text, 120))}\n"
        f"📅 **زمان:** {escape_markdown(format_tehran_datetime(created_at))}\n"
        f"📎 **نوع:** {escape_markdown(message_type)}"
    )


async def _send_pending_preview(query, pending: PendingMessage) -> None:
    file_id = decrypt_value(pending.file_id) if pending.file_id else None
    content_text = decrypt_value(pending.message_text) or ""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تایید", callback_data=f"approve_{pending.id}"),
         InlineKeyboardButton("❌ رد", callback_data=f"reject_{pending.id}")],
        [InlineKeyboardButton("🔍 جزئیات", callback_data=f"detail_{pending.id}")]
    ])

    caption = _message_preview_caption("📥 **پیام تایید نشده**", pending.sender_id, pending.id, content_text, pending.created_at, pending.message_type)

    if pending.message_type == "photo" and file_id:
        await query.message.reply_photo(photo=file_id, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
    elif pending.message_type == "video" and file_id:
        await query.message.reply_video(video=file_id, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
    elif pending.message_type == "document" and file_id:
        await query.message.reply_document(document=file_id, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
    elif pending.message_type == "voice" and file_id:
        await query.message.reply_voice(voice=file_id, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
    else:
        await query.message.reply_text(caption, reply_markup=keyboard, parse_mode='Markdown')


async def _send_reply_preview(query, reply: Reply) -> None:
    file_id = decrypt_value(reply.file_id) if reply.file_id else None
    reply_text = decrypt_value(reply.reply_text) or ""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تایید", callback_data=f"reply_approve_{reply.id}"),
         InlineKeyboardButton("❌ رد", callback_data=f"reply_reject_{reply.id}")],
        [InlineKeyboardButton("🔍 جزئیات", callback_data=f"reply_detail_{reply.id}")]
    ])

    caption = _message_preview_caption("💬 **پاسخ تایید نشده**", reply.replier_id, reply.id, reply_text, reply.created_at, reply.reply_type)
    caption += f"\n🔗 **آیدی پیام کانال:** `{reply.channel_msg_id}`"

    if reply.reply_type == "photo" and file_id:
        await query.message.reply_photo(photo=file_id, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
    elif reply.reply_type == "video" and file_id:
        await query.message.reply_video(video=file_id, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
    elif reply.reply_type == "document" and file_id:
        await query.message.reply_document(document=file_id, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
    elif reply.reply_type == "voice" and file_id:
        await query.message.reply_voice(voice=file_id, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
    else:
        await query.message.reply_text(caption, reply_markup=keyboard, parse_mode='Markdown')

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id, Config.ADMIN_IDS):
        await update.message.reply_text("⛔ شما دسترسی به پنل مدیریت ندارید.")
        return
    keyboard = [
        [InlineKeyboardButton("📥 پیام‌های تایید نشده", callback_data="admin_pending")],
        [InlineKeyboardButton("💬 پاسخ‌های تایید نشده", callback_data="admin_replies")]
    ]
    await update.message.reply_text(
        "👑 **پنل مدیریت ربات** 👑\n\n"
        "از اینجا فقط پیام‌ها و پاسخ‌های در صف تایید را می‌بینی.\n"
        "برای بررسی کامل، یکی از گزینه‌های زیر را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id, Config.ADMIN_IDS):
        await query.edit_message_text("⛔ دسترسی ندارید.")
        return
    db = SessionLocal()
    pendings = db.query(PendingMessage).filter_by(is_approved=False).order_by(PendingMessage.created_at).all()
    db.close()
    if not pendings:
        await query.edit_message_text("📭 هیچ پیام تایید نشده‌ای وجود ندارد.")
        return
    for p in pendings[:10]:
        await _send_pending_preview(query, p)
    if len(pendings) > 10:
        await query.message.reply_text("⚠️ فقط 10 پیام آخر نمایش داده شد. بقیه رو از پنل وب مدیریت کن.")


async def list_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id, Config.ADMIN_IDS):
        await query.edit_message_text("⛔ دسترسی ندارید.")
        return

    db = SessionLocal()
    replies = db.query(Reply).filter_by(is_approved=False).order_by(Reply.created_at).all()
    db.close()

    if not replies:
        await query.edit_message_text("📭 هیچ پاسخ تایید نشده‌ای وجود ندارد.")
        return

    for reply in replies[:10]:
        await _send_reply_preview(query, reply)

    if len(replies) > 10:
        await query.message.reply_text("⚠️ فقط 10 پاسخ آخر نمایش داده شد. بقیه رو از پنل وب مدیریت کن.")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id
    if not is_admin(admin_id, Config.ADMIN_IDS):
        await query.edit_message_text("⛔ دسترسی ندارید.")
        return
    pending_id = int(query.data.split('_')[1])
    db = SessionLocal()
    pending = db.query(PendingMessage).filter_by(id=pending_id).first()
    if not pending or pending.is_approved:
        await query.edit_message_text("⚠️ پیام قبلاً تایید شده یا وجود ندارد.")
        db.close()
        return
    channel_msg_id = await send_to_channel(pending, context.bot)
    if channel_msg_id:
        pending.is_approved = True
        pending.approved_by = admin_id
        pending.approved_at = now_tehran()
        pending.channel_message_id = channel_msg_id
        db.commit()
        logger.info(f"پیام {pending_id} توسط ادمین {admin_id} تایید شد.")
        await _safe_result_message(query, f"✅ پیام {pending_id} تایید و در کانال منتشر شد.")
    else:
        await _safe_result_message(query, "❌ خطا در ارسال به کانال. لطفاً دوباره تلاش کن.")
    db.close()

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id
    if not is_admin(admin_id, Config.ADMIN_IDS):
        await query.edit_message_text("⛔ دسترسی ندارید.")
        return
    pending_id = int(query.data.split('_')[1])
    db = SessionLocal()
    pending = db.query(PendingMessage).filter_by(id=pending_id).first()
    if pending and not pending.is_approved:
        db.delete(pending)
        db.commit()
        logger.info(f"پیام {pending_id} توسط ادمین {admin_id} حذف شد.")
        await _safe_result_message(query, f"❌ پیام {pending_id} حذف شد.")
    else:
        await _safe_result_message(query, "⚠️ پیام پیدا نشد یا قبلاً تایید شده.")
    db.close()

async def detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id, Config.ADMIN_IDS):
        await query.edit_message_text("⛔ دسترسی ندارید.")
        return
    pending_id = int(query.data.split('_')[1])
    db = SessionLocal()
    pending = db.query(PendingMessage).filter_by(id=pending_id).first()
    db.close()
    if not pending:
        await query.edit_message_text("پیام پیدا نشد.")
        return
    message_text = decrypt_value(pending.message_text) or ""
    text = (
        f"🔍 **جزئیات پیام #{pending.id}**\n\n"
        f"👤 **فرستنده:** `{pending.sender_id}`\n"
        f"📝 **متن کامل:**\n{escape_markdown(message_text)}\n\n"
        f"📎 **نوع:** {escape_markdown(pending.message_type)}\n"
        f"📅 **زمان ارسال:** {escape_markdown(format_tehran_datetime(pending.created_at))}\n"
        f"✅ **وضعیت:** {escape_markdown('تایید شده' if pending.is_approved else 'در انتظار تایید')}\n"
    )
    if pending.is_approved:
        text += f"👑 **تاییدکننده:** `{pending.approved_by}`\n📆 **زمان تایید:** {escape_markdown(format_tehran_datetime(pending.approved_at))}"
    await query.edit_message_text(text, parse_mode='Markdown')


async def approve_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id
    if not is_admin(admin_id, Config.ADMIN_IDS):
        await query.edit_message_text("⛔ دسترسی ندارید.")
        return

    reply_id = int(query.data.split('_')[2])
    db = SessionLocal()
    reply = db.query(Reply).filter_by(id=reply_id).first()
    if not reply or reply.is_approved:
        await query.edit_message_text("⚠️ پاسخ قبلاً تایید شده یا وجود ندارد.")
        db.close()
        return

    sent_message_id = await send_reply_to_channel(reply, context.bot)
    if sent_message_id:
        reply.is_approved = True
        reply.approved_by = admin_id
        reply.approved_at = now_tehran()
        reply.bot_reply_msg_id = sent_message_id
        db.commit()
        logger.info(f"پاسخ {reply_id} توسط ادمین {admin_id} تایید شد.")
        await _safe_result_message(query, f"✅ پاسخ {reply_id} تایید و در کانال منتشر شد.")
    else:
        await _safe_result_message(query, "❌ خطا در ارسال پاسخ به کانال. لطفاً دوباره تلاش کن.")
    db.close()


async def reject_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id
    if not is_admin(admin_id, Config.ADMIN_IDS):
        await query.edit_message_text("⛔ دسترسی ندارید.")
        return

    reply_id = int(query.data.split('_')[2])
    db = SessionLocal()
    reply = db.query(Reply).filter_by(id=reply_id).first()
    if reply and not reply.is_approved:
        db.delete(reply)
        db.commit()
        logger.info(f"پاسخ {reply_id} توسط ادمین {admin_id} حذف شد.")
        await _safe_result_message(query, f"❌ پاسخ {reply_id} حذف شد.")
    else:
        await _safe_result_message(query, "⚠️ پاسخ پیدا نشد یا قبلاً تایید شده.")
    db.close()


async def detail_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id, Config.ADMIN_IDS):
        await query.edit_message_text("⛔ دسترسی ندارید.")
        return

    reply_id = int(query.data.split('_')[2])
    db = SessionLocal()
    reply = db.query(Reply).filter_by(id=reply_id).first()
    db.close()

    if not reply:
        await query.edit_message_text("پاسخ پیدا نشد.")
        return

    reply_text = decrypt_value(reply.reply_text) or ""
    text = (
        f"🔍 **جزئیات پاسخ #{reply.id}**\n\n"
        f"🔗 **آیدی پیام کانال:** `{reply.channel_msg_id}`\n"
        f"👤 **فرستنده پاسخ:** `{reply.replier_id}`\n"
        f"📝 **متن کامل:**\n{escape_markdown(reply_text)}\n\n"
        f"📎 **نوع:** {escape_markdown(reply.reply_type)}\n"
        f"📅 **زمان ارسال:** {escape_markdown(format_tehran_datetime(reply.created_at))}\n"
        f"✅ **وضعیت:** {escape_markdown('تایید شده' if reply.is_approved else 'در انتظار تایید')}\n"
    )
    if reply.is_approved:
        text += f"👑 **تاییدکننده:** `{reply.approved_by}`\n📆 **زمان تایید:** {escape_markdown(format_tehran_datetime(reply.approved_at))}"
    await query.edit_message_text(text, parse_mode='Markdown')