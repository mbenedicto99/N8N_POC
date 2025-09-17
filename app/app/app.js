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
