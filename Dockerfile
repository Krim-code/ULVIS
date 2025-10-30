FROM python:3.12-slim

WORKDIR /app

# системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential libpq-dev netcat-traditional postgresql-client  && \
    rm -rf /var/lib/apt/lists/*

# зависимости проекта
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# копим всё приложение
COPY . /app

# переменные окружения
ENV PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=furniture_site.settings
    
EXPOSE 8000
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
