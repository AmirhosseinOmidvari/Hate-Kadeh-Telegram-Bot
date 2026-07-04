from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Boolean
from bot.utils import now_tehran
from bot.database import Base

class PendingMessage(Base):
    __tablename__ = "pending_messages"
    id = Column(Integer, primary_key=True)
    sender_id = Column(BigInteger, nullable=False)
    message_text = Column(Text, nullable=True)
    message_type = Column(String(50), default="text")
    file_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=now_tehran)
    is_approved = Column(Boolean, default=False)
    approved_by = Column(BigInteger, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    channel_message_id = Column(Integer, nullable=True)

class ChannelMessage(Base):
    __tablename__ = "channel_messages"
    id = Column(Integer, primary_key=True)
    channel_msg_id = Column(Integer, unique=True, nullable=False)
    original_sender_id = Column(BigInteger, nullable=False)
    original_pending_id = Column(Integer, nullable=False)
    message_text = Column(Text, nullable=True)
    message_type = Column(String(50), default="text")
    file_id = Column(String(255), nullable=True)
    sent_at = Column(DateTime, default=now_tehran)

class Reply(Base):
    __tablename__ = "replies"
    id = Column(Integer, primary_key=True)
    channel_msg_id = Column(Integer, nullable=False)
    replier_id = Column(BigInteger, nullable=False)
    reply_text = Column(Text, nullable=True)
    reply_type = Column(String(50), default="text")
    file_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=now_tehran)
    is_approved = Column(Boolean, default=False)
    approved_by = Column(BigInteger, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    bot_reply_msg_id = Column(Integer, nullable=True)

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    is_owner = Column(Boolean, default=False)
    added_at = Column(DateTime, default=now_tehran)