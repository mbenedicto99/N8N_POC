#!/usr/bin/env bash
set -euo pipefail

echo "== Rundeck AI – Fixador de app estatico (Amplify) =="

ROOT="$(pwd)"
APP_DIR="$ROOT/app"
OUT_YML="$ROOT/amplify.yml"

# -------------------------------------------------------------------
# 1) Conferências básicas
# -------------------------------------------------------------------
command -v git >/dev/null || { echo "git não encontrado"; exit 1; }
command -v node >/dev/null || echo "Aviso: node não encontrado (ok se app for estático puro)"
git rev-parse --is-inside-work-tree >/dev/null || { echo "Não é um repositório git"; exit 1; }

# -------------------------------------------------------------------
# 2) Estrutura /app e JSON de exemplo (se faltar)
# -------------------------------------------------------------------
mkdir -p "$APP_DIR/app"
if [ ! -f "$APP_DIR/app/ai_analysis.json" ]; then
  echo ">> Criando app/app/ai_analysis.json (exemplo)"
  cat > "$APP_DIR/app/ai_analysis.json" <<'JSON'
{
  "meta": { "modelo": "BernoulliRBM", "periodo": "último trimestre", "gerado_em": "2025-09-17T00:00:00Z" },
  "resumo": { "registros": 2500, "falhas": 87, "alto_tempo": 42, "eventos_cruzados": 19, "taxa_cruzada": 0.34, "phi": 0.21, "lift": 1.8 },
  "hotspots": [
    { "projeto": "core", "job": "daily_settlement", "eventos": 12, "risco_medio": 0.73, "risco_p95": 0.92, "duracao_media_s": 410 }
  ],
  "risco_p95_por_job": [
    { "job": "daily_settlement", "p95": 732, "duracao_media": 410 }
  ],
  "top_amostras": [
    { "projeto": "core", "job": "daily_settlement", "exec_id": "abc", "inicio": "2025-09-17T10:00:00Z", "status": "FAILED", "duracao_s": 930, "risco": 0.92 }
  ]
}
JSON
fi

# -------------------------------------------------------------------
# 3) app.js (same-origin, saneamento, sem S3)
# -------------------------------------------------------------------
if [ ! -f "$APP_DIR/app.js" ]; then
  echo ">> Criando app/app.js"
else
  echo ">> Sobrescrevendo app/app.js (backup em app/app.js.bak)"
  cp -f "$APP_DIR/app.js" "$APP_DIR/app.js.bak"
fi
cat > "$APP_DIR/app.js" <<'JS'
// app.js — same-origin, sem S3
const $ = (s) => document.querySelector(s);
const fmt = (v, d=0) => (v ?? 0).toLocaleString("pt-BR",{maximumFractionDigits:d,minimumFractionDigits:d});
const toNum = (v,f=0)=>{ if(v==null)return f; if(typeof v==="string") v=v.replace(",",".").replace(/[^0-9eE.\-+]/g,""); const n=Number(v); return Number.isFinite(n)?n:f; };
const DATA_URL = new URL("./app/ai_analysis.json?ts="+Date.now(), document.baseURI);
let chartHotspots, chartRisk;

async function loadData(){
  setStatus("Atualizando…");
  try{
    const res = await fetch(DATA_URL,{cache:"no-store",credentials:"same-origin",headers:{"Accept":"application/json"}});
    console.log("ai_analysis.json ->", res.status, res.headers.get("content-type"));
    if(!res.ok) throw new Error("HTTP "+res.status);
    const txt = await res.text();
    const data = JSON.parse(txt);
    renderAll(data); setStatus("Atualizado");
  }catch(e){
    console.error("Falha ao carregar ai_analysis.json:", e);
    setStatus("Erro ao carregar dados"); renderAll(null);
  }
}
function setStatus(t){ const el=$("#badge-updated"); if(el) el.textContent=t; }
function esc(s){ return (s??"").toString().replace(/[&<>"]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[m])); }
function fillTable(sel,arr,rowFn,cols=7){ const tb=document.querySelector(sel); tb.innerHTML=""; if(!Array.isArray(arr)||!arr.length){ tb.innerHTML=`<tr><td colspan="${cols}" style="text-align:center;color:#94a3b8">Sem dados</td></tr>`; return;} tb.innerHTML=arr.map(rowFn).join(""); }

function renderAll(d){
  const r=d?.resumo||{};
  $("#kpi-total")?.append(fmt(toNum(r.registros)));
  $("#kpi-failed")?.append(fmt(toNum(r.falhas)));
  $("#kpi-high")?.append(fmt(toNum(r.alto_tempo??r.altoTempo)));
  $("#kpi-cross")?.append(fmt(toNum(r.eventos_cruzados??r.eventosCruzados)));
  $("#kpi-cross-rate")?.append(fmt(toNum(r.taxa_cruzada??r.taxaCruzada,2),2));
  $("#kpi-phi")?.append(fmt(toNum(r.phi??r["phi_falha_alto"]??r.phi_falha_alto,3),3));
  $("#kpi-lift")?.append(fmt(toNum(r.lift??r.lift_falha_alto??r["lift_falha_alto"],2),2));

  fillTable("#tbl-hotspots tbody", d?.hotspots, (x)=>`
    <tr><td>${esc(x.projeto)}</td><td>${esc(x.job)}</td>
    <td>${fmt(toNum(x.eventos))}</td>
    <td>${fmt(toNum(x.risco_medio??x.riscoMedio,3),3)}</td>
    <td>${fmt(toNum(x.risco_p95??x.riscoP95,3),3)}</td>
    <td>${fmt(toNum(x.duracao_media_s??x.duracaoMediaS??x.duracao,0))}</td></tr>`, 6);

  fillTable("#tbl-samples tbody", d?.top_amostras??d?.amostras??d?.samples, (s)=>`
    <tr><td>${esc(s.projeto)}</td><td>${esc(s.job)}</td>
    <td>${esc(s.exec_id??s.execId??"")}</td><td>${esc(s.inicio??s.start??"")}</td>
    <td>${esc(s.status??"")}</td><td>${fmt(toNum(s.duracao_s??s.duracao??0))}</td>
    <td>${fmt(toNum(s.risco??s.risk,3),3)}</td></tr>`, 7);
}
window.addEventListener("DOMContentLoaded", loadData);
window.addEventListener("error", (e)=>console.error("Uncaught:", e.message));
JS

# -------------------------------------------------------------------
# 4) Patch em index.html — garante fetch relativo (se arquivo existir)
# -------------------------------------------------------------------
if [ -f "$APP_DIR/index.html" ]; then
  echo ">> Ajustando app/index.html (fetch relativo)"
  cp -f "$APP_DIR/index.html" "$APP_DIR/index.html.bak"
  # remove URLs absolutas para ai_analysis.json e deixa ./app/ai_analysis.json
  sed -i -E 's#https?://[^"]*/app/ai_analysis\.json#./app/ai_analysis.json#g' "$APP_DIR/index.html" || true
fi

# -------------------------------------------------------------------
# 5) package.json + package-lock.json mínimos (se faltarem)
# -------------------------------------------------------------------
if [ ! -f "$ROOT/package.json" ]; then
  echo ">> Criando package.json mínimo"
  cat > "$ROOT/package.json" <<'PKG'
{
  "name": "rundeck-ai-panel",
  "version": "1.0.0",
  "private": true,
  "description": "Painel estático que lê ./app/ai_analysis.json no mesmo domínio (sem S3).",
  "license": "UNLICENSED",
  "engines": { "node": ">=18" },
  "scripts": {
    "build": "node -e \"require('fs').rmSync('webout',{recursive:true,force:true}); require('fs').mkdirSync('webout',{recursive:true}); require('fs').cpSync('app','webout',{recursive:true});\"",
    "dev": "node -e \"console.log('Use: npx http-server app -p 8080')\"",
    "test": "node -e \"console.log('sem testes')\""
  }
}
PKG
fi

if [ ! -f "$ROOT/package-lock.json" ]; then
  echo ">> Criando package-lock.json mínimo"
  cat > "$ROOT/package-lock.json" <<'LOCK'
{
  "name": "rundeck-ai-panel",
  "version": "1.0.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": { "name": "rundeck-ai-panel", "version": "1.0.0", "license": "UNLICENSED" }
  }
}
LOCK
fi

# -------------------------------------------------------------------
# 6) amplify.yml (sem erro de ':' e build para ./app → webout/)
# -------------------------------------------------------------------
echo ">> Escrevendo amplify.yml"
cat > "$OUT_YML" <<'YML'
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - |
          set -euo pipefail
          echo "Top-level:"
          ls -la
          test -d app || (echo "ERRO: diretório './app' não encontrado"; exit 1)
          echo "Conteúdo de ./app:"
          ls -la app
    build:
      commands:
        - |
          set -euo pipefail
          ROOT="$PWD"
          APP_DIR="$ROOT/app"
          OUT="$ROOT/webout"
          rm -rf "$OUT" && mkdir -p "$OUT"

          if [ -f "$APP_DIR/package.json" ]; then
            echo "Build Node detectado em ./app"
            cd "$APP_DIR"
            if [ -f package-lock.json ]; then npm ci; else npm install; fi
            npm run build
            if [ -d dist ]; then BUILD_DIR="dist"
            elif [ -d build ]; then BUILD_DIR="build"
            else
              echo "ERRO: não encontrei 'dist' nem 'build' após npm run build"
              exit 1
            fi
            cd "$ROOT"
            cp -r "$APP_DIR/$BUILD_DIR/"* "$OUT"/
          else
            echo "Site estático puro em ./app — copiando arquivos"
            cp -r "$APP_DIR/"* "$OUT"/
          fi

          mkdir -p "$OUT/app"
          if [ -f "$APP_DIR/app/ai_analysis.json" ]; then
            cp -f "$APP_DIR/app/ai_analysis.json" "$OUT/app/ai_analysis.json"
          fi

          echo "Artifact final em $OUT"
          ls -la "$OUT" || true
          ls -la "$OUT/app" || true
  artifacts:
    baseDirectory: webout
    files:
      - '**/*'
  cache:
    paths:
      - app/node_modules/**/*
YML

# -------------------------------------------------------------------
# 7) README técnico (com Mermaid e RBM)
# -------------------------------------------------------------------
cat > "$ROOT/README_RBM_Painel.md" <<'MD'
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
