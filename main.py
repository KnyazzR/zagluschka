import os
import json
import asyncio
import secrets
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

app = FastAPI(title="Zigluchka Auth")

# Глобальный словарь для хранения пользователей (ключ: id, значение: location)
USERS_MAP = {}

def load_users():
    global USERS_MAP
    users_env = os.getenv("USERS", "{}")
    try:
        parsed = json.loads(users_env)
        # Приводим все ключи к нижнему регистру для регистронезависимого поиска
        USERS_MAP = {str(k).strip().lower(): v for k, v in parsed.items()}
        print(f"✅ Загружено {len(USERS_MAP)} пользователей из переменной USERS")
    except json.JSONDecodeError:
        print("❌ Ошибка парсинга USERS. Убедитесь, что это валидный JSON-объект.")
        USERS_MAP = {}

# Загружаем при старте
load_users()

# Раздаем фронтенд
FRONTEND_DIR = Path(__file__).parent / "frontend"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    file_path = FRONTEND_DIR / "index.html"
    if file_path.exists():
        return FileResponse(file_path)
    return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)

@app.post("/api/check")
async def check_user(request: Request):
    try:
        body = await request.json()
        user_input = body.get("input", "")
    except Exception:
        raise HTTPException(status_code=400, detail="Неверный формат запроса")

    if not isinstance(user_input, str):
        raise HTTPException(status_code=400, detail="Неверный формат запроса")

    normalized_input = user_input.strip().lower()

    # 🔒 Защита от timing-атак: искусственная задержка
    await asyncio.sleep(0.05)
    
    location = None
    for stored_id, loc in USERS_MAP.items():
        # 🔧 ИСПРАВЛЕНИЕ: кодируем строки в UTF-8 байты перед сравнением.
        # Это полностью решает проблему с русскими символами (кириллицей).
        if secrets.compare_digest(stored_id.encode('utf-8'), normalized_input.encode('utf-8')):
            location = loc
            break

    if location:
        return {"redirect": location}
    
    # Универсальный ответ для безопасности
    raise HTTPException(status_code=401, detail="Доступ запрещён")

@app.post("/api/reload")
async def reload_users():
    """Горячая перезагрузка списка без рестарта контейнера."""
    load_users()
    return {"ok": True, "count": len(USERS_MAP)}