#!/usr/bin/env bash
set -euo pipefail

TS=$(date +%Y%m%d_%H%M%S)
mkdir -p backups

echo "[n8n] Backup do PostgreSQL..."
docker compose exec -T postgres pg_dump -U ${POSTGRES_USER:-n8n} -d ${POSTGRES_DB:-n8ndb} | gzip > backups/n8n_pg_${TS}.sql.gz

echo "[n8n] Arquivo: backups/n8n_pg_${TS}.sql.gz"
