#!/bin/bash
set -e

echo "Waiting for database to be ready..."
until pg_isready -h "${DATABASE_HOST:-db}" -p "${DATABASE_PORT:-5432}" -U "${DATABASE_USER:-autonews}" > /dev/null 2>&1; do
  echo "Database is unavailable - sleeping"
  sleep 2
done

echo "Database is ready!"
echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"
