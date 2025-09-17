import os, re, hashlib
import pandas as pd
from datetime import datetime

INPUT_GLOB = os.environ.get("INPUT_GLOB", "data/*.csv")

def _parse_dt(s: str):
    if pd.isna(s) or not str(s).strip():
        return pd.NaT
    s = str(s).strip()
    try:
        if " " in s:
            return pd.to_datetime(s, format="%d/%m/%y %H:%M:%S", dayfirst=True)
        return pd.to_datetime(s, format="%d/%m/%y", dayfirst=True)
    except Exception:
        return pd.to_datetime(s, dayfirst=True, errors="coerce")

def _norm_status(s: str) -> str:
    s = (str(s or "")).strip().lower()
    if s in ("succeed","success","ok","sucesso","completed","complete"):
        return "succeeded"
    if s in ("error","erro","fail","failed","timeout","timedout"):
        return "failed" if "time" not in s else "timedout"
    return s or "unknown"

def _mk_exec_id(row) -> int:
    raw = f"{row.get('Job','')}|{row.get('Application','')}|{row.get('Start Time','')}|{row.get('End Time','')}|{row.get('Host','')}"
    import hashlib
    h = hashlib.sha1(raw.encode('utf-8', 'ignore')).hexdigest()[:12]
    return int(int(h, 16) % 10**9)

def load_and_normalize(input_glob: str) -> pd.DataFrame:
    import glob
    files = sorted(glob.glob(input_glob))
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo encontrado para INPUT_GLOB={input_glob}")
    frames = []
    for fp in files:
        df = pd.read_csv(fp, sep=";", encoding="utf-8")
        cols = {c.strip(): c.strip() for c in df.columns}
        df = df.rename(columns=cols)

        df["Start Time"] = df["Start Time"].map(_parse_dt)
        df["End Time"]   = df["End Time"].map(_parse_dt)
        df["Creation Date"] = df["Creation Date"].map(_parse_dt)
        df["Ended Status"]  = df["Ended Status"].map(_norm_status)

        df["duration_sec"] = (df["End Time"] - df["Start Time"]).dt.total_seconds().fillna(0).astype(int)
        out = pd.DataFrame({
            "execution_id": df.apply(_mk_exec_id, axis=1),
            "project": df["Application"].astype(str),
            "job_name": df["Job"].astype(str),
            "sub_app": df.get("Sub-Application", ""),
            "folder": df.get("Folder", ""),
            "node": df.get("Host", ""),
            "start_time": df["Start Time"],
            "end_time": df["End Time"],
            "status": df["Ended Status"],
            "duration_sec": df["duration_sec"],
            "retries": 0,
            "queue_depth": pd.NA,
            "cpu_pct": pd.NA,
            "mem_pct": pd.NA,
            "error_message": ""
        })
        frames.append(out)
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values("start_time", na_position="last")
    merged = merged.drop_duplicates(subset=["execution_id","start_time"], keep="last").reset_index(drop=True)
    return merged

def save_normalized(df: pd.DataFrame, out_csv: str):
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df.to_csv(out_csv, index=False)

if __name__ == "__main__":
    df = load_and_normalize(INPUT_GLOB)
    out = os.path.join("data","dados_rundeck.csv")
    save_normalized(df, out)
    print(f"OK: normalizado para {out} ({len(df)} linhas)")
