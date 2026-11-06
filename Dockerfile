FROM python:3.11-slim

WORKDIR /app

# Копируем и устанавливаем зависимости (кэшируется Docker'ом)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY main.py .
COPY frontend ./frontend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]