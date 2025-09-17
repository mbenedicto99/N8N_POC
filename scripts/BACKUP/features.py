
import pandas as pd

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Ensure datetime
    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["end"]   = pd.to_datetime(df["end"], errors="coerce")
    df["dow"] = df["start"].dt.dayofweek
    df["hour"] = df["start"].dt.hour
    df["dom"] = df["start"].dt.day
    df["week"] = df["start"].dt.isocalendar().week.astype("Int64")
    df["is_weekend"] = df["dow"].isin([5,6]).astype(int)

    # Frequencies
    for col in ["project","job_name","node","folder","sub_application"]:
        if col in df.columns:
            freq = df[col].value_counts(normalize=True)
            df[f"freq_{col if col!='sub_application' else 'sub_app'}"] = df[col].map(freq).fillna(0.0)

    # Rolling durations by job
    df["job_project"] = df["project"].astype(str) + "::" + df["job_name"].astype(str)
    df = df.sort_values(["job_project","start"])
    df["dur_roll_mean_7"]   = df.groupby("job_project")["duration_sec"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    df["dur_roll_median_7"] = df.groupby("job_project")["duration_sec"].transform(lambda s: s.rolling(7, min_periods=1).median())

    df["status_ok"] = (df["status"]=="succeeded").astype(int)
    # Missing 'retries' default to 0 if not present
    if "retries" not in df.columns:
        df["retries"] = 0
    return df

if __name__ == "__main__":
    import os
    import pandas as pd
    p = os.path.join(os.path.dirname(__file__), "..", "data","dados_rundeck.csv")
    df = pd.read_csv(p, parse_dates=["start","end"])
    print(add_features(df).head().to_string())
