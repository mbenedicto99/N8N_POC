# N8N_POC — Análise de Falhas x Alto Tempo com RBM

Este repositório implementa uma esteira **n8n → GitHub → GitHub Actions → RBM (Restricted Boltzmann Machine) → Painel estático (Amplify)** para detectar **eventos cruzados** entre **falhas** e **alto tempo de execução** em JOBs de schedulers (ex.: Rundeck). A saída executiva é o arquivo `app/ai_analysis.json`, consumido por um **painel estático** (`app/index.html`).

> **Objetivo**: fornecer visibilidade rápida e acionável dos **hotspots** (jobs e projetos) que combinam **falha** e **runtime anormalmente alto**, priorizando correções e capacidade.

---

## Arquitetura (Mermaid)

```mermaid
flowchart LR
  %% Fontes
  A[n8n<br/>Coleta via API do Scheduler] -->|CSV append| B[data/dados_rundeck.csv]

  %% Pipeline de dados
  subgraph P[Pipeline de Dados (GitHub Actions ou local)]
    B --> C[ETL<br/>scripts/etl.py]
    C --> D[Features & Scaling<br/>scripts/features.py]
    D --> E[Treino RBM<br/>scripts/train_rbm.py]
    E --> F[Detecção & Insights<br/>scripts/detect_anomalies.py]
  end

  %% Artefatos gerados
  F --> G[[app/ai_analysis.json]]
  F --> H[(models/rbm.joblib)]
  D --> I[(data/features.csv)]

  %% Publicação
  subgraph W[Web Static Hosting]
    G --> J[App estático<br/>app/index.html + app/app.js + app/styles.css]
  end

  %% Usuário
  J --> U[Executivos & Operação<br/>KPIs, Hotspots, Amostras]

  %% DevOps
  subgraph CI[CI/CD]
    B -. push .-> P
    P -. commit .-> G
    G -. deploy .-> W
  end
```

---

## Principais componentes

- **Coleta (n8n)**: fluxo que lê execuções do scheduler (ex.: Rundeck) e realiza *append* em `data/dados_rundeck.csv`.
- **ETL (`scripts/etl.py`)**: normaliza campos, calcula `duration_sec`, trata datas e status.
- **Features (`scripts/features.py`)**: cria variáveis (sazonalidade horária/semanal, *z-score* de duração por `job_name`), normaliza em [0,1] e gera alvos binários: `failed` e `high_runtime`.
- **Treino RBM (`scripts/train_rbm.py`)**: treina uma `BernoulliRBM` sobre as features.
- **Detecção/Insights (`scripts/detect_anomalies.py`)**: calcula **erro de reconstrução** → `risk_score`; cruza `failed` & `high_runtime`; gera KPIs, **hotspots** e **amostras** em `app/ai_analysis.json`.
- **Painel (`app/index.html`)**: lê o JSON, exibe KPIs, gráficos (Chart.js) e tabelas. Mostra **badge de “Última atualização”** via `HEAD` (Last-Modified).

---

## Estrutura de pastas

```
app/
  index.html
  app.js
  styles.css
data/
  dados_rundeck.csv           # entrada (append pelo n8n)
  clean.csv                   # saída do ETL
models/
  rbm.joblib                  # modelo treinado
  feature_meta.json           # metadados de features/escala
scripts/
  etl.py
  features.py
  train_rbm.py
  detect_anomalies.py
  pipeline.py                 # orquestra a sequência
```

---

## Requisitos

- Python 3.10+ (Ubuntu 24.04 recomendado)
- Dependências Python:
  ```txt
  pandas>=2.2.0
  numpy>=1.26.0
  scikit-learn>=1.4.0
  scipy>=1.11.0
  joblib>=1.3.0
  python-dateutil>=2.9.0
  ```

- **Scheduler** (ex.: Rundeck) acessível via API.
- **n8n** operando (Docker ou SaaS) para coleta.

---

## Variáveis de ambiente (`.env.example`)

Crie um `.env` na raiz (não *commitar*) e exporte no ambiente de execução ou use o n8n Secrets:

```bash
# Fonte de dados
INPUT_CSV=data/dados_rundeck.csv
OUTPUT_CSV=data/clean.csv

# Features / Modelo
INPUT_CSV_CLEAN=data/clean.csv
OUTPUT_CSV_FEATS=data/features.csv
FEATURE_META=models/feature_meta.json
MODEL_PATH=models/rbm.joblib
RBM_COMPONENTS=32
RBM_LR=0.01
RBM_EPOCHS=50
RBM_BATCH=64
RBM_SEED=42
Z_THRESHOLD=2.0   # z-score para classificar "alto runtime" por job

# Saída web
OUTPUT_JSON=app/ai_analysis.json
TOP_N=20

# n8n / Scheduler (ex.: Rundeck)
RUNDECK_BASE_URL=https://<<host>>
RUNDECK_API_TOKEN=<<token>>
RUNDECK_PROJECT=<<nome-projeto>>
```

> **Dica**: no GitHub Actions/Amplify, use **Secrets** para credenciais (nunca exponha em `.env`).

---

## Esquema de dados esperado (`data/dados_rundeck.csv`)

O ETL é tolerante a variações de nome de coluna. Campos alvo e aliases aceitos:

| Campo alvo  | Aliases aceitos                              |
|-------------|-----------------------------------------------|
| job_id      | `job_id`, `id`, `execution_id`                |
| job_name    | `job_name`, `name`, `job`                     |
| project     | `project`, `project_name`                     |
| status      | `status`, `result`, `state`                   |
| start_time  | `start_time`, `started_at`, `start`           |
| end_time    | `end_time`, `ended_at`, `end`, `finish_time`  |

- Datas em ISO 8601 são preferidas. `duration_sec` é calculado como `end_time - start_time` (segundos).

---

## Como executar localmente

1) Instale dependências:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

2) Garanta `data/dados_rundeck.csv` com dados reais ou de teste.

3) Rode o pipeline completo:
```bash
python scripts/pipeline.py
```
Saída final: `app/ai_analysis.json` (consumido pelo painel).

4) Visualize o painel:
```bash
# Servir a pasta app/ em um server estático local
python -m http.server --directory app 8080
# abra http://localhost:8080
```

---

## Integração CI/CD (exemplo GitHub Actions)

`.github/workflows/mlops.yml` (exemplo mínimo):

```yaml
name: mlops-rbm
on:
  push:
    branches: [ main ]
    paths:
      - 'data/**'
      - 'scripts/**'
      - 'app/**'
      - 'requirements.txt'
jobs:
  build-run-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Run pipeline
        run: python scripts/pipeline.py
      - name: Commit artifacts
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add app/ai_analysis.json data/clean.csv data/features.csv models/*
          git commit -m "ci: update artifacts" || echo "No changes"
          git push
```

> **Amplify Hosting**: a pasta `app/` é estática (HTML/CSS/JS). Opcionalmente use um `amplify.yml` simples apontando `app/` como raiz de artefatos.

---

## KPIs & Insights gerados

- `summary.total_records` — total de execuções no período.
- `summary.failed_count` — quantidade de falhas.
- `summary.high_runtime_count` — quantidade de execuções com **alto tempo** (z-score > `Z_THRESHOLD` por job).
- `summary.cross_events_count` e `cross_events_rate` — eventos em que **falha** e **alto tempo** ocorreram juntos.
- `phi_failed_high_runtime` — **correlação phi** entre falha e alto tempo.
- `lift_failed_given_high_runtime` — **lift** de falha condicionado a alto tempo.
- `hotspots[]` — ranking `project/job_name` por volume de eventos cruzados, risco médio e p95.
- `top_risk_samples[]` — amostras com maior `risk_score` para auditoria.

---

## Operação, SLOs e alertas

- **SLO orientação**: ≤ 15 minutos entre ocorrência e exibição no painel.
- **Alertas**: configurar no **n8n** um gatilho quando `cross_events_count` ou densidade diária exceder limiar.
- **Versionamento**: `ai_analysis.json` é versionado a cada execução (diffs úteis para auditoria).

---

## Segurança e governança

- Segredos via **GitHub Secrets** / **Amplify Environment Variables**.
- Dados sensíveis: anonimizar `job_name`/`project` se necessário (hash ou mapeamento).
- **Imutabilidade** de artefatos: preferir *append-only* para `dados_rundeck.csv` + *commits* frequentes.

---

## Troubleshooting

- **`FileNotFoundError: data/dados_rundeck.csv`**: verifique se o n8n está populando ou crie uma massa de testes.
- **Sem `ai_analysis.json`**: rode `python scripts/pipeline.py` e confirme permissões de escrita em `app/`.
- **Mermaid não renderiza**: valide o bloco no Preview do GitHub; evite caracteres especiais e links dentro de nós.

---

## Roadmap (sugestões)

- Ajuste adaptativo do `Z_THRESHOLD` por **perfil de job** (EWMA ou quantis históricos).
- Score híbrido RBM + **Isolation Forest** para robustez.
- Exportar métricas para **Prometheus** e alarmes no **Grafana**.
- Enriquecimento com **custos** (FinOps) por job/projeto.

---

## Licença

MIT (ou ajuste conforme necessidade da organização).

