import os
import json
import asyncio
import secrets
import time
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pathlib import Path

app = FastAPI(title="Zigluchka Auth")

# === Защита от брутфорса (Rate Limiting в памяти) ===
REQUESTS_LIMIT = 5      # Максимум попыток
TIME_WINDOW = 60        # В секундах (1 минута)
ip_attempts = defaultdict(list)

def check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    # Оставляем только недавние попытки
    ip_attempts[client_ip] = [t for t in ip_attempts[client_ip] if now - t < TIME_WINDOW]
    if len(ip_attempts[client_ip]) >= REQUESTS_LIMIT:
        return False
    ip_attempts[client_ip].append(now)
    return True

# === Загрузка пользователей ===
USERS_MAP = {}

def load_users():
    global USERS_MAP
    users_env = os.getenv("USERS", "{}")
    try:
        parsed = json.loads(users_env)
        USERS_MAP = {str(k).strip().lower(): v for k, v in parsed.items()}
        print(f"✅ Загружено {len(USERS_MAP)} пользователей из переменной USERS")
    except json.JSONDecodeError:
        print("❌ Ошибка парсинга USERS. Убедитесь, что это валидный JSON.")
        USERS_MAP = {}

load_users()

FRONTEND_DIR = Path(__file__).parent / "frontend"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    file_path = FRONTEND_DIR / "index.html"
    if file_path.exists():
        return FileResponse(file_path)
    return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)

# Раздаем статические файлы (CSS)
@app.get("/style.css")
async def get_css():
    return FileResponse(FRONTEND_DIR / "style.css", media_type="text/css")

@app.post("/api/check")
async def check_user(request: Request):
    # Получаем IP клиента для защиты от брутфорса
    client_ip = request.client.host
    
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Слишком много попыток. Подождите минуту.")

    try:
        body = await request.json()
        user_input = body.get("input", "")
    except Exception:
        raise HTTPException(status_code=400, detail="Неверный формат запроса")

    if not isinstance(user_input, str):
        raise HTTPException(status_code=400, detail="Неверный формат запроса")

    normalized_input = user_input.strip().lower()

    # Защита от timing-атак
    await asyncio.sleep(0.05)
    
    location = None
    for stored_id, loc in USERS_MAP.items():
        # Кодирование в UTF-8 для корректной работы с кириллицей
        if secrets.compare_digest(stored_id.encode('utf-8'), normalized_input.encode('utf-8')):
            location = loc
            break

    if location:
        # Очищаем историю попыток для этого IP при успешном входе
        ip_attempts.pop(client_ip, None)
        
        response = JSONResponse(content={"redirect": location})
        response.set_cookie(
            key="user_redirect_route",
            value=location,
            httponly=False,  # False, чтобы JS мог прочитать для авто-редиректа
            secure=False,    # ⚠️ В продакшене с HTTPS измените на True!
            samesite="lax",  
            max_age=86400    # 24 часа
        )
        return response
    
    raise HTTPException(status_code=401, detail="Неверный код доступа")

@app.post("/api/reload")
async def reload_users():
    load_users()
    return {"ok": True, "count": len(USERS_MAP)}