// app.js (ESM) — sem S3, same-origin

// ---------- helpers ----------
const $ = (sel) => document.querySelector(sel);
const fmt = (v, d = 0) =>
  (v ?? 0).toLocaleString("pt-BR", {
    maximumFractionDigits: d,
    minimumFractionDigits: d,
  });

// Aceita "0,9", remove lixo, trata NaN/Infinity/null
const toNum = (v, fallback = 0) => {
  if (v === null || v === undefined) return fallback;
  if (typeof v === "string")
    v = v.replace(",", ".").replace(/[^0-9eE.\-+]/g, "");
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
};

const esc = (s) =>
  (s ?? "").toString().replace(/[&<>"]/g, (m) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
  })[m]);

function fillTable(sel, arr, rowFn, cols = 7) {
  const tbody = document.querySelector(sel);
  tbody.innerHTML = "";
  if (!Array.isArray(arr) || arr.length === 0) {
    tbody.innerHTML = `<tr><td colspan="${cols}" style="text-align:center;color:#94a3b8">Sem dados</td></tr>`;
    return;
  }
  tbody.innerHTML = arr.map(rowFn).join("");
}

// ---------- data ----------
const DATA_URL = new URL("./app/ai_analysis.json?ts=" + Date.now(), document.baseURI);

async function loadData() {
  setStatus("Atualizando…");
  try {
    const res = await fetch(DATA_URL, {
      cache: "no-store",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) throw new Error("Falha ao carregar ai_analysis.json: " + res.status);
    const data = await res.json();
    renderAll(data);
    setStatus("Atualizado");
  } catch (e) {
    console.error(e);
    setStatus("Erro ao carregar dados");
    renderAll(null);
  }
}

function setStatus(text) {
  const el = $("#badge-updated");
  if (el) el.textContent = text;
}

// ---------- render ----------
let chartHotspots, chartRisk;

function renderAll(d) {
  // KPIs
  const r = d?.resumo || {};
  $("#kpi-total").textContent = fmt(toNum(r.registros));
  $("#kpi-failed").textContent = fmt(toNum(r.falhas));
  $("#kpi-high").textContent = fmt(toNum(r.alto_tempo ?? r.altoTempo));
  $("#kpi-cross").textContent = fmt(toNum(r.eventos_cruzados ?? r.eventosCruzados));
  $("#kpi-cross-rate").textContent = fmt(toNum(r.taxa_cruzada ?? r.taxaCruzada, 2), 2);
  $("#kpi-phi").textContent = fmt(toNum(r.phi ?? r["phi_falha_alto"] ?? r.phi_falha_alto, 3), 3);
  $("#kpi-lift").textContent = fmt(
    toNum(r.lift ?? r.lift_falha_alto ?? r["lift_falha_alto"], 2),
    2
  );

  // Tabelas
  fillTable(
    "#tbl-hotspots tbody",
    d?.hotspots,
    (x) => `
    <tr>
      <td>${esc(x.projeto)}</td>
      <td>${esc(x.job)}</td>
      <td>${fmt(toNum(x.eventos))}</td>
      <td>${fmt(toNum(x.risco_medio ?? x.riscoMedio, 3), 3)}</td>
      <td>${fmt(toNum(x.risco_p95 ?? x.riscoP95, 3), 3)}</td>
      <td>${fmt(toNum(x.duracao_media_s ?? x.duracaoMediaS ?? x.duracao, 0))}</td>
    </tr>`,
    6
  );

  fillTable(
    "#tbl-samples tbody",
    d?.top_amostras ?? d?.amostras ?? d?.samples,
    (s) => `
    <tr>
      <td>${esc(s.projeto)}</td>
      <td>${esc(s.job)}</td>
      <td>${esc(s.exec_id ?? s.execId ?? "")}</td>
      <td>${esc(s.inicio ?? s.start ?? "")}</td>
      <td>${esc(s.status ?? "")}</td>
      <td>${fmt(toNum(s.duracao_s ?? s.duracao ?? 0))}</td>
      <td>${fmt(toNum(s.risco ?? s.risk, 3), 3)}</td>
    </tr>`,
    7
  );

  // Gráficos
  renderCharts(d);
}
