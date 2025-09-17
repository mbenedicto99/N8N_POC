import os, json, numpy as np, pandas as pd

def load(csv_path):
    return pd.read_csv(csv_path, parse_dates=["scheduled_time","start_time","end_time"]).sort_values("start_time")

def add_features(df):
    df=df.copy(); df["dow"]=df["start_time"].dt.dayofweek; df["hour"]=df["start_time"].dt.hour
    df["is_weekend"]=df["dow"].isin([5,6]).astype(int); df["job_project"]=df["project"]+"::"+df["job_name"]; return df

def z(x): m=np.nanmean(x); s=np.nanstd(x) or 1.0; return (x-m)/s

def detect(df, threshold=3.0):
    z_job = df.groupby("job_project")["duration_sec"].transform(z).abs()
    z_glb = z(df["duration_sec"]).abs()
    return (np.maximum(z_job, z_glb) >= threshold) | (df["status"]!="succeeded")

def to_json(df, mask, top=200):
    out=[]; d=df[mask].sort_values(["start_time","duration_sec"], ascending=[False,False]).head(top)
    for _,r in d.iterrows():
        out.append(dict(execution_id=int(r["execution_id"]), ts=r["start_time"].isoformat(),
                        project=r["project"], job_name=r["job_name"], status=r["status"],
                        duration_sec=int(r["duration_sec"]), retries=int(r["retries"]),
                        cpu_pct=float(r["cpu_pct"]), mem_pct=float(r["mem_pct"]),
                        node=r["node"], error_message=(r.get("error_message") or "")[:120]))
    return out

if __name__=="__main__":
    base=os.path.join(os.path.dirname(__file__),"..")
    csv=os.path.join(base,"data","dados_rundeck.csv")
    if not os.path.exists(csv):
        from simulate_data import *  # gera se não existir
    df=add_features(load(csv))
    mask=detect(df, float(os.environ.get("ANOMALY_THRESHOLD","3.0")))
    out=to_json(df, mask)
    for p in (os.path.join(base,"app","anomalies.json"), os.path.join(base,"data","anomalies.json")):
        os.makedirs(os.path.dirname(p),exist_ok=True); open(p,"w").write(json.dumps(out,indent=2))
    print(f"OK: {len(out)} anomalias gravadas.")
