#!/bin/sh
set -e
# NotePlus API entrypoint — solo Docker (prod/dev).
# 1. Espera a Postgres, 2. corre migraciones, 3. ejecuta el CMD.

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

echo "Waiting for Postgres at ${DB_HOST}:${DB_PORT}..."
python3 -c "
import socket, time, sys
host = '${DB_HOST}'
port = ${DB_PORT}
for i in range(30):
    try:
        with socket.create_connection((host, port), timeout=2):
            print('Postgres is up')
            sys.exit(0)
    except OSError:
        time.sleep(1)
print('Postgres not reachable after 30s', file=sys.stderr)
sys.exit(1)
"

echo "Running migrations..."
alembic upgrade head

echo "Starting: $@"
exec "$@"
