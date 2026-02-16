const DATA_URL = "./results.json";

const COLORS = [
  "#6ee7b7","#93c5fd","#fca5a5","#fcd34d","#c4b5fd",
  "#f9a8d4","#67e8f9","#fdba74","#a5f3fc","#d9f99d",
  "#e879f9","#fbbf24",
];

let sortDir = {};

async function main() {
  let data;
  try {
    const r = await fetch(DATA_URL);
    data = await r.json();
  } catch (e) {
    document.getElementById("meta").textContent = "Failed to load results. Run benchmarks first.";
    return;
  }

  document.getElementById("meta").textContent =
    `Generated ${new Date(data.timestamp).toLocaleString()} — ${data.results.length} results`;

  const summary = data.summary;
  const scenarios = Object.keys(summary.scenarios).sort();
  const models = summary.ranking.map((r) => r.model);

  renderTable(models, scenarios, summary);
  renderRadar(models, scenarios, summary);
  renderMatrix(models, scenarios, summary);
}

function shortName(id) {
  return id.split("/").pop();
}

/* ── Table ── */
function renderTable(models, scenarios, summary) {
  const head = document.getElementById("table-head");
  const cols = ["#", "Model", ...scenarios.map(s => s.replace(/_/g, " ")), "Avg", "Cost ($)"];
  cols.forEach((c, i) => {
    const th = document.createElement("th");
    th.textContent = c;
    th.style.cursor = "pointer";
    th.onclick = () => sortTable(i);
    head.appendChild(th);
  });

  const body = document.getElementById("table-body");
  models.forEach((m, idx) => {
    const s = summary.models[m];
    const tr = document.createElement("tr");
    const cells = [
      idx + 1,
      shortName(m),
      ...scenarios.map((sc) => s.scores[sc] ?? "—"),
      s.average_score,
      s.total_cost.toFixed(4),
    ];
    cells.forEach((v) => {
      const td = document.createElement("td");
      td.textContent = v;
      if (typeof v === "number" && v <= 100 && v >= 0) td.classList.add(scoreClass(v));
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

function sortTable(colIdx) {
  const body = document.getElementById("table-body");
  const rows = Array.from(body.rows);
  const dir = (sortDir[colIdx] = !sortDir[colIdx]) ? 1 : -1;
  rows.sort((a, b) => {
    const av = a.cells[colIdx].textContent;
    const bv = b.cells[colIdx].textContent;
    const an = parseFloat(av), bn = parseFloat(bv);
    if (!isNaN(an) && !isNaN(bn)) return (an - bn) * dir;
    return av.localeCompare(bv) * dir;
  });
  rows.forEach((r) => body.appendChild(r));
}

function scoreClass(v) {
  if (v >= 80) return "score-high";
  if (v >= 50) return "score-mid";
  return "score-low";
}

/* ── Radar ── */
function renderRadar(models, scenarios, summary) {
  const datasets = models.map((m, i) => ({
    label: shortName(m),
    data: scenarios.map((s) => summary.models[m].scores[s] ?? 0),
    borderColor: COLORS[i % COLORS.length],
    backgroundColor: COLORS[i % COLORS.length] + "22",
    pointRadius: 3,
  }));

  new Chart(document.getElementById("radar-chart"), {
    type: "radar",
    data: {
      labels: scenarios.map((s) => s.replace(/_/g, " ")),
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { r: { min: 0, max: 100, ticks: { stepSize: 20, color: "#888" }, grid: { color: "#333" }, pointLabels: { color: "#ccc" } } },
      plugins: { legend: { labels: { color: "#ccc", boxWidth: 12 } } },
    },
  });
}

/* ── Recommendation Matrix ── */
function renderMatrix(models, scenarios, summary) {
  const head = document.getElementById("matrix-head");
  const th0 = document.createElement("th");
  th0.textContent = "Model";
  head.appendChild(th0);
  scenarios.forEach((s) => {
    const th = document.createElement("th");
    th.textContent = s.replace(/_/g, " ");
    head.appendChild(th);
  });

  const body = document.getElementById("matrix-body");
  // Find best per scenario
  const best = {};
  scenarios.forEach((s) => {
    best[s] = Math.max(...models.map((m) => summary.models[m].scores[s] ?? 0));
  });

  models.forEach((m) => {
    const tr = document.createElement("tr");
    const td0 = document.createElement("td");
    td0.textContent = shortName(m);
    tr.appendChild(td0);
    scenarios.forEach((s) => {
      const v = summary.models[m].scores[s] ?? 0;
      const td = document.createElement("td");
      td.textContent = v;
      // Color: green if best, yellow if within 10, red if low
      if (v === best[s]) td.className = "rec-best";
      else if (v >= best[s] - 10) td.className = "rec-good";
      else if (v >= 50) td.className = "rec-ok";
      else td.className = "rec-poor";
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

main();
