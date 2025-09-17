# Rundeck AI – Falhas x Alto Tempo (RBM)

Painel estático (HTML/JS) para visualizar riscos de falhas e alto tempo de execução de Jobs (Rundeck).  
**Fonte de dados:** `./app/ai_analysis.json` servido no **mesmo domínio** do site (sem S3).

## 📁 Estrutura

```
.
├─ public/
│  ├─ index.html
│  ├─ app.js
│  └─ app/
│     └─ ai_analysis.json        # gerado pelo pipeline (RBM/ETL)
├─ package.json
└─ amplify.yml                   # build e cópia do JSON para a pasta final
```

> Se usar Vite/React, a pasta final pode ser `dist/` ou `build/`. O JSON deve ser copiado para `dist/app/ai_analysis.json`.

## 🔌 Consumo de dados (same-origin)

O front busca os dados **localmente**, evitando cache:

```js
// app.js
const DATA_URL = new URL('./app/ai_analysis.json?ts=' + Date.now(), document.baseURI);
const res = await fetch(DATA_URL, { cache: 'no-store', credentials: 'same-origin' });
```

## 🔧 Build & Deploy (Amplify Hosting)

### 1) `amplify.yml` (exemplo com Vite)
Copia o JSON para a saída final e publica **sem S3** externo:

```yaml
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run build
        # garanta que o JSON vá para a pasta publicada
        - mkdir -p dist/app
        - cp public/app/ai_analysis.json dist/app/ai_analysis.json
  artifacts:
    baseDirectory: dist
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
```

### 2) Rewrites & Redirects (ordem importa)

Primeiro **preserve tudo que começa com `/app/`**, depois a rota SPA:

```json
[
  { "source": "/app/<*>", "target": "/app/<*>", "status": "200" },
  { "source": "/<*>",     "target": "/index.html", "status": "200" }
]
```

### 3) Custom Headers

Garanta o tipo correto e desabilite cache do JSON:

```
Source: /app/*.json
Content-Type: application/json
Cache-Control: no-cache
```

## ▶️ Execução local

Sem servidor especial: qualquer estático serve.

```bash
# 1) instalar deps (se houver)
npm i

# 2) rodar preview local (ex.: Vite)
npm run dev
# ou servir a pasta 'public/' num servidor simples
npx http-server public -p 8080
```

Acesse: `http://localhost:8080/` e confira `http://localhost:8080/app/ai_analysis.json`.

## 🧪 JSON – esquema mínimo esperado

```json
{
  "meta": { "modelo": "BernoulliRBM", "periodo": "último trimestre" },
  "resumo": {
    "registros": 1234,
    "falhas": 87,
    "alto_tempo": 42,
    "eventos_cruzados": 19,
    "taxa_cruzada": 0.34,
    "phi": 0.21,
    "lift": 1.8
  },
  "hotspots": [
    { "projeto": "X", "job": "Y", "eventos": 12, "risco_medio": 0.73, "risco_p95": 0.92, "duracao_media_s": 410 }
  ],
  "risco_p95_por_job": [
    { "job": "Y", "p95": 732, "duracao_media": 410 }
  ],
  "top_amostras": [
    { "projeto": "X", "job": "Y", "exec_id": "abc", "inicio": "2025-09-17T10:00:00Z", "status": "FAILED", "duracao_s": 930, "risco": 0.92 }
  ]
}
```

> Não use `NaN`, `Infinity` ou comentários no JSON. Números com vírgula (`"0,9"`) são tolerados pelo front, mas prefira ponto decimal.

## 🛠️ Geração do `ai_analysis.json`

O pipeline (RBM/ETL) deve **escrever/atualizar** `public/app/ai_analysis.json` (ou copiar para `dist/app/`) ao final do build. Exemplo de comando:

```bash
python scripts/build_ai_json.py --out public/app/ai_analysis.json
```

## 🩺 Troubleshooting

1. **Página diz “Erro ao carregar dados”**  
   - DevTools → Network → clique em `/app/ai_analysis.json`.  
   - Se **Preview mostra HTML**: ajuste as Rewrites (a regra `/app/<*>` deve vir **antes** da SPA).  
   - Se **404**: o arquivo não foi publicado; garanta a cópia no `amplify.yml`.  
   - Se **Content-Type ≠ application/json**: configure o header.

2. **Gráficos não renderizam / travam**  
   - Dados não-numéricos. O front já saneia `"0,9"`, `null`, strings; ainda assim valide o JSON.

3. **Cache**  
   - O front usa `?ts=` e `cache: 'no-store'`. Mantenha `Cache-Control: no-cache` nos headers.

## 📜 Licença

Uso interno. Ajuste conforme sua política.
