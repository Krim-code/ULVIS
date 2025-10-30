#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h db -p 5432 -U "$DB_USER" > /dev/null 2>&1; do
  sleep 0.5
done
echo "PostgreSQL is ready!"

python manage.py collectstatic --noinput
python manage.py migrate --noinput

if [ -f /app/db.json ]; then
  echo "Loading initial data..."
  # удаляем BOM на лету
  sed -i '1s/^\xEF\xBB\xBF//' /app/db.json || true
  python manage.py loaddata /app/db.json || true
fi

echo "Starting Gunicorn..."
exec gunicorn furniture_site.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
