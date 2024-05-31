# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем зависимости для postgresql
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы приложения
COPY . /app

# Устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1

# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]