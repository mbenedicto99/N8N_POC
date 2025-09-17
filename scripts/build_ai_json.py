#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consolida saídas do pipeline e gera ./app/app/ai_analysis.json (same-origin).
Lê:
  - stage/execucoes.parquet  (campos: projeto, job, exec_id, inicio, status, duracao_s, ...)
  - stage/score.parquet      (campo: re = erro de reconstrução por execução)
Escreve:
  - app/app/ai_analysis.json
Uso:
  python scripts/build_ai_json.py [--out app/app/ai_analysis.json]
"""
import os
import sys
import json
import argparse
from pathlib import Path
import numpy as np

def _fail(msg: str, code: int = 2):
    sys.stderr.write((msg or "").strip() + "\n")
    sys.exit(code)

try:
    import pandas as pd
except Exception as e:
    _fail("Dependências ausentes. Ative a venv e instale pandas/numpy/pyarrow. Detalhe: %s" % e)

STAGE_DIR = os.environ.get("STAGE_DIR", "stage")
DEFAULT_OUT = os.environ.get("AI_JSON_OUT", "app/app/ai_analysis.json")

def _p95(arr):
    arr = np.asarray(arr, dtype=float)
    if arr.size == 0:
        return float("nan")
    return float(np.percentile(arr, 95))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT, help="caminho de saída do JSON (default: %(default)s)")
    args = ap.parse_args()
    out_path = Path(args.out)

    execs_pq = Path(STAGE_DIR) / "execucoes.parquet"
    score_pq = Path(STAGE_DIR) / "score.parquet"

    if not execs_pq.exists():
        _fail(f"Arquivo não encontrado: {execs_pq}")
    if not score_pq.exists():
        _fail(f"Arquivo não encontrado: {score_pq}")

    # ---- Carregar dados ----
    df_exec = pd.read_parquet(execs_pq)
    df_score = pd.read_parquet(score_pq)

    # Normaliza colunas mínimas
    for col in ["projeto","job","exec_id","inicio","status"]:
        if col not in df_exec.columns:
            df_exec[col] = None
    if "duracao_s" not in df_exec.columns:
        _fail("Coluna obrigatória ausente: duracao_s")
    if "re" not in df_score.columns:
        _fail("Coluna obrigatória ausente em score.parquet: re")

    # Garante tipos
    df_exec["duracao_s"] = pd.to_numeric(df_exec["duracao_s"], errors="coerce")
    df_exec["status"] = df_exec["status"].astype(str).str.upper().str.strip()
    df = pd.concat([df_exec.reset_index(drop=True), df_score.reset_index(drop=True)], axis=1)

    # Limpa nulos essenciais
    df = df.dropna(subset=["job","duracao_s","re"]).copy()
    if df.empty:
        _fail("Após limpeza, não há linhas válidas para consolidar.")

    # Marcas auxiliares
    # p95 de duração por job
    p95_job = df.groupby("job", dropna=False)["duracao_s"].quantile(0.95).rename("p95_job")
    df = df.join(p95_job, on="job")
    df["alto_tempo"] = df["duracao_s"] > df["p95_job"]
    df["falhou"] = df["status"].ne("SUCCESS")

    # Eventos cruzados: falha & alto tempo
    eventos_cruz = df.loc[df["alto_tempo"] & df["falhou"]].copy()

    # ---- Hotspots (por projeto, job) ----
    agg = eventos_cruz.groupby(["projeto","job"], dropna=False).agg(
        eventos=("job","count"),
        risco_medio=("re","mean"),
        risco_p95=("re", _p95),
        duracao_media_s=("duracao_s","mean"),
    ).reset_index().sort_values(["eventos","risco_p95","risco_medio"], ascending=[False,False,False])
    # Limpeza numérica
    for c in ["eventos","risco_medio","risco_p95","duracao_media_s"]:
        if c in agg.columns:
            agg[c] = pd.to_numeric(agg[c], errors="coerce")
    agg = agg.replace([np.inf, -np.inf], np.nan).fillna({ "eventos": 0, "risco_medio": 0.0, "risco_p95": 0.0, "duracao_media_s": 0.0 })
    hotspots = agg.head(50).to_dict(orient="records")

    # ---- Risco p95 por job ----
    risco_job = df.groupby("job", dropna=False).agg(
        p95=("duracao_s", _p95),
        duracao_media=("duracao_s","mean")
    ).reset_index().sort_values("p95", ascending=False)
    for c in ["p95","duracao_media"]:
        risco_job[c] = pd.to_numeric(risco_job[c], errors="coerce").replace([np.inf,-np.inf], np.nan).fillna(0.0)
    risco_p95_por_job = risco_job.to_dict(orient="records")

    # ---- Top amostras por RE ----
    keep_cols = ["projeto","job","exec_id","inicio","status","duracao_s","re"]
    for k in keep_cols:
        if k not in df.columns:
            df[k] = None
    top = (df.sort_values("re", ascending=False)
             .loc[:, keep_cols]
             .head(50)
             .rename(columns={"re":"risco"}))
    # Converte tipos seguros
    top["duracao_s"] = pd.to_numeric(top["duracao_s"], errors="coerce").fillna(0.0)
    top["risco"] = pd.to_numeric(top["risco"], errors="coerce").fillna(0.0)
    top_amostras = top.to_dict(orient="records")

    # ---- Resumo ----
    total = int(len(df))
    falhas = int(df["falhou"].sum())
    alto = int(df["alto_tempo"].sum())
    cruz = int(len(eventos_cruz))
    taxa = round(cruz / max(1, total), 3)

    # phi e lift (proxies simples)
    p_falha = df["falhou"].mean() if total else 0.0
    p_alto = df["alto_tempo"].mean() if total else 0.0
    p_conj = (df["falhou"] & df["alto_tempo"]).mean() if total else 0.0

    phi = round(float(p_falha * p_alto), 3)  # proxy intuitivo
    lift = round(float(p_conj / max(p_falha, 1e-6)), 2) if p_falha > 0 else 0.0

    resumo = {
        "registros": total,
        "falhas": falhas,
        "alto_tempo": alto,
        "eventos_cruzados": cruz,
        "taxa_cruzada": taxa,
        "phi": phi,
        "lift": lift,
    }

    out = {
        "meta": { "modelo": "BernoulliRBM", "periodo": "último trimestre" },
        "resumo": resumo,
        "hotspots": hotspots,
        "risco_p95_por_job": risco_p95_por_job,
        "top_amostras": top_amostras,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "status": "ok",
        "out": str(out_path),
        "resumo": resumo,
        "counts": {
            "hotspots": len(hotspots),
            "risco_p95_por_job": len(risco_p95_por_job),
            "top_amostras": len(top_amostras)
        }
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
