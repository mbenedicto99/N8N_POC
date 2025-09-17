#!/usr/bin/env python3
import os, random
import numpy as np, pandas as pd
from datetime import datetime, timedelta

np.random.seed(42); random.seed(42)

N_DAYS = int(os.environ.get("SIM_DAYS","60"))
JOBS = [("backup-db","infra"),("etl-billing","finance"),("load-kpis","bi"),
        ("rotate-logs","infra"),("sync-catalog","retail"),("recalc-limits","cards"),
        ("replicate-olap","bi"),("agg-clicks","marketing")]
NODES=["node-a","node-b","node-c"]; base_date = datetime.now()-timedelta(days=N_DAYS)

def base(job): return {"backup-db":180,"etl-billing":600,"load-kpis":240,"rotate-logs":120,"sync-catalog":300,"recalc-limits":420,"replicate-olap":360,"agg-clicks":200}.get(job,300)

rows=[]; eid=100000
for d in range(N_DAYS):
  day=base_date+timedelta(days=d)
  week=1+0.2*np.sin(2*np.pi*(d/7)); month=1+(0.3 if day.day in (1,2,30) else 0)
  for job,proj in JOBS:
    for hour in (2,10,18):
      start=day.replace(hour=hour, minute=int(np.random.randint(0,59)), second=0, microsecond=0)
      dur=max(30, base(job)*week*month + np.random.normal(0, base(job)*0.1))
      if np.random.rand()<0.03:
        dur*=np.random.uniform(1.8,3.2); status="timedout" if np.random.rand()<0.5 else "failed"; err="Timeout" if status=="timedout" else "Exit code 137"
      else:
        status="succeeded" if np.random.rand()>0.05 else "failed"; err="" if status=="succeeded" else "Non-zero exit"
      end=start+timedelta(seconds=int(dur))
      rows.append(dict(execution_id=eid, project=proj, job_name=job, sub_app="", folder="ELO-PRD", node=random.choice(NODES),
        start_time=start.isoformat(timespec="seconds"), end_time=end.isoformat(timespec="seconds"), status=status, duration_sec=int(dur),
        retries=0 if status=="succeeded" else np.random.randint(0,3)))
      eid+=1

df=pd.DataFrame(rows)
out=os.path.join(os.path.dirname(__file__),"..","data","dados_rundeck.csv")
os.makedirs(os.path.dirname(out),exist_ok=True); df.to_csv(out,index=False)
print(f"OK: {out} ({len(df)} linhas)")
