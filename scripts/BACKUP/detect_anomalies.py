import os, json, numpy as np, pandas as pd

FEATS = ["duration_sec","retries","dow","hour","dom","is_weekend",
         "freq_project","freq_job_name","freq_node","freq_folder","freq_sub_app",
         "dur_roll_mean_7","dur_roll_median_7"]

def _z(x: pd.Series):
    mu = np.nanmean(x); sd = np.nanstd(x)
    if not np.isfinite(sd) or sd == 0: sd = 1.0
    return (x - mu) / sd

def _heuristic_insights(row, z_job: float, z_glb: float) -> list:
    hints = []
    if str(row.get("status","")).lower() != "succeeded":
        hints.append("Falha explícita no status do job")
    if z_job >= 3:
        hints.append("Duração anormal para este job (Z-score por job ≥ 3)")
    if z_glb >= 3:
        hints.append("Duração extrema no contexto global (Z-score global ≥ 3)")
    if (row.get("freq_node",0) or 0) < 0.02:
        hints.append("Host raro/pouco frequente para este job")
    if row.get("hour",0) in (1,2,3,4) and row.get("status","")!="succeeded":
        hints.append("Falha em horário de janela noturna (1h–4h)")
    if row.get("dur_roll_mean_7",0) and row.get("duration_sec",0) > 2.5*row.get("dur_roll_mean_7",0):
        hints.append("Duração > 2.5x da média móvel de 7 execuções")
    return hints or ["Comportamento atípico detectado pelo modelo"]

def detect_zscore(df: pd.DataFrame, threshold=3.0) -> pd.Series:
    z_job = df.groupby("job_project")["duration_sec"].transform(_z).abs()
    z_glb = _z(df["duration_sec"]).abs()
    mask = (np.maximum(z_job, z_glb) >= threshold) | (df["status"]!="succeeded")
    return mask, z_job, z_glb

def load_model(path):
    import joblib, os
    if os.path.exists(path):
        return joblib.load(path)
    return None

def predict_iforest(model, df: pd.DataFrame) -> np.ndarray:
    X = df[FEATS].astype(float).fillna(0.0).values
    return -model.score_samples(X)

def run_detection(base_dir: str, top_n=500):
    from features import add_features
    csv = os.path.join(base_dir, "data", "dados_rundeck.csv")
    if not os.path.exists(csv):
        from etl import load_and_normalize, save_normalized, INPUT_GLOB
        df = load_and_normalize(os.path.join(base_dir, INPUT_GLOB))
        save_normalized(df, csv)

    df = pd.read_csv(csv, parse_dates=["start_time","end_time"])
    df = add_features(df)

    threshold = float(os.environ.get("ANOMALY_THRESHOLD","3.0"))
    z_mask, z_job, z_glb = detect_zscore(df, threshold=threshold)

    model = load_model(os.path.join(base_dir, "data", "iforest_model.joblib"))
    if model is not None:
        scores = predict_iforest(model, df)
        q = float(os.environ.get("IFOREST_QUANTILE","0.97"))
        if_mask = scores >= np.quantile(scores, q)
        final_mask = z_mask | if_mask
        df["iforest_score"] = scores
    else:
        final_mask = z_mask
        df["iforest_score"] = np.nan

    out = []
    anom = df[final_mask].copy()
    anom["z_job"] = z_job[final_mask].values
    anom["z_glb"] = z_glb[final_mask].values

    anom = anom.sort_values(["start_time","duration_sec"], ascending=[False, False]).head(top_n)
    for _, r in anom.iterrows():
        insights = _heuristic_insights(r, float(r.get("z_job",0) or 0), float(r.get("z_glb",0) or 0))
        out.append({
            "execution_id": int(r.get("execution_id",0)) if pd.notna(r.get("execution_id",0)) else 0,
            "ts": r["start_time"].isoformat() if not pd.isna(r["start_time"]) else "",
            "project": str(r.get("project","")),
            "job_name": str(r.get("job_name","")),
            "status": str(r.get("status","")),
            "duration_sec": int(r.get("duration_sec",0)) if pd.notna(r.get("duration_sec",0)) else 0,
            "node": str(r.get("node","")),
            "folder": str(r.get("folder","")),
            "sub_app": str(r.get("sub_app","")),
            "z_job": round(float(r.get("z_job",0) or 0),2),
            "z_glb": round(float(r.get("z_glb",0) or 0),2),
            "iforest_score": (float(r.get("iforest_score")) if pd.notna(r.get("iforest_score")) else None),
            "insights": insights
        })

    app_out  = os.path.join(base_dir, "app",  "anomalies.json")
    data_out = os.path.join(base_dir, "data", "anomalies.json")
    os.makedirs(os.path.dirname(app_out), exist_ok=True)
    with open(app_out,"w",encoding="utf-8") as f: json.dump(out, f, indent=2, ensure_ascii=False)
    with open(data_out,"w",encoding="utf-8") as f: json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"OK: {len(out)} anomalias com insights gravadas em app/ e data/.")

if __name__ == "__main__":
    run_detection(os.path.join(os.path.dirname(__file__), ".."))
