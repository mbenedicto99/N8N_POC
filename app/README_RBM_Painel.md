# Rundeck AI – Painel de Falhas × Alto Tempo (RBM)
Painel estático que lê `./app/ai_analysis.json` (same-origin). Sem S3.

## Arquitetura
```mermaid
flowchart LR
  subgraph User["🧑‍💻 Operação / Diretoria"]
    B[Browser<br/>index.html + app.js]
  end
  subgraph Hosting["Hosting estático"]
    H[/Site (HTML, JS, CSS)/]
    J[(/app/ai_analysis.json)]
  end
  subgraph Pipeline["Pipeline de Dados"]
    R[Rundeck/CI]
    E[etl.py]
    F[features.py]
    M[rbm_train.py]
    G[build_ai_json.py]
  end
  B -- GET /index.html,/app.js --> H
  B -- GET /app/ai_analysis.json --> J
  R --> E --> F --> M --> G --> J
