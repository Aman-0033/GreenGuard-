let chart, labels = [], values = [], anomalies = [];

function initChart() {
  const ctx = document.getElementById('chart').getContext('2d');
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'kW', data: values, fill: true, borderColor: '#00ff88', backgroundColor: 'rgba(0,255,136,0.08)' },
        { label: 'Anomaly', data: anomalies, pointRadius: 6, showLine: false, borderColor: '#ff4444' }
      ]
    },
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: { display: false },
        y: { beginAtZero: true }
      }
    }
  });
}

async function fetchStream() {
  try {
    const r = await fetch('/api/stream');
    return await r.json();
  } catch (e) { console.error(e); return {data: [], alerts: []}; }
}

function renderAlerts(alerts) {
  const wrap = document.getElementById('alerts');
  wrap.innerHTML = '';
  (alerts || []).slice().reverse().forEach(a => {
    const div = document.createElement('div');
    div.className = 'alert ' + (a.severity || 'info');
    const ts = new Date(a.timestamp * 1000).toLocaleTimeString();
    div.innerHTML = `<b>${ts}</b> — ${a.message} <em>(CO₂ saved: ${a.avoided_emissions.toFixed(3)} kg)</em>`;
    wrap.appendChild(div);
  });
}

function updateFacts(stream) {
  const anomCount = (stream.data || []).filter(d => d.anomaly).length;
  document.getElementById('anomCount').innerText = anomCount;
  const last = (stream.data || [])[stream.data.length-1];
  document.getElementById('co2').innerText = last ? last.avoided_emissions_total.toFixed(3) : '0.000';
  document.getElementById('status').innerText = last && last.anomaly ? `Anomaly: ${last.type}` : 'Monitoring';
}

async function loop() {
  const stream = await fetchStream();
  labels.length = 0; values.length = 0; anomalies.length = 0;
  (stream.data || []).forEach((d, i) => {
    labels.push(i);
    values.push(d.kw);
    anomalies.push(d.anomaly ? d.kw : null);
  });
  chart.update();
  renderAlerts(stream.alerts || []);
  updateFacts(stream);
  setTimeout(loop, 1000);
}

async function apply() {
  const z = parseFloat(document.getElementById('zth').value);
  const a = parseFloat(document.getElementById('alpha').value);
  await fetch('/api/tune', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ z_threshold: z, ewma_alpha: a })
  });
  alert(`Settings applied: Z=${z}, EWMA=${a}`);
}

async function demo() {
  const res = await fetch('/demo', { method: 'POST' });
  const j = await res.json();
  alert(j.message);
}

document.getElementById('apply').addEventListener('click', apply);
document.getElementById('demo').addEventListener('click', demo);

initChart();
loop();

