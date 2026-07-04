from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from telegram import Bot

from bot.database import SessionLocal
from bot.models import PendingMessage, ChannelMessage, Reply
from bot.config import Config
from bot.handlers.channel import send_to_channel, send_reply_to_channel
from bot.database import run_db_task
from bot.utils import now_tehran
from bot.security import decrypt_value
import secrets
from bot.utils import logger
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram

REQUEST_COUNT = Counter('hatekadeh_requests_total', 'Total HTTP requests')
REQUEST_LATENCY = Histogram('hatekadeh_request_latency_seconds', 'Request latency')

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Hate Kadeh Admin Panel")
templates = Jinja2Templates(directory=str(BASE_DIR / "admin_panel" / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "admin_panel" / "static")), name="static")


@app.on_event("startup")
async def _on_startup():
    logger.info("Admin panel startup")


@app.on_event("shutdown")
async def _on_shutdown():
    logger.info("Admin panel shutdown")


@app.get('/health')
async def health():
    return JSONResponse({"status": "ok"})


@app.get('/metrics')
async def metrics():
    data = generate_latest()
    return HTMLResponse(content=data, media_type=CONTENT_TYPE_LATEST)

sessions = {}
login_attempts = {}


def _bot() -> Bot:
    return Bot(token=Config.BOT_TOKEN)


def _create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    sessions[token] = {
        "user_id": user_id,
        "created_at": datetime.utcnow(),
    }
    return token


def _session_is_expired(created_at: datetime) -> bool:
    return datetime.utcnow() - created_at > timedelta(seconds=Config.SESSION_TTL_SECONDS)


def _prune_login_attempts(bucket: list[datetime]) -> list[datetime]:
    cutoff = datetime.utcnow() - timedelta(seconds=Config.LOGIN_WINDOW_SECONDS)
    return [attempt for attempt in bucket if attempt >= cutoff]


def _login_is_blocked(client_ip: str) -> bool:
    attempts = login_attempts.get(client_ip, [])
    attempts = _prune_login_attempts(attempts)
    login_attempts[client_ip] = attempts
    return len(attempts) >= Config.MAX_LOGIN_ATTEMPTS


def _register_login_attempt(client_ip: str) -> None:
    attempts = login_attempts.get(client_ip, [])
    attempts.append(datetime.utcnow())
    login_attempts[client_ip] = _prune_login_attempts(attempts)


def _reset_login_attempts(client_ip: str) -> None:
    login_attempts.pop(client_ip, None)


def _require_admin(session_token: str | None) -> int | None:
    if not session_token or session_token not in sessions:
        return None
    session_data = sessions[session_token]
    if _session_is_expired(session_data["created_at"]):
        sessions.pop(session_token, None)
        return None
    return session_data["user_id"]


def _hydrate_pending(msg: PendingMessage) -> PendingMessage:
    msg.message_text = decrypt_value(msg.message_text) or ""
    msg.file_id = decrypt_value(msg.file_id)
    return msg


def _hydrate_reply(reply: Reply) -> Reply:
    reply.reply_text = decrypt_value(reply.reply_text) or ""
    reply.file_id = decrypt_value(reply.file_id)
    return reply

def get_admin_id(session_token: str = Cookie(None)) -> int:
    return _require_admin(session_token)

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    client_ip = request.client.host if request.client else "unknown"
    if _login_is_blocked(client_ip):
        return templates.TemplateResponse("login.html", {"request": request, "error": "تعداد تلاش‌های ورود زیاد است. کمی بعد دوباره امتحان کن."})

    if not username.isdigit():
        _register_login_attempt(client_ip)
        return templates.TemplateResponse("login.html", {"request": request, "error": "نام کاربری باید آی‌دی عددی باشد"})
    user_id = int(username)
    if user_id in Config.ADMIN_IDS and password == Config.PANEL_PASSWORD:
        _reset_login_attempts(client_ip)
        token = _create_session(user_id)
        resp = RedirectResponse("/dashboard", status_code=303)
        resp.set_cookie(
            "session_token",
            token,
            httponly=True,
            samesite="strict",
            secure=Config.COOKIE_SECURE,
            max_age=Config.SESSION_TTL_SECONDS,
            path="/",
        )
        return resp

    _register_login_attempt(client_ip)
    return templates.TemplateResponse("login.html", {"request": request, "error": "اطلاعات نادرست"})

@app.get("/logout")
async def logout(session_token: str = Cookie(None)):
    if session_token and session_token in sessions:
        del sessions[session_token]
    resp = RedirectResponse("/")
    resp.delete_cookie("session_token")
    return resp

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session_token: str = Cookie(None)):
    admin_id = get_admin_id(session_token)
    if not admin_id:
        return RedirectResponse("/")
    db = SessionLocal()
    try:
        total_pending = db.query(PendingMessage).filter_by(is_approved=False).count()
        total_approved = db.query(PendingMessage).filter_by(is_approved=True).count()
        total_users = db.query(PendingMessage.sender_id).distinct().count()
        total_replies = db.query(Reply).count()
        pending_replies = db.query(Reply).filter_by(is_approved=False).count()
        recent_messages = db.query(PendingMessage).order_by(PendingMessage.created_at.desc()).limit(8).all()
        recent_messages = [_hydrate_pending(msg) for msg in recent_messages]
    finally:
        db.close()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_pending": total_pending,
        "total_approved": total_approved,
        "total_users": total_users,
        "total_replies": total_replies,
        "pending_replies": pending_replies,
        "admin_id": admin_id,
        "recent_messages": recent_messages,
    })

@app.get("/stats")
async def stats(session_token: str = Cookie(None)):
    admin_id = get_admin_id(session_token)
    if not admin_id:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    db = SessionLocal()
    try:
        return {
            "total_pending": db.query(PendingMessage).filter_by(is_approved=False).count(),
            "total_approved": db.query(PendingMessage).filter_by(is_approved=True).count(),
            "total_users": db.query(PendingMessage.sender_id).distinct().count(),
            "total_replies": db.query(Reply).count(),
            "pending_replies": db.query(Reply).filter_by(is_approved=False).count(),
        }
    finally:
        db.close()

@app.get("/pending", response_class=HTMLResponse)
async def pending_messages(request: Request, session_token: str = Cookie(None)):
    admin_id = get_admin_id(session_token)
    if not admin_id:
        return RedirectResponse("/")
    def _get_pending(db):
        return db.query(PendingMessage).filter_by(is_approved=False).order_by(PendingMessage.created_at.desc()).all()
    messages = await run_db_task(_get_pending)
    messages = [_hydrate_pending(msg) for msg in messages]
    return templates.TemplateResponse("pending_messages.html", {"request": request, "messages": messages})

@app.get("/approved", response_class=HTMLResponse)
async def approved_messages(request: Request, session_token: str = Cookie(None)):
    admin_id = get_admin_id(session_token)
    if not admin_id:
        return RedirectResponse("/")
    db = SessionLocal()
    try:
        messages = db.query(PendingMessage).filter_by(is_approved=True).order_by(PendingMessage.approved_at.desc()).all()
        messages = [_hydrate_pending(msg) for msg in messages]
    finally:
        db.close()
    return templates.TemplateResponse("approved_messages.html", {"request": request, "messages": messages})

@app.get("/message/{msg_id}", response_class=HTMLResponse)
async def message_detail(request: Request, msg_id: int, session_token: str = Cookie(None)):
    admin_id = get_admin_id(session_token)
    if not admin_id:
        return RedirectResponse("/")
    db = SessionLocal()
    try:
        msg = db.query(PendingMessage).filter_by(id=msg_id).first()
        if msg:
            msg = _hydrate_pending(msg)
    finally:
        db.close()
    if not msg:
        return HTMLResponse("پیام پیدا نشد", status_code=404)
    return templates.TemplateResponse("message_detail.html", {"request": request, "msg": msg})


@app.get("/reply/{reply_id}", response_class=HTMLResponse)
async def reply_detail(request: Request, reply_id: int, session_token: str = Cookie(None)):
    admin_id = get_admin_id(session_token)
    if not admin_id:
        return RedirectResponse("/")
    db = SessionLocal()
    try:
        reply = db.query(Reply).filter_by(id=reply_id).first()
        if reply:
            reply = _hydrate_reply(reply)
    finally:
        db.close()
    if not reply:
        return HTMLResponse("پاسخ پیدا نشد", status_code=404)
    return HTMLResponse(
        f"<h3>Reply #{reply.id}</h3><p>{reply.reply_text}</p><p>Channel message: {reply.channel_msg_id}</p>",
        status_code=200,
    )


@app.post("/approve/{msg_id}")
async def approve_message(msg_id: int, session_token: str = Cookie(None)):
    admin_id = get_admin_id(session_token)
    if not admin_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    db = SessionLocal()
    try:
        def _get_msg(db):
            return db.query(PendingMessage).filter_by(id=msg_id).first()
        msg = await run_db_task(_get_msg)
        if not msg:
            return JSONResponse({"error": "not_found"}, status_code=404)
        if not msg.is_approved:
            msg = _hydrate_pending(msg)
            channel_message_id = await send_to_channel(msg, _bot())
            if channel_message_id:
                def _mark_approved(db):
                    db.query(PendingMessage).filter_by(id=msg_id).update({
                        "is_approved": True,
                        "approved_by": admin_id,
                        "approved_at": now_tehran(),
                        "channel_message_id": channel_message_id,
                    })
                    db.commit()
                await run_db_task(_mark_approved)
            else:
                return JSONResponse({"error": "channel_send_failed"}, status_code=500)
    finally:
        db.close()
    return {"status": "ok"}

@app.post("/reject/{msg_id}")
async def reject_message(msg_id: int, session_token: str = Cookie(None)):
    admin_id = get_admin_id(session_token)
    if not admin_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    db = SessionLocal()
    try:
        msg = db.query(PendingMessage).filter_by(id=msg_id).first()
        if msg and not msg.is_approved:
            db.delete(msg)
            db.commit()
    finally:
        db.close()
    return {"status": "ok"}

@app.get("/replies", response_class=HTMLResponse)
async def replies_list(request: Request, session_token: str = Cookie(None)):
    admin_id = get_admin_id(session_token)
    if not admin_id:
        return RedirectResponse("/")
    def _get_replies(db):
        return db.query(Reply).order_by(Reply.created_at.desc()).all()
    replies = await run_db_task(_get_replies)
    replies = [_hydrate_reply(reply) for reply in replies]
    return templates.TemplateResponse("replies.html", {"request": request, "replies": replies})


@app.post("/reply/approve/{reply_id}")
async def approve_reply(reply_id: int, session_token: str = Cookie(None)):
    admin_id = get_admin_id(session_token)
    if not admin_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = SessionLocal()
    try:
        def _get_reply(db):
            return db.query(Reply).filter_by(id=reply_id).first()
        reply = await run_db_task(_get_reply)
        if not reply:
            return JSONResponse({"error": "not_found"}, status_code=404)
        if reply.is_approved:
            return {"status": "ok"}

        reply = _hydrate_reply(reply)
        sent_message_id = await send_reply_to_channel(reply, _bot())
        if not sent_message_id:
            return JSONResponse({"error": "channel_send_failed"}, status_code=500)

        def _mark_reply(db):
            db.query(Reply).filter_by(id=reply_id).update({
                "is_approved": True,
                "approved_by": admin_id,
                "approved_at": now_tehran(),
                "bot_reply_msg_id": sent_message_id,
            })
            db.commit()
        await run_db_task(_mark_reply)
    finally:
        db.close()
    return {"status": "ok"}


@app.post("/reply/reject/{reply_id}")
async def reject_reply(reply_id: int, session_token: str = Cookie(None)):
    admin_id = get_admin_id(session_token)
    if not admin_id:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    db = SessionLocal()
    try:
        reply = db.query(Reply).filter_by(id=reply_id).first()
        if reply and not reply.is_approved:
            db.delete(reply)
            db.commit()
    finally:
        db.close()
    return {"status": "ok"}