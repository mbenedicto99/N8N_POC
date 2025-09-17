#!/usr/bin/env bash
set -eo pipefail

# 0) venv (Ubuntu 24)
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip setuptools wheel
  .venv/bin/pip install -r requirements.txt
fi
source .venv/bin/activate

# 1) caminhos
RAW="data/raw"
STAGE="stage"
APPJSON="app/app/ai_analysis.json"

mkdir -p "$RAW" "$STAGE" "app/app"

# 2) validação rápida de CSVs novos
echo "[check] validando CSVs em $RAW"
python - <<'PY'
import os,sys,csv,glob
req = {"projeto","job","exec_id","inicio","status","duracao_s"}
ok=True
for f in glob.glob("data/raw/*.csv"):
    with open(f, newline='', encoding='utf-8') as fh:
        r=csv.DictReader(fh)
        miss=req-set(r.fieldnames or [])
        if miss:
            ok=False; print(f"[ERRO] {f} faltam colunas: {sorted(miss)}")
        else:
            print(f"[ok] {f}")
if not ok: sys.exit(2)
PY

# 3) ETL → features → RBM → JSON
echo "[run] ETL"
python scripts/etl.py

echo "[run] features"
python scripts/features.py

echo "[run] RBM score"
python scripts/train_rbm.py

echo "[run] Geração do ai_analysis.json"
python scripts/build_ai_json.py  # deve escrever em app/app/ai_analysis.json

# 4) sanity check do JSON
python - <<'PY'
import json,sys
j=json.load(open("app/app/ai_analysis.json"))
assert "resumo" in j and "hotspots" in j, "JSON incompleto"
print("[ok] ai_analysis.json pronto")
PY

echo "[done] JSON em $APPJSON"
