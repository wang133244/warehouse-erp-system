#!/bin/sh
set -e
cd /repo/backend
python -m alembic upgrade head
cd /repo
exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
