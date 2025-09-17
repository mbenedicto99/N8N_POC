import os
import pandas as pd
from dateutil import parser

INPUT_CSV = os.getenv("INPUT_CSV", "data/dados_rundeck.csv")
OUTPUT_CSV = os.getenv("OUTPUT_CSV", "data/clean.csv")

def parse_dt(x):
    if pd.isna(x):
        return pd.NaT
    try:
        return parser.parse(str(x))
    except Exception:
        return pd.NaT

def main():
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Arquivo não encontrado: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)
    df.columns = [c.strip().lower() for c in df.columns]

    colmap = {
        "job_id": ["job_id", "id", "execution_id"],
        "job_name": ["job_name", "name", "job"],
        "project": ["project", "project_name"],
        "status": ["status", "result", "state"],
        "start_time": ["start_time", "started_at", "start"],
        "end_time": ["end_time", "ended_at", "end", "finish_time"],
    }

    def pick(df, keys):
        for k in keys:
            if k in df.columns:
                return df[k]
        return pd.Series([None]*len(df))

    out = pd.DataFrame()
    for k, aliases in colmap.items():
        out[k] = pick(df, aliases)

    out["start_time"] = out["start_time"].apply(parse_dt)
    out["end_time"] = out["end_time"].apply(parse_dt)
    out["duration_sec"] = (out["end_time"] - out["start_time"]).dt.total_seconds()
    out["status"] = out["status"].astype(str).str.lower().str.strip()
    out["status"] = out["status"].replace({
        "succeeded": "success", "ok": "success", "successful": "success",
        "fail": "failed", "error": "failed", "ko": "failed"
    })
    out = out.dropna(subset=["start_time"])
    out["duration_sec"] = out["duration_sec"].fillna(0).clip(lower=0)

    out["date"] = out["start_time"].dt.date
    out["hour"] = out["start_time"].dt.hour
    out["weekday"] = out["start_time"].dt.weekday
    out["job_name"] = out["job_name"].fillna("UNKNOWN")
    out["project"] = out["project"].fillna("UNKNOWN")

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    out.to_csv(OUTPUT_CSV, index=False)
    print(f"[etl] Gravado {OUTPUT_CSV} com {len(out)} linhas.")

if __name__ == "__main__":
    main()
