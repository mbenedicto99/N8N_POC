import os
import json
import joblib
import numpy as np
import pandas as pd

MODEL_PATH = os.getenv("MODEL_PATH", "models/rbm.joblib")
FEATURE_META = os.getenv("FEATURE_META", "models/feature_meta.json")
INPUT_FEATS = os.getenv("INPUT_FEATS", "data/features.csv")
OUTPUT_JSON = os.getenv("OUTPUT_JSON", "app/ai_analysis.json")

TOP_N = int(os.getenv("TOP_N", "20"))

def reconstruction_error(rbm, X):
    H = rbm.transform(X)
    V_recon = rbm.gibbs(H)
    err = ((X - V_recon) ** 2).mean(axis=1)
    return err, V_recon

def phi_coefficient(a, b):
    a = np.asarray(a).astype(int)
    b = np.asarray(b).astype(int)
    tp = np.sum((a==1) & (b==1))
    tn = np.sum((a==0) & (b==0))
    fp = np.sum((a==0) & (b==1))
    fn = np.sum((a==1) & (b==0))
    denom = np.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    if denom == 0:
        return 0.0
    return (tp*tn - fp*fn)/denom

def main():
    if not (os.path.exists(MODEL_PATH) and os.path.exists(INPUT_FEATS) and os.path.exists(FEATURE_META)):
        raise FileNotFoundError("Modelo/Features/Meta não encontrados.")

    rbm = joblib.load(MODEL_PATH)
    with open(FEATURE_META) as f:
        meta = json.load(f)
    feats = pd.read_csv(INPUT_FEATS, parse_dates=["start_time","end_time"])

    X = feats[meta["feature_cols"]].astype(float).values
    err, _ = reconstruction_error(rbm, X)

    e_min, e_max = float(err.min()), float(err.max())
    risk = (err - e_min)/(e_max - e_min + 1e-9)

    feats["risk_score"] = risk
    feats["failed"] = feats["failed"].astype(int)
    feats["high_runtime"] = feats["high_runtime"].astype(int)
    feats["cross_event"] = ((feats["failed"]==1) & (feats["high_runtime"]==1)).astype(int)

    phi = float(phi_coefficient(feats["failed"].values, feats["high_runtime"].values))

    total = int(len(feats))
    n_failed = int(feats["failed"].sum())
    n_high = int(feats["high_runtime"].sum())
    n_cross = int(feats["cross_event"].sum())
    cross_rate = float(n_cross / max(total,1))

    cross_df = feats[feats["cross_event"]==1].copy()
    hotspots = (
        cross_df.groupby(["project","job_name"])
        .agg(
            events=("cross_event","sum"),
            avg_risk=("risk_score","mean"),
            p95_risk=("risk_score", lambda x: float(np.percentile(x,95))),
            avg_duration=("duration_sec","mean")
        )
        .reset_index()
        .sort_values(["events","avg_risk"], ascending=[False,False])
        .head(TOP_N)
    )

    samples = (
        cross_df.sort_values("risk_score", ascending=False)
        .head(min(TOP_N, 50))
        [["project","job_name","job_id","start_time","status","duration_sec","risk_score"]]
    )
    samples["start_time"] = samples["start_time"].astype(str)

    p_fail = n_failed / max(total,1)
    p_high = n_high / max(total,1)
    p_joint = n_cross / max(total,1)
    lift = float(p_joint / max(p_fail*p_high, 1e-9))

    analysis = {
        "meta": {
            "model": "BernoulliRBM",
            "version": 1,
            "z_threshold_high_runtime": meta.get("z_threshold", 2.0),
            "feature_cols": meta.get("feature_cols", []),
        },
        "summary": {
            "total_records": total,
            "failed_count": n_failed,
            "high_runtime_count": n_high,
            "cross_events_count": n_cross,
            "cross_events_rate": round(cross_rate, 5),
            "phi_failed_high_runtime": round(phi, 5),
            "lift_failed_given_high_runtime": round(lift, 5)
        },
        "hotspots": hotspots.to_dict(orient="records"),
        "top_risk_samples": samples.to_dict(orient="records")
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"[detect_anomalies] Gravado JSON em {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
