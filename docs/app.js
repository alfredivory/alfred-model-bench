const DATA_URL = "./results.json";

const COLORS = [
  "#6ee7b7","#93c5fd","#fca5a5","#fcd34d","#c4b5fd",
  "#f9a8d4","#67e8f9","#fdba74","#a5f3fc","#d9f99d",
  "#e879f9","#fbbf24",
];

const OPEN_WEIGHT_PREFIXES = ["meta-llama/", "qwen/", "deepseek/", "mistral/", "moonshotai/", "minimax/", "openai/gpt-oss-"];
const MAC_STUDIO_MODELS = [
  "meta-llama/llama-3.3-70b-instruct",
  "meta-llama/llama-4-maverick",
  "qwen/qwen-2.5-72b-instruct",
  "deepseek/deepseek-chat-v3-0324",
  "deepseek/deepseek-r1-0528",
  "moonshotai/kimi-k2.5",
  "minimax/minimax-m1",
  "qwen/qwen3-30b-a3b",
  "openai/gpt-oss-120b",
];

const MAC_STUDIO_ESTIMATES = {
  "meta-llama/llama-3.3-70b-instruct": { quant: "FP16", memGB: 140, tps: 8, qualityRetention: 100 },
  "qwen/qwen-2.5-72b-instruct": { quant: "FP16", memGB: 144, tps: 8, qualityRetention: 100 },
  "meta-llama/llama-4-maverick": { quant: "Q8", memGB: 400, tps: 12, qualityRetention: 99 },
  "deepseek/deepseek-chat-v3-0324": { quant: "Q4_K_M", memGB: 350, tps: 19, qualityRetention: 93 },
  "deepseek/deepseek-r1-0528": { quant: "Q4_K_M", memGB: 350, tps: 17, qualityRetention: 93 },
  "moonshotai/kimi-k2.5": { quant: "Q3_K_M", memGB: 480, tps: 15, qualityRetention: 90 },
  "minimax/minimax-m1": { quant: "Q8", memGB: 460, tps: 14, qualityRetention: 99 },
  "qwen/qwen3-30b-a3b": { quant: "FP16", memGB: 60, tps: 35, qualityRetention: 100 },
  "openai/gpt-oss-120b": { quant: "Q4_K_M", memGB: 70, tps: 20, qualityRetention: 95 },
};

const NEAR_AI_PRICING = {
  "anthropic/claude-opus-4": { input: 5.00, output: 25.00 },
  "deepseek/deepseek-chat-v3-0324": { input: 1.05, output: 3.10 },
};

function nearAiBlended(model) {
  const p = NEAR_AI_PRICING[model];
  return p ? (p.input + p.output) / 2 : null;
}

let sortDir = {};
let radarChart = null;
let barChart = null;
let globalData = null;
let currentFilter = "all";

function isOpenWeight(model) {
  return OPEN_WEIGHT_PREFIXES.some(p => model.startsWith(p));
}

function isMacStudio(model) {
  return MAC_STUDIO_MODELS.includes(model);
}

function filterModels(models) {
  if (currentFilter === "open") return models.filter(isOpenWeight);
  if (currentFilter === "mac") return models.filter(isMacStudio);
  return models;
}

function shortName(id) {
  return id.split("/").pop();
}

function modelTags(model) {
  const tags = [];
  if (isOpenWeight(model)) {
    tags.push('<span class="tag tag-open">Open Weight</span>');
    if (isMacStudio(model)) tags.push('<span class="tag tag-mac">Mac Studio OK</span>');
  } else {
    tags.push('<span class="tag tag-prop">Proprietary</span>');
  }
  return tags.join(" ");
}

function scoreClass(v) {
  if (v >= 80) return "score-high";
  if (v >= 50) return "score-mid";
  return "score-low";
}

async function main() {
  let data;
  try {
    const r = await fetch(DATA_URL);
    data = await r.json();
  } catch (e) {
    document.getElementById("meta").textContent = "Failed to load results. Run benchmarks first.";
    return;
  }
  globalData = data;

  document.getElementById("meta").textContent =
    `Generated ${new Date(data.timestamp).toLocaleString()} — ${data.results.length} results`;

  // Compute tokens/sec per model (avg across scenarios)
  computeTokensPerSec(data);
  computeCostPerMTok(data);

  renderFilters();
  renderAll();
}

function computeTokensPerSec(data) {
  data._tokPerSec = {};
  const byModel = {};
  for (const r of data.results) {
    if (!byModel[r.model]) byModel[r.model] = [];
    const ct = r.usage?.completion_tokens || 0;
    const dur = r.duration_s || 0;
    if (ct > 0 && dur > 0) byModel[r.model].push(ct / dur);
  }
  for (const [m, vals] of Object.entries(byModel)) {
    data._tokPerSec[m] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  }
}

function renderFilters() {
  const container = document.getElementById("filters");
  const buttons = [
    { id: "all", label: "All Models" },
    { id: "open", label: "Open Weight Only" },
    { id: "mac", label: "Mac Studio Runnable" },
  ];
  buttons.forEach(b => {
    const btn = document.createElement("button");
    btn.textContent = b.label;
    btn.className = "filter-btn" + (b.id === currentFilter ? " active" : "");
    btn.onclick = () => {
      currentFilter = b.id;
      container.querySelectorAll(".filter-btn").forEach(el => el.classList.remove("active"));
      btn.classList.add("active");
      renderAll();
    };
    container.appendChild(btn);
  });
}

function computeCostPerMTok(data) {
  data._costPerMTok = {};
  const byModel = {};
  for (const r of data.results) {
    if (!byModel[r.model]) byModel[r.model] = { cost: 0, tokens: 0 };
    byModel[r.model].cost += r.cost || 0;
    const pt = r.usage?.prompt_tokens || 0;
    const ct = r.usage?.completion_tokens || 0;
    byModel[r.model].tokens += pt + ct;
  }
  for (const [m, v] of Object.entries(byModel)) {
    data._costPerMTok[m] = v.tokens > 0 && v.cost > 0 ? (v.cost / v.tokens) * 1_000_000 : null;
  }
}

function renderAll() {
  const data = globalData;
  const summary = data.summary;
  const scenarios = Object.keys(summary.scenarios).sort();
  const allModels = summary.ranking.map(r => r.model);
  const models = filterModels(allModels);

  // Clear existing
  document.getElementById("table-head").innerHTML = "";
  document.getElementById("table-body").innerHTML = "";
  if (radarChart) { radarChart.destroy(); radarChart = null; }
  if (barChart) { barChart.destroy(); barChart = null; }
  document.getElementById("matrix-head").innerHTML = "";
  document.getElementById("matrix-body").innerHTML = "";
  sortDir = {};

  renderTable(models, scenarios, summary, data._tokPerSec, data._costPerMTok);
  renderRadar(models, scenarios, summary);
  renderBarChart(models, data._tokPerSec);
  renderArchitectureGuide(summary, data._costPerMTok, data._tokPerSec);
  renderRecommendations(allModels, summary, data._costPerMTok);
  renderMatrix(models, scenarios, summary);
}

/* ── Table ── */
function renderTable(models, scenarios, summary, tokPerSec, costPerMTok) {
  const head = document.getElementById("table-head");
  const cols = ["#", "Model", ...scenarios.map(s => s.replace(/_/g, " ")), "Avg", "Tok/s", "Best Quant ¹", "VRAM ¹", "Est. Local TPS ¹", "Est. Local Score ¹", "$/1M tok", "NEAR AI $/M"];
  cols.forEach((c, i) => {
    const th = document.createElement("th");
    if (c === "NEAR AI $/M") {
      th.innerHTML = '<span class="near-ai-header"><span class="near-ai-badge">NEAR AI</span>$/M</span>';
    } else {
      th.textContent = c;
    }
    th.style.cursor = "pointer";
    th.onclick = () => sortTable(i);
    head.appendChild(th);
  });

  const body = document.getElementById("table-body");
  models.forEach((m, idx) => {
    const s = summary.models[m];
    const tr = document.createElement("tr");

    // Rank
    const tdRank = document.createElement("td");
    tdRank.textContent = idx + 1;
    tr.appendChild(tdRank);

    // Model name + tags
    const tdModel = document.createElement("td");
    tdModel.innerHTML = `<span class="model-name">${shortName(m)}</span> ${modelTags(m)}`;
    tdModel.style.textAlign = "left";
    tr.appendChild(tdModel);

    // Scenario scores
    scenarios.forEach(sc => {
      const v = s.scores[sc] ?? "—";
      const td = document.createElement("td");
      td.textContent = v;
      if (typeof v === "number" && v <= 100 && v >= 0) td.classList.add(scoreClass(v));
      tr.appendChild(td);
    });

    // Average
    const tdAvg = document.createElement("td");
    tdAvg.textContent = s.average_score;
    if (typeof s.average_score === "number") tdAvg.classList.add(scoreClass(s.average_score));
    tr.appendChild(tdAvg);

    // Tokens/sec
    const tdTok = document.createElement("td");
    const tps = tokPerSec[m] || 0;
    tdTok.textContent = tps.toFixed(1);
    tr.appendChild(tdTok);

    // Best Quant
    const est = MAC_STUDIO_ESTIMATES[m];
    const tdQuant = document.createElement("td");
    tdQuant.textContent = est ? est.quant : "—";
    tr.appendChild(tdQuant);

    // VRAM
    const tdVram = document.createElement("td");
    tdVram.textContent = est ? `${est.memGB} GB` : "—";
    tr.appendChild(tdVram);

    // Est. Local TPS
    const tdLocal = document.createElement("td");
    tdLocal.textContent = est ? `~${est.tps}` : "—";
    tr.appendChild(tdLocal);

    // Est. Local Score
    const tdQual = document.createElement("td");
    if (est) {
      const estScore = (s.average_score * est.qualityRetention / 100).toFixed(1);
      tdQual.textContent = estScore;
      if (parseFloat(estScore) >= 0 && parseFloat(estScore) <= 100) tdQual.classList.add(scoreClass(parseFloat(estScore)));
      tdQual.title = "Estimated score when running locally = cloud score × quality retention at best-fit quantization";
    } else {
      tdQual.textContent = "—";
    }
    tr.appendChild(tdQual);

    // Cost per 1M tokens
    const tdCost = document.createElement("td");
    const cpm = costPerMTok[m];
    tdCost.textContent = cpm != null ? `$${cpm.toFixed(2)}/1M` : "—";
    tr.appendChild(tdCost);

    // NEAR AI $/M
    const tdNear = document.createElement("td");
    const nearCost = nearAiBlended(m);
    tdNear.textContent = nearCost != null ? `$${nearCost.toFixed(2)}/M` : "—";
    tr.appendChild(tdNear);

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

/* ── Radar ── */
function renderRadar(models, scenarios, summary) {
  const datasets = models.map((m, i) => ({
    label: shortName(m),
    data: scenarios.map((s) => summary.models[m].scores[s] ?? 0),
    borderColor: COLORS[i % COLORS.length],
    backgroundColor: COLORS[i % COLORS.length] + "22",
    pointRadius: 3,
  }));

  radarChart = new Chart(document.getElementById("radar-chart"), {
    type: "radar",
    data: { labels: scenarios.map(s => s.replace(/_/g, " ")), datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { r: { min: 0, max: 100, ticks: { stepSize: 20, color: "#888" }, grid: { color: "#333" }, pointLabels: { color: "#ccc" } } },
      plugins: { legend: { labels: { color: "#ccc", boxWidth: 12 } } },
    },
  });
}

/* ── Bar Chart (Tokens/sec) ── */
function renderBarChart(models, tokPerSec) {
  const ctx = document.getElementById("bar-chart");
  const data = models.map(m => tokPerSec[m] || 0);

  barChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: models.map(shortName),
      datasets: [{
        label: "Output Tokens/sec",
        data,
        backgroundColor: models.map((_, i) => COLORS[i % COLORS.length] + "cc"),
        borderColor: models.map((_, i) => COLORS[i % COLORS.length]),
        borderWidth: 1,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: "y",
      scales: {
        x: { grid: { color: "#333" }, ticks: { color: "#ccc" } },
        y: { grid: { color: "#333" }, ticks: { color: "#ccc", font: { size: 11 } } },
      },
      plugins: { legend: { display: false } },
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
      if (v === best[s]) td.className = "rec-best";
      else if (v >= best[s] - 10) td.className = "rec-good";
      else if (v >= 50) td.className = "rec-ok";
      else td.className = "rec-poor";
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

/* ── Recommendations ── */
function renderRecommendations(allModels, summary, costPerMTok) {
  const container = document.getElementById("recommendation-cards");
  container.innerHTML = "";

  // Best Cloud: highest avg score, tiebreak by lowest cost
  const ranked = allModels.map(m => ({ model: m, score: summary.models[m].average_score, cost: costPerMTok[m] }))
    .sort((a, b) => b.score - a.score || (a.cost || Infinity) - (b.cost || Infinity));
  const bestCloud = ranked[0];
  // Among models tied at top score, find best cost ratio
  const topScore = bestCloud.score;
  const topTied = ranked.filter(r => r.score === topScore);
  const cheapestTop = topTied.reduce((a, b) => ((a.cost || Infinity) < (b.cost || Infinity) ? a : b));
  const cloudNote = topTied.length > 1
    ? `${shortName(cheapestTop.model)} offers the best score-to-cost ratio among ${topTied.length} models tied at ${topScore}.`
    : `Top performer across all benchmarks.`;

  // Best Local: Mac Studio model with highest est local score
  const localRanked = MAC_STUDIO_MODELS
    .filter(m => summary.models[m])
    .map(m => {
      const est = MAC_STUDIO_ESTIMATES[m];
      const estScore = parseFloat((summary.models[m].average_score * est.qualityRetention / 100).toFixed(1));
      return { model: m, estScore, ...est };
    })
    .sort((a, b) => b.estScore - a.estScore);
  const bestLocal = localRanked[0];
  const localNote = bestLocal.qualityRetention === 100
    ? `Full ${bestLocal.quant} precision with zero quality loss. Best local option.`
    : `${bestLocal.quant} quantization with ${bestLocal.qualityRetention}% quality retention.`;

  // Best Value: highest score-per-dollar (local = infinite value, so pick best cloud value)
  const valueModels = allModels
    .filter(m => costPerMTok[m] != null && costPerMTok[m] > 0)
    .map(m => ({ model: m, score: summary.models[m].average_score, cost: costPerMTok[m], ratio: summary.models[m].average_score / costPerMTok[m] }))
    .sort((a, b) => b.ratio - a.ratio);
  const bestValue = valueModels[0];
  const valueNote = bestLocal
    ? `For budget setups, ${shortName(bestLocal.model)} locally costs $0/token with competitive quality (est. ${bestLocal.estScore}).`
    : `Best bang for your buck in the cloud.`;

  const cards = [
    { cls: "rec-card-cloud", icon: "☁️", title: "Best Cloud Agent", model: shortName(bestCloud.model), stats: [
      { label: "Score", value: bestCloud.score },
      ...(bestCloud.cost != null ? [{ label: "Cost", value: `$${bestCloud.cost.toFixed(2)}/1M tok` }] : []),
    ], note: cloudNote },
    ...(bestLocal ? [{ cls: "rec-card-local", icon: "🖥️", title: "Best Local Agent (Mac Studio 512GB)", model: shortName(bestLocal.model), stats: [
      { label: "Est. Score", value: bestLocal.estScore },
      { label: "Quant", value: bestLocal.quant },
      { label: "TPS", value: `~${bestLocal.tps}` },
      { label: "VRAM", value: `${bestLocal.memGB} GB` },
    ], note: localNote }] : []),
    ...(bestValue ? [{ cls: "rec-card-value", icon: "💰", title: "Best Value Agent", model: shortName(bestValue.model), stats: [
      { label: "Score", value: bestValue.score },
      { label: "Cost", value: `$${bestValue.cost.toFixed(2)}/1M tok` },
      { label: "Score/$", value: bestValue.ratio.toFixed(1) },
    ], note: valueNote }] : []),
  ];

  cards.forEach(c => {
    const div = document.createElement("div");
    div.className = `rec-card ${c.cls}`;
    div.innerHTML = `
      <div class="rec-card-icon">${c.icon}</div>
      <div class="rec-card-title">${c.title}</div>
      <div class="rec-card-model">${c.model}</div>
      <div class="rec-card-stats">${c.stats.map(s => `<span class="rec-card-stat">${s.label}: <strong>${s.value}</strong></span>`).join("")}</div>
      <div class="rec-card-note">${c.note}</div>
    `;
    container.appendChild(div);
  });
}

main();
