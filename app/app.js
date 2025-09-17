/* eslint-disable no-console */
const fmt = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });

const dtFmt = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short', timeStyle: 'short', hour12: false,
  timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
});

async function headJSON(path = 'ai_analysis.json') {
  const cacheBuster = `_=${Date.now()}`;
  const url = path.includes('?') ? `${path}&${cacheBuster}` : `${path}?${cacheBuster}`;
  const res = await fetch(url, { method: 'HEAD', cache: 'no-store' });
  if (!res.ok) throw new Error(`Falha ao consultar HEAD de ${path}: ${res.status}`);
  return {
    lastModified: res.headers.get('Last-Modified'),
    etag: res.headers.get('ETag')
  };
}

function setBadge(text) {
  const el = document.getElementById('badge-updated');
  if (el) el.textContent = text;
}

async function updateLastModified() {
  try {
    const { lastModified } = await headJSON('ai_analysis.json');
    if (lastModified) {
      const dt = new Date(lastModified);
      setBadge(`Última atualização: ${dtFmt.format(dt)}`);
    } else {
      setBadge('Última atualização: indisponível');
    }
  } catch (e) {
    console.error(e);
    setBadge('Última atualização: erro ao consultar');
  }
}

async function loadJSON(path = 'ai_analysis.json') {
  const cacheBuster = `_=${Date.now()}`;
  const url = path.includes('?') ? `${path}&${cacheBuster}` : `${path}?${cacheBuster}`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Falha ao carregar ${path}: ${res.status}`);
  return res.json();
}

function setKPI(id, value, fractionDigits = 2) {
  const el = document.getElementById(id);
  if (!el) return;
  const v = typeof value === 'number'
    ? new Intl.NumberFormat('pt-BR', { maximumFractionDigits: fractionDigits }).format(value)
    : (value ?? '–');
  el.textContent = v;
}

function buildHotspotsTable(hotspots = []) {
  const tbody = document.querySelector('#tbl-hotspots tbody');
  tbody.innerHTML = '';
  hotspots.forEach(h => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${h.project ?? ''}</td>
      <td title="\${h.job_name}">\${h.job_name ?? ''}</td>
      <td class="num">\${h.events ?? 0}</td>
      <td class="num">\${fmt.format(h.avg_risk ?? 0)}</td>
      <td class="num">\${fmt.format(h.p95_risk ?? 0)}</td>
      <td class="num">\${fmt.format(h.avg_duration ?? 0)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function buildSamplesTable(samples = []) {
  const tbody = document.querySelector('#tbl-samples tbody');
  tbody.innerHTML = '';
  samples.forEach(s => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${s.project ?? ''}</td>
      <td title="\${s.job_name}">\${s.job_name ?? ''}</td>
      <td class="mono">\${s.job_id ?? ''}</td>
      <td>\${s.start_time ?? ''}</td>
      <td>\${s.status ?? ''}</td>
      <td class="num">\${fmt.format(s.duration_sec ?? 0)}</td>
      <td class="num">\${fmt.format(s.risk_score ?? 0)}</td>
    `;
    tbody.appendChild(tr);
  });
}

let charts = [];

function destroyCharts() {
  charts.forEach(c => c?.destroy());
  charts = [];
}

function buildCharts(hotspots = []) {
  destroyCharts();
  const top = hotspots.slice(0, 10);
  const labels = top.map(h => `${h.project ?? ''} :: ${h.job_name ?? ''}`);

  const ctx1 = document.getElementById('chartHotspots').getContext('2d');
  charts.push(new Chart(ctx1, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Eventos cruzados',
        data: top.map(h => h.events ?? 0)
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: true } },
      scales: { x: { ticks: { autoSkip: false } } }
    }
  }));

  const ctx2 = document.getElementById('chartRisk').getContext('2d');
  charts.push(new Chart(ctx2, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Risco médio', data: top.map(h => h.avg_risk ?? 0) },
        { label: 'Risco p95', data: top.map(h => h.p95_risk ?? 0) }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: true } },
      scales: { x: { ticks: { autoSkip: false } } }
    }
  }));
}

function applyData(json) {
  const sum = json?.summary ?? {};
  setKPI('kpi-total', sum.total_records ?? 0, 0);
  setKPI('kpi-failed', sum.failed_count ?? 0, 0);
  setKPI('kpi-high', sum.high_runtime_count ?? 0, 0);
  setKPI('kpi-cross', sum.cross_events_count ?? 0, 0);
  setKPI('kpi-cross-rate', (sum.cross_events_rate ?? 0) * 100, 3);
  setKPI('kpi-phi', sum.phi_failed_high_runtime ?? 0, 3);
  setKPI('kpi-lift', sum.lift_failed_given_high_runtime ?? 0, 3);

  const hotspots = Array.isArray(json?.hotspots) ? json.hotspots : [];
  buildHotspotsTable(hotspots);
  buildCharts(hotspots);

  const samples = Array.isArray(json?.top_risk_samples) ? json.top_risk_samples : [];
  buildSamplesTable(samples);
}

async function init() {
  try {
    updateLastModified();
    const data = await loadJSON('ai_analysis.json');
    applyData(data);
  } catch (err) {
    console.error(err);
    alert('Não foi possível carregar ai_analysis.json. Verifique se o pipeline já gerou o arquivo.');
  }
  document.getElementById('btn-reload')?.addEventListener('click', init, { once: true });
}
document.addEventListener('DOMContentLoaded', init);
