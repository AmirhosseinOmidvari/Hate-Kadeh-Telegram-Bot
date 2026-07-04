# Hate Kadeh UI

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.13" />
  <img src="https://img.shields.io/badge/FastAPI-00C7B7?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Telegram%20Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Bot" />
  <img src="https://img.shields.io/badge/Status-Ready%20for%20Deployment-22C55E?style=for-the-badge" alt="Ready for Deployment" />
</p>

<p align="center">
  <strong>A private anonymous messaging platform with a Telegram bot and a secure admin panel.</strong><br />
  Users send anonymous messages, admins review them in a modern web dashboard, and approved content is published to a Telegram channel.
</p>

---

## What It Does

Hate Kadeh UI is a full Telegram-based anonymous message workflow:

- Anonymous users send text, photo, video, document, or voice messages.
- Messages are stored in a local database until an admin approves them.
- Approved messages are posted to a Telegram channel with a reply button.
- Replies from the channel can be reviewed and approved from the admin panel.
- The admin panel includes dashboards, message detail pages, approval actions, and basic metrics.

---

## Highlights

- Clean FastAPI admin panel with Jinja templates.
- Telegram bot powered by python-telegram-bot.
- SQLite persistence for a simple local-first deployment.
- Optional proxy support for bot connectivity.
- Encrypted storage helpers for sensitive message content.
- Rate-limit and retry controls for channel delivery.
- Prometheus metrics endpoint for observability.

---

## Screenshots

> Add your own screenshots here after deployment for a polished public repo.

- Admin dashboard
- Pending message queue
- Message detail view
- Login screen

---

## Tech Stack

- Python 3.13
- FastAPI
- SQLAlchemy
- Jinja2
- python-telegram-bot
- SQLite
- Prometheus client

---

## Project Structure

```text
Hate-Kade-Ui/
├── admin_panel/
│   ├── main.py
│   ├── static/
│   └── templates/
├── bot/
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── security.py
│   ├── utils.py
│   └── handlers/
├── tests/
├── requirements.txt
├── run_bot.bat
├── run_panel.bat
└── .env.example
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/Hate-Kade-Ui.git
cd Hate-Kade-Ui
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy [.env.example](.env.example) to `.env` and fill in your values.

Required values:

- `BOT_TOKEN`: Telegram bot token
- `BOT_USERNAME`: bot username with or without `@`
- `CHANNEL_ID`: channel id or username target
- `ADMIN_IDS`: comma-separated Telegram user IDs allowed in the panel
- `PANEL_PASSWORD`: admin panel password

Optional values:

- `DATA_ENCRYPTION_KEY`: Fernet key for stronger encryption
- `PROXY_URL`: HTTP/SOCKS proxy for Telegram access
- `COOKIE_SECURE`: set to `true` behind HTTPS

### 5. Run the bot

```bash
python -m bot.main
```

or use `run_bot.bat` on Windows.

### 6. Run the admin panel

```bash
uvicorn admin_panel.main:app --reload
```

or use `run_panel.bat` on Windows.

---

## Environment Variables

| Variable | Description |
| --- | --- |
| `BOT_TOKEN` | Telegram bot token from BotFather |
| `BOT_USERNAME` | Bot username used for reply links |
| `CHANNEL_ID` | Destination channel ID |
| `ADMIN_IDS` | Comma-separated admin user IDs |
| `OWNER_ID` | Optional owner ID |
| `PANEL_PASSWORD` | Admin panel password |
| `DATA_ENCRYPTION_KEY` | Optional Fernet encryption key |
| `PROXY_URL` | Optional proxy URL |
| `SESSION_TTL_SECONDS` | Admin session lifetime |
| `LOGIN_WINDOW_SECONDS` | Login rate-limit window |
| `MAX_LOGIN_ATTEMPTS` | Maximum login attempts per window |
| `COOKIE_SECURE` | Secure cookie flag |
| `SEND_RETRIES` | Retry count for Telegram sends |
| `SEND_BACKOFF_BASE` | Backoff base for retries |
| `MAX_CONCURRENT_SENDS` | Concurrency limit for sends |
| `RATE_LIMIT` | Guidance value for send throughput |

---

## Security Notes

- Do not commit `.env` or the SQLite database.
- Rotate the bot token immediately if it was ever exposed publicly.
- Prefer a dedicated `DATA_ENCRYPTION_KEY` in production.
- Enable `COOKIE_SECURE=true` when deploying behind HTTPS.
- Keep the admin panel password strong and unique.

---

## Deployment Tips

- Use a separate production `.env` file on the server.
- Run the bot and panel as independent processes.
- Place the panel behind HTTPS and a reverse proxy.
- Back up the SQLite database before migrations or major changes.

---

## Contributing

Pull requests are welcome. Please keep changes small, testable, and aligned with the existing architecture.

---

## License

This project is licensed under the terms of the repository license.