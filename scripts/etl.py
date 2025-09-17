
import os, glob
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

def load_and_normalize(input_glob: str) -> pd.DataFrame:
    files = sorted(glob.glob(input_glob))
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo encontrado para o padrão: {input_glob}")

    dfs = []
    for fp in files:
        # Try headered read; fallback to header=None with canonical names
        try:
            df = pd.read_csv(fp, sep=';', engine='python', dtype=str)
            cols_lower = [c.strip().lower() for c in df.columns]
            if not any('start' in c for c in cols_lower) or not any('end' in c for c in cols_lower):
                raise ValueError('missing expected columns - fallback')
        except Exception:
            names = ['Job','Application','Sub-Application','Folder','Host','Ended Status','Start Time','End Time','Creation Date']
            df = pd.read_csv(fp, sep=';', engine='python', header=None, names=names, dtype=str)

        # Cleanup
        df.columns = [c.strip() for c in df.columns]
        for c in df.columns:
            if df[c].dtype == object:
                df[c] = df[c].astype(str).str.strip()

        # Host: drop leading "name:"
        if 'Host' in df.columns:
            df['Host'] = df['Host'].str.replace(r'^name:\s*', '', regex=True).str.strip()

        # Canonical names
        rename_map = {
            'Job':'job',
            'Application':'application',
            'Sub-Application':'sub_application',
            'Folder':'folder',
            'Host':'node',
            'Ended Status':'status',
            'Start Time':'start',
            'End Time':'end',
            'Creation Date':'created_date',
        }
        df = df.rename(columns=rename_map)

        # Parse dates
        for col in ['start','end']:
            df[col] = pd.to_datetime(df[col], format='%d/%m/%y %H:%M:%S', errors='coerce')
        df['created_date'] = pd.to_datetime(df.get('created_date'), format='%d/%m/%y', errors='coerce')

        # Normalize status
        df['status'] = df['status'].str.lower().map({
            'succeed':'succeeded','success':'succeeded','ok':'succeeded',
            'fail':'failed','failed':'failed','timeout':'timedout'
        }).fillna(df['status'].str.lower())

        df['duration_sec'] = (df['end'] - df['start']).dt.total_seconds()
        df['project'] = df['folder'].fillna('UNKNOWN')
        df['job_name'] = df['job'].fillna('UNKNOWN')
        df['job_project'] = df['project'] + '::' + df['job_name']
        dfs.append(df)

    out = pd.concat(dfs, ignore_index=True)
    out = out.dropna(subset=['start','end','duration_sec'])
    out = out[out['duration_sec'] >= 0]
    (BASE / 'data').mkdir(exist_ok=True, parents=True)
    out.to_csv(BASE / 'data' / 'dados_rundeck.csv', index=False)
    return out

if __name__ == '__main__':
    INPUT_GLOB = os.getenv('INPUT_GLOB', 'data/*.csv')
    df = load_and_normalize(INPUT_GLOB)
    print('Linhas normalizadas:', len(df))
    print('Saída:', str((BASE / 'data' / 'dados_rundeck.csv')))
