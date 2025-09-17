import pandas as pd

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    df["end_time"]   = pd.to_datetime(df["end_time"], errors="coerce")
    df["dow"] = df["start_time"].dt.dayofweek
    df["hour"] = df["start_time"].dt.hour
    df["dom"] = df["start_time"].dt.day
    df["week"] = df["start_time"].dt.isocalendar().week.astype("Int64")
    df["is_weekend"] = df["dow"].isin([5,6]).astype(int)
    df["job_project"] = df["project"].astype(str) + "::" + df["job_name"].astype(str)
    for col in ["project","job_name","node","folder","sub_app"]:
        if col in df.columns:
            freq = df[col].value_counts(normalize=True)
            df[f"freq_{col}"] = df[col].map(freq).fillna(0.0)
    df = df.sort_values(["job_project","start_time"])
    df["dur_roll_mean_7"]   = df.groupby("job_project")["duration_sec"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    df["dur_roll_median_7"] = df.groupby("job_project")["duration_sec"].transform(lambda s: s.rolling(7, min_periods=1).median())
    df["status_ok"] = (df["status"]=="succeeded").astype(int)
    return df

if __name__ == "__main__":
    import os
    p = os.path.join("data","dados_rundeck.csv")
    print(add_features(pd.read_csv(p, parse_dates=["start_time","end_time"])).head().to_string())
