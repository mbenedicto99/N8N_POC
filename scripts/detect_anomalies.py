import os, json, numpy as np, pandas as pd
from pathlib import Path
from features import add_features

def _p90_per_job(d):
    # P90 por job; se grupo for pequeno ou NaN, será tratado depois
    return d.quantile(0.90)

def _insights(row):
    tips = []
    tips.append(f"Duração {int(row['duration_sec'])}s >= limiar P90 do job ({int(row['thr_long'])}s)")
    if row.get("dur_roll_mean_7"):
        try:
            if float(row['duration_sec']) >= 2.0 * float(row['dur_roll_mean_7']):
                tips.append("≥ 2x a média móvel (7) do job")
        except Exception:
            pass
    if str(row.get("status","")).lower() == "timedout":
        tips.append("Timeout de execução")
    tips.append("Falha priorizada: status != succeeded")
    return tips

if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1]
    csv_norm = base / "data" / "dados_rundeck.csv"
    if not csv_norm.exists():
        raise SystemExit("Arquivo normalizado não encontrado. Rode etl.py primeiro.")

    # Carrega e enriquece
    df = pd.read_csv(csv_norm, parse_dates=["start","end"])
    df = add_features(df)

    # Marca falhas
    df["failed"] = df["status"].str.lower().ne("succeeded")

    # Limiar de 'longo': P90 por job (fallback: P90 global se grupo pequeno < 8 pontos)
    size_by_job = df.groupby("job_project")["duration_sec"].transform("size")
    p90_by_job  = df.groupby("job_project")["duration_sec"].transform(_p90_per_job)
    p90_global  = df["duration_sec"].quantile(0.90)
    df["thr_long"] = np.where(size_by_job >= 8, p90_by_job, p90_global)

    # Máscara final: scripts longos E falhados
    long_mask = df["duration_sec"] >= df["thr_long"]
    mask = df["failed"] & long_mask

    anomalies = df.loc[mask].copy()

    # Insights específicos
    anomalies["insights"] = anomalies.apply(_insights, axis=1)

    # Ordenação: mais longos e mais recentes primeiro
    anomalies = anomalies.sort_values(["duration_sec","end"], ascending=[False, False])

    # Serialização
    out_json = base / "app" / "anomalies.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    records = []
    keep = ["start","end","project","job_name","node","folder","sub_application","status",
            "duration_sec","dur_roll_mean_7","thr_long"]
    for _, r in anomalies.iterrows():
        rec = {k: (r[k].isoformat() if k in ("start","end") and not pd.isna(r[k]) else (None if pd.isna(r.get(k)) else r.get(k))) for k in keep}
        # Converte numericos
        for k in ["duration_sec","dur_roll_mean_7","thr_long"]:
            if rec[k] is not None:
                try: rec[k] = float(rec[k])
                except Exception: pass
        rec["insights"] = list(r.get("insights", []))
        records.append(rec)

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"OK: {len(records)} anomalias (falha + 'longo') -> {out_json}")
