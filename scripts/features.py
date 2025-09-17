import os
import json
import numpy as np
import pandas as pd

INPUT_CSV = os.getenv("INPUT_CSV_CLEAN", "data/clean.csv")
OUTPUT_CSV = os.getenv("OUTPUT_CSV_FEATS", "data/features.csv")
FEATURE_META = os.getenv("FEATURE_META", "models/feature_meta.json")

Z_THRESHOLD = float(os.getenv("Z_THRESHOLD", "2.0"))

def main():
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Arquivo não encontrado: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV, parse_dates=["start_time","end_time"])

    df["_dur_mean"] = df.groupby("job_name")["duration_sec"].transform("mean")
    df["_dur_std"]  = df.groupby("job_name")["duration_sec"].transform("std").replace(0, np.nan)
    df["_dur_std"]  = df["_dur_std"].fillna(df["_dur_std"].median() or 1.0)
    df["duration_z"] = (df["duration_sec"] - df["_dur_mean"]) / df["_dur_std"]

    df["failed"] = (df["status"].str.lower() == "failed").astype(int)
    df["high_runtime"] = (df["duration_z"] > Z_THRESHOLD).astype(int)

    df["hour_sin"] = np.sin(2*np.pi*df["hour"]/24.0)
    df["hour_cos"] = np.cos(2*np.pi*df["hour"]/24.0)
    df["wday_sin"] = np.sin(2*np.pi*df["weekday"]/7.0)
    df["wday_cos"] = np.cos(2*np.pi*df["weekday"]/7.0)

    num_cols = ["duration_sec", "duration_z", "hour_sin", "hour_cos", "wday_sin", "wday_cos"]
    df["duration_z_clipped"] = df["duration_z"].clip(-5,5)
    num_cols = ["duration_sec", "duration_z_clipped", "hour_sin", "hour_cos", "wday_sin", "wday_cos"]

    meta = {}
    for c in num_cols:
        vmin, vmax = float(df[c].min()), float(df[c].max())
        if vmax - vmin == 0:
            vmax = vmin + 1e-6
        meta[c] = {"min": vmin, "max": vmax}
        df[c+"_mm"] = (df[c]-vmin)/(vmax-vmin)

    feat_cols = [c+"_mm" for c in num_cols] + ["failed","high_runtime"]
    feature_meta = {
        "z_threshold": Z_THRESHOLD,
        "continuous_cols": num_cols,
        "binary_cols": ["failed","high_runtime"],
        "feature_cols": feat_cols,
        "minmax": meta,
        "id_cols": ["job_id","job_name","project","start_time","end_time","status","duration_sec","duration_z","date"]
    }

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    os.makedirs(os.path.dirname(FEATURE_META), exist_ok=True)

    df_out = df[feature_meta["id_cols"] + feat_cols].copy()
    df_out.to_csv(OUTPUT_CSV, index=False)
    with open(FEATURE_META, "w") as f:
        json.dump(feature_meta, f, indent=2)
    print(f"[features] Gravado {OUTPUT_CSV} e {FEATURE_META}")

if __name__ == "__main__":
    main()
