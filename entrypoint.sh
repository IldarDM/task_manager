#!/bin/bash
set -e

echo "=== Starting entrypoint ==="
echo "Running Alembic migrations..."

if alembic upgrade head; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed"
    exit 1
fi

echo "=== Starting FastAPI ==="
echo "Command: $@"
exec "$@"