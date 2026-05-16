#!/usr/bin/env bash
set -euo pipefail

# Folder where local backups will be stored temporarily.
BACKUP_DIR="/opt/ihui-backups/postgres"

# Timestamp for unique backup filenames.
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# Final backup file path.
BACKUP_FILE="${BACKUP_DIR}/ihui_postgres_${TIMESTAMP}.dump"

# Go to the app directory where docker-compose.prod.yml exists.
cd /opt/ihui

echo "Creating Postgres backup: ${BACKUP_FILE}"

# Run pg_dump inside the postgres container.
# -Fc means custom format, best for pg_restore.
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U jcj -d jcjdb -Fc \
  > "${BACKUP_FILE}"

echo "Backup created successfully."

# Keep only the latest 7 local backups.
find "${BACKUP_DIR}" -type f -name "ihui_postgres_*.dump" -mtime +7 -delete

echo "Old backups older than 7 days cleaned."
