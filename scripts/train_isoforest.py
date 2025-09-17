import os, json, numpy as np, pandas as pd
from sklearn.ensemble import IsolationForest

FEATS = ["duration_sec","retries","dow","hour","dom","is_weekend",
         "freq_project","freq_job_name","freq_node","freq_folder","freq_sub_app",
         "dur_roll_mean_7","dur_roll_median_7"]

def fit_iforest(df: pd.DataFrame, contamination=0.03, random_state=42):
    X = df[FEATS].astype(float).fillna(0.0).values
    model = IsolationForest(contamination=contamination, random_state=random_state)
    model.fit(X)
    scores = -model.score_samples(X)
    return model, scores

def save_model(model, path):
    import joblib, os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(model, path)

if __name__ == "__main__":
    from etl import load_and_normalize, save_normalized, INPUT_GLOB
    from features import add_features

    base = os.path.join(os.path.dirname(__file__), "..")
    csv_norm = os.path.join(base, "data", "dados_rundeck.csv")
    if not os.path.exists(csv_norm):
        df = load_and_normalize(os.path.join(base, INPUT_GLOB))
        save_normalized(df, csv_norm)
    df = pd.read_csv(csv_norm, parse_dates=["start_time","end_time"])
    df = add_features(df)

    contamination = float(os.environ.get("IFOREST_CONTAMINATION","0.03"))
    model, scores = fit_iforest(df, contamination=contamination)
    df["iforest_score"] = scores
    out_scored = os.path.join(base, "data", "dados_rundeck_scored.csv")
    df.to_csv(out_scored, index=False)

    model_path = os.path.join(base, "data", "iforest_model.joblib")
    save_model(model, model_path)
    print(f"OK: modelo salvo em {model_path} e scores em {out_scored}")
