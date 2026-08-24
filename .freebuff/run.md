# Run Doc — Hate Kadeh Admin Panel Preview

## How to Reproduce Artifacts

1. Copy `.env` from the main checkout (the workspace IS the main checkout — no copy needed).
2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

## How to Run the Server

Start uvicorn serving the FastAPI admin panel:

```
python -m uvicorn admin_panel.main:app --host 0.0.0.0 --port 8000
```

- **Port:** 8000 (default, free)
- **URL:** http://localhost:8000
- **Login:** Use an admin user ID from `ADMIN_IDS` in `.env` and the `PANEL_PASSWORD`
