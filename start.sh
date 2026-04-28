#!/bin/bash
set -e

echo "=== Timesheet Backend Starting ==="
echo "PORT: ${PORT:-8000}"
echo "DATABASE_URL set: $([ -n "$DATABASE_URL" ] && echo YES || echo NO)"
echo "SECRET_KEY set: $([ -n "$SECRET_KEY" ] && echo YES || echo NO)"

echo "=== Running Alembic Migrations ==="
alembic upgrade head
echo "=== Migrations Complete ==="

echo "=== Seeding Default Data ==="
python -c "from app.core.seed import seed_superadmin; seed_superadmin()"
echo "=== Seeding Complete ==="

echo "=== Starting Uvicorn on port ${PORT:-8000} ==="
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
