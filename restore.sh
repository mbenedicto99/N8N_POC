#!/usr/bin/env bash
set -euo pipefail

FILE="$1"
if [[ -z "${FILE}" ]]; then
  echo "Uso: $0 backups/n8n_pg_YYYYmmdd_HHMMSS.sql.gz"; exit 1; fi

echo "[n8n] Restaurando '${FILE}'..."
gunzip -c "${FILE}" | docker compose exec -T postgres psql -U ${POSTGRES_USER:-n8n} -d ${POSTGRES_DB:-n8ndb}

echo "[n8n] Restore concluído."
