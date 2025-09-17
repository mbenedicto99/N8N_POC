#!/usr/bin/env bash
set -euo pipefail

echo "[n8n] Subindo ambiente..."
docker compose up -d

echo "[n8n] Serviços ativos:"
docker compose ps

echo "[n8n] URL: http://localhost:${N8N_PORT:-5678}/"
