FROM python:3.11-slim

WORKDIR /app

# Устанавливаем только необходимые пакеты
RUN pip install --no-cache-dir fastapi uvicorn

# Копируем файл сервера и папку фронтенда
COPY main.py .
COPY frontend ./frontend

EXPOSE 8000

# Запускаем production-сервер uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]