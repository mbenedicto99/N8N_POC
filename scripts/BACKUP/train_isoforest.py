
import os, pandas as pd
from pathlib import Path
from features import add_features

try:
    from sklearn.ensemble import IsolationForest
    import joblib
except Exception as e:
    raise SystemExit("scikit-learn não disponível; pule este passo se necessário.")

if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1]
    csv_norm = base / "data" / "dados_rundeck.csv"
    df = pd.read_csv(csv_norm, parse_dates=["start","end"])
    df = add_features(df)
    X = df[["duration_sec","retries","dow","hour","dom","is_weekend",
            "freq_project","freq_job_name","freq_node","freq_folder","freq_sub_app",
            "dur_roll_mean_7","dur_roll_median_7"]].astype(float).fillna(0.0)

    model = IsolationForest(contamination=float(os.environ.get("IFOREST_CONTAMINATION","0.03")), random_state=42)
    model.fit(X)
    (base/"data").mkdir(exist_ok=True, parents=True)
    joblib.dump(model, base/"data"/"iforest_model.joblib")
    print("IsolationForest treinado e salvo em data/iforest_model.joblib")
