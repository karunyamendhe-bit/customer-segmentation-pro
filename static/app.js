/* ═══════════════════════════════════════════════════════════════════
   Customer Segmentation Pro — Advanced JS
   Features:
     • Drag-and-drop file upload
     • Dark mode toggle with localStorage persistence
     • Animated progress bar simulation
     • 10 Chart.js charts (line, bar, scatter, radar, doughnut, polar)
     • 3D scatter via CSS transform simulation
     • Sortable tables
     • Colour-coded lift, churn, anomaly badges
     • Tooltip system
     • Smooth section reveal
     • Multi-format download links (CSV, Excel, JSON)
   ═══════════════════════════════════════════════════════════════════ */

"use strict";

// ── Palette ──────────────────────────────────────────────────────────────
const PALETTE = [
  "#10b981","#3b82f6","#8b5cf6","#06b6d4",
  "#f59e0b","#ef4444","#f97316","#ec4899",
  "#6b7280","#1e293b",
];
const alpha = (hex, a) => hex + Math.round(a * 255).toString(16).padStart(2,"0");

// ── State ─────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
let charts = {};
let currentData = null;

// ── Dark mode ─────────────────────────────────────────────────────────────
const setTheme = dark => {
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  $("themeToggle").textContent = dark ? "☀️" : "🌙";
  localStorage.setItem("theme", dark ? "dark" : "light");
  // Update existing charts
  if (currentData) setTimeout(() => renderAllCharts(currentData), 50);
};
const initTheme = () => {
  const saved = localStorage.getItem("theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  setTheme(saved ? saved === "dark" : prefersDark);
};
$("themeToggle").addEventListener("click", () => {
  setTheme(document.documentElement.getAttribute("data-theme") !== "dark");
});
initTheme();

// ── Tooltip system ────────────────────────────────────────────────────────
const popup = $("tooltipPopup");
document.querySelectorAll(".tooltip").forEach(el => {
  el.addEventListener("mouseenter", e => {
    popup.textContent = el.dataset.tip;
    popup.classList.add("show");
  });
  el.addEventListener("mousemove", e => {
    popup.style.left = (e.clientX + 12) + "px";
    popup.style.top  = (e.clientY - 28) + "px";
  });
  el.addEventListener("mouseleave", () => popup.classList.remove("show"));
});

// ── Drag-and-drop upload ──────────────────────────────────────────────────
const dropZone = $("dropZone");
const fileInput = $("file");
$("browseBtn").addEventListener("click", () => fileInput.click());
dropZone.addEventListener("click", e => { if (e.target !== $("browseBtn")) fileInput.click(); });
dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave",   () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  if (e.dataTransfer.files[0]) {
    const dt = new DataTransfer();
    dt.items.add(e.dataTransfer.files[0]);
    fileInput.files = dt.files;
    setFileName(e.dataTransfer.files[0].name);
  }
});
fileInput.addEventListener("change", e => {
  if (e.target.files[0]) setFileName(e.target.files[0].name);
});
function setFileName(name) {
  $("fileName").innerHTML = `<span class="file-name-badge">📄 ${name}</span>`;
}

// ── Form submit ───────────────────────────────────────────────────────────
$("form").addEventListener("submit", e => {
  e.preventDefault();
  if (!fileInput.files[0]) return showError("Please choose a CSV or Excel file, or use 'Run Demo'.");
  send("/api/analyze", new FormData($("form")));
});
$("demo").addEventListener("click", () => {
  const fd = new FormData($("form"));
  fd.delete("file");
  send("/api/demo", fd);
});

function showError(msg) {
  $("error").textContent = msg;
  $("error").hidden = !msg;
}

// ── Progress animation ────────────────────────────────────────────────────
let progressTimer;
function startProgress() {
  const bar = $("progressFill");
  let pct = 0;
  bar.style.width = "0%";
  $("statusBar").hidden = false;
  clearInterval(progressTimer);
  progressTimer = setInterval(() => {
    pct = pct < 85 ? pct + (Math.random() * 4) : pct + 0.3;
    bar.style.width = Math.min(pct, 90) + "%";
  }, 200);
}
function endProgress() {
  clearInterval(progressTimer);
  $("progressFill").style.width = "100%";
  setTimeout(() => { $("statusBar").hidden = true; }, 800);
}

// ── Send request ──────────────────────────────────────────────────────────
async function send(url, body) {
  showError("");
  document.querySelectorAll(".btn").forEach(b => b.disabled = true);
  $("status").textContent = "🔄 Running ML pipeline…";
  startProgress();
  try {
    const res  = await fetch(url, { method: "POST", body });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed");
    currentData = data;
    renderAllCharts(data);
    endProgress();
    $("status").textContent = "✅ Analysis complete";
    $("results").hidden = false;
    setTimeout(() => $("results").scrollIntoView({ behavior: "smooth" }), 100);
  } catch (err) {
    endProgress();
    showError(err.message);
    $("status").textContent = "";
  } finally {
    document.querySelectorAll(".btn").forEach(b => b.disabled = false);
  }
}

// ── Chart helpers ─────────────────────────────────────────────────────────
function mk(id, config) {
  if (charts[id]) charts[id].destroy();
  const ctx = $(id);
  if (!ctx) return;
  charts[id] = new Chart(ctx, config);
}
const isDark = () => document.documentElement.getAttribute("data-theme") === "dark";
const gridColor  = () => isDark() ? "rgba(255,255,255,.08)" : "rgba(0,0,0,.07)";
const labelColor = () => isDark() ? "#94a3b8" : "#64748b";
const baseOpts   = (title) => ({
  maintainAspectRatio: false,
  plugins: {
    title: { display: !!title, text: title, color: labelColor(), font: { size: 13.5, weight: "600" } },
    legend: { labels: { color: labelColor() } },
  },
  scales: {
    x: { grid: { color: gridColor() }, ticks: { color: labelColor() } },
    y: { grid: { color: gridColor() }, ticks: { color: labelColor() }, beginAtZero: true },
  },
});

// ── Main render ───────────────────────────────────────────────────────────
function renderAllCharts(d) {
  renderKPIs(d);
  renderRevenueTrend(d);
  renderCohort(d);
  renderKSelectionCharts(d);
  renderScatterCharts(d);
  renderSegmentCards(d);
  renderProfileTable(d);
  renderCLVChart(d);
  renderChurnChart(d);
  renderTopProducts(d);
  renderRulesTabs(d);
  renderAnomalySection(d);
  renderInsights(d);
  setDownloadLinks(d);
  initLookup(d.download_id);   // enable customer lookup
}

// ── KPIs ──────────────────────────────────────────────────────────────────
function renderKPIs(d) {
  const s = d.summary;
  const fmtRevenue = v => v >= 1e6 ? `$${(v/1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v/1e3).toFixed(0)}K` : `$${v}`;
  const kps = [
    [s.customers,                      "Customers"],
    [s.invoices,                        "Invoices"],
    [s.products,                        "Products"],
    [fmtRevenue(s.total_revenue),       "Total Revenue"],
    [s.chosen_k,                        "Segments (k)"],
    [s.silhouette,                      "Silhouette ↑"],
    [s.davies_bouldin,                  "Davies-Bouldin ↓"],
    [`${(s.pca_variance*100).toFixed(1)}%`, "PCA Variance"],
    [fmtRevenue(s.avg_clv_12m),         "Avg CLV 12M"],
    [s.anomalies,                       "Anomalies 🚨"],
  ];
  $("kpis").innerHTML = kps.map(([v,l]) =>
    `<div class="kpi"><b>${v}</b><span>${l}</span></div>`).join("");
  $("metaRow").innerHTML =
    `<span>📅 Date range: <strong>${s.date_range}</strong></span>
     <span>🤖 Algorithm: <strong>${s.algorithm}</strong></span>
     <span>📐 PCA components: <strong>${s.pca_components}</strong></span>
     <span>🧹 Clean rows: <strong>${s.rows_clean.toLocaleString()} / ${s.rows_in.toLocaleString()}</strong></span>`;
}

// ── Revenue Trend ─────────────────────────────────────────────────────────
function renderRevenueTrend(d) {
  const months = d.rev_trend.map(r => r.month);
  const revs   = d.rev_trend.map(r => r.revenue);
  const gradient = (ctx) => {
    const g = ctx.createLinearGradient(0, 0, 0, 280);
    g.addColorStop(0, alpha(PALETTE[0], .5));
    g.addColorStop(1, alpha(PALETTE[0], .02));
    return g;
  };
  mk("revChart", {
    type: "line",
    data: { labels: months, datasets: [{
      label: "Monthly Revenue ($)", data: revs,
      borderColor: PALETTE[0], pointBackgroundColor: PALETTE[0],
      backgroundColor: (ctx) => gradient(ctx.chart.ctx),
      fill: true, tension: .4, pointRadius: 4,
    }]},
    options: { ...baseOpts("Monthly Revenue Trend"), scales: {
      x: { grid: { color: gridColor() }, ticks: { color: labelColor(), maxTicksLimit: 8 } },
      y: { grid: { color: gridColor() }, ticks: { color: labelColor(), callback: v => "$" + v.toLocaleString() } },
    }},
  });
}

// ── Cohort Chart ──────────────────────────────────────────────────────────
function renderCohort(d) {
  const months = d.cohort_data.map(r => r.month);
  const counts = d.cohort_data.map(r => r.new_customers);
  mk("cohortChart", {
    type: "bar",
    data: { labels: months, datasets: [{
      label: "New Customers", data: counts,
      backgroundColor: alpha(PALETTE[1], .75), borderColor: PALETTE[1], borderWidth: 1.5, borderRadius: 5,
    }]},
    options: baseOpts("New Customer Cohorts (Monthly)"),
  });
}

// ── K-Selection Charts ────────────────────────────────────────────────────
function renderKSelectionCharts(d) {
  const ks = d.k_metrics.map(m => "k=" + m.k);
  mk("kChart", {
    type: "line",
    data: { labels: ks, datasets: [
      { label: "Silhouette ↑", data: d.k_metrics.map(m => m.silhouette),
        borderColor: PALETTE[0], backgroundColor: alpha(PALETTE[0], .15), tension: .3, fill: true },
      { label: "Davies-Bouldin ↓", data: d.k_metrics.map(m => m.davies_bouldin),
        borderColor: PALETTE[4], backgroundColor: alpha(PALETTE[4], .15), tension: .3, fill: true },
    ]},
    options: baseOpts("Cluster Quality vs k"),
  });
  mk("elbowChart", {
    type: "line",
    data: { labels: ks, datasets: [{
      label: "Inertia (Elbow method)", data: d.k_metrics.map(m => m.inertia),
      borderColor: PALETTE[1], backgroundColor: alpha(PALETTE[1], .12), tension: .3, fill: true,
    }]},
    options: baseOpts("Elbow — look for the bend"),
  });
}

// ── Scatter Charts ────────────────────────────────────────────────────────
function renderScatterCharts(d) {
  const names = d.profiles.map(p => p.segment);
  // 2D scatter
  mk("pcaChart", {
    type: "scatter",
    data: { datasets: names.map((n, i) => ({
      label: n, pointRadius: 3,
      data: (d.scatter2d[n] || []).map(([x,y]) => ({ x, y })),
      backgroundColor: alpha(d.profiles[i].color, .65),
    }))},
    options: { ...baseOpts("PCA Space (PC1 vs PC2)"), scales: {
      x: { title: { display: true, text: "PC1", color: labelColor() }, grid: { color: gridColor() }, ticks: { color: labelColor() } },
      y: { title: { display: true, text: "PC2", color: labelColor() }, grid: { color: gridColor() }, ticks: { color: labelColor() } },
    }},
  });

  // Size/Revenue comparison
  mk("sizeChart", {
    type: "bar",
    data: { labels: names, datasets: [
      { label: "% of Customers", data: d.profiles.map(p => p.share),
        backgroundColor: d.profiles.map(p => alpha(p.color, .75)), borderRadius: 4 },
      { label: "% of Revenue",   data: d.profiles.map(p => p.revenue_share),
        backgroundColor: d.profiles.map(p => alpha(p.color, .4)),
        borderColor: d.profiles.map(p => p.color), borderWidth: 2, borderRadius: 4 },
    ]},
    options: { ...baseOpts("Customer Share vs Revenue Share"),
      scales: { x: { grid: { color: gridColor() }, ticks: { color: labelColor() } },
                y: { grid: { color: gridColor() }, ticks: { color: labelColor(), callback: v => v + "%" } } } },
  });

  // 3D scatter tab handler
  document.querySelectorAll(".stab").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll(".stab").forEach(t => t.classList.remove("on"));
    b.classList.add("on");
    const is3d = b.dataset.view === "3d";
    $("scatter2dBox").hidden =  is3d;
    $("scatter3dBox").hidden = !is3d;
    if (is3d) render3DScatter(d);
  }));
}

function render3DScatter(d) {
  const names = d.profiles.map(p => p.segment);
  // Simulate 3D via bubble chart (PC1 × PC2, size = PC3)
  mk("pca3dChart", {
    type: "bubble",
    data: { datasets: names.map((n, i) => ({
      label: n,
      data: (d.scatter3d[n] || []).slice(0, 400).map(([x, y, z]) => ({
        x, y, r: Math.max(2, Math.abs(z) * 5 + 2),
      })),
      backgroundColor: alpha(d.profiles[i].color, .5),
      borderColor: d.profiles[i].color, borderWidth: 1,
    }))},
    options: { ...baseOpts("3D PCA View (PC1 × PC2, size = |PC3|)"), scales: {
      x: { title: { display: true, text: "PC1", color: labelColor() }, grid: { color: gridColor() }, ticks: { color: labelColor() } },
      y: { title: { display: true, text: "PC2", color: labelColor() }, grid: { color: gridColor() }, ticks: { color: labelColor() } },
    }},
  });
}

// ── Segment Cards ─────────────────────────────────────────────────────────
function renderSegmentCards(d) {
  $("segmentCards").innerHTML = d.profiles.map(p => `
    <div class="seg-card" style="border-left-color:${p.color}">
      <div class="seg-name">
        <span class="dot" style="background:${p.color}"></span>${p.segment}
        <span style="margin-left:auto;font-size:12px;color:var(--ink-muted)">${p.share}%</span>
      </div>
      <div class="seg-stats">
        <div class="seg-stat"><strong>${p.customers}</strong>Customers</div>
        <div class="seg-stat"><strong>${p.revenue_share}%</strong>Revenue</div>
        <div class="seg-stat"><strong>$${p.clv_12m.toLocaleString()}</strong>CLV 12M</div>
        <div class="seg-stat"><strong>${churnBadgeText(p.churn_risk)}</strong>Churn Risk</div>
        <div class="seg-stat"><strong>${p.recency}d</strong>Recency</div>
        <div class="seg-stat"><strong>${p.frequency}</strong>Orders</div>
      </div>
      <div class="seg-action">💡 ${p.action}</div>
    </div>`).join("");
}

// ── Profile Table ─────────────────────────────────────────────────────────
function renderProfileTable(d) {
  const headers = ["Segment","Customers","Recency","Orders","Avg Basket","CLV 12M","Churn Risk","Revenue %","CLV %","Anomalies %","Suggested Action"];
  $("profile").innerHTML = `<tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr>` +
    d.profiles.map((p, i) => `<tr>
      <td><span class="dot" style="background:${p.color}"></span><b>${p.segment}</b></td>
      <td>${p.customers} (${p.share}%)</td>
      <td>${p.recency}d</td>
      <td>${p.frequency}</td>
      <td>$${p.avg_basket}</td>
      <td>$${p.clv_12m.toLocaleString()}</td>
      <td>${churnBadge(p.churn_risk)}</td>
      <td>${p.revenue_share}%</td>
      <td>${p.clv_share}%</td>
      <td>${p.anomaly_pct}%</td>
      <td>${p.action}</td></tr>`).join("");
}

function churnBadge(v) {
  const cls = v >= 70 ? "churn-high" : v >= 40 ? "churn-mid" : "churn-low";
  return `<span class="${cls}">${v}%</span>`;
}
function churnBadgeText(v) {
  return v >= 70 ? `🔴 ${v}%` : v >= 40 ? `🟡 ${v}%` : `🟢 ${v}%`;
}

// ── CLV Bar Chart ─────────────────────────────────────────────────────────
function renderCLVChart(d) {
  mk("clvChart", {
    type: "bar",
    data: {
      labels: d.profiles.map(p => p.segment),
      datasets: [{
        label: "Avg 12-Month CLV ($)", data: d.profiles.map(p => p.clv_12m),
        backgroundColor: d.profiles.map(p => alpha(p.color, .7)),
        borderColor: d.profiles.map(p => p.color), borderWidth: 2, borderRadius: 6,
      }],
    },
    options: { ...baseOpts("12-Month CLV Forecast per Segment"),
      scales: { x: { grid: { color: gridColor() }, ticks: { color: labelColor() } },
                y: { grid: { color: gridColor() }, ticks: { color: labelColor(), callback: v => "$" + v.toLocaleString() } } },
    },
  });
}

// ── Churn Risk Polar Area ─────────────────────────────────────────────────
function renderChurnChart(d) {
  mk("churnChart", {
    type: "polarArea",
    data: {
      labels: d.profiles.map(p => p.segment),
      datasets: [{
        label: "Churn Risk (%)",
        data: d.profiles.map(p => p.churn_risk),
        backgroundColor: d.profiles.map(p => alpha(p.color, .6)),
        borderColor: d.profiles.map(p => p.color), borderWidth: 1.5,
      }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: "Churn Risk Score by Segment (%)", color: labelColor(), font: { size: 13.5, weight: "600" } },
        legend: { labels: { color: labelColor() } },
      },
      scales: { r: { ticks: { color: labelColor() }, grid: { color: gridColor() } } },
    },
  });
}

// ── Top Products Horizontal Bar ───────────────────────────────────────────
function renderTopProducts(d) {
  const sorted = [...d.top_products].sort((a, b) => a.revenue - b.revenue);
  mk("topProdChart", {
    type: "bar",
    data: {
      labels: sorted.map(p => p.product.length > 30 ? p.product.slice(0, 28) + "…" : p.product),
      datasets: [{
        label: "Revenue ($)",
        data: sorted.map(p => p.revenue),
        backgroundColor: sorted.map((_, i) => alpha(PALETTE[i % PALETTE.length], .7)),
        borderColor:      sorted.map((_, i) => PALETTE[i % PALETTE.length]),
        borderWidth: 1.5, borderRadius: 4,
      }],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: "Top 15 Products by Revenue", color: labelColor(), font: { size: 13.5, weight: "600" } },
        legend: { display: false },
      },
      scales: {
        x: { grid: { color: gridColor() }, ticks: { color: labelColor(), callback: v => "$" + v.toLocaleString() } },
        y: { grid: { color: gridColor() }, ticks: { color: labelColor(), font: { size: 11 } } },
      },
    },
  });
}

// ── Rules Tabs ────────────────────────────────────────────────────────────
function renderRulesTabs(d) {
  const keys = Object.keys(d.rules);
  $("tabs").innerHTML = keys.map((k, i) =>
    `<button class="tab ${i === 0 ? "on" : ""}" data-k="${k}">${k}</button>`).join("");
  const showRules = key => {
    const r = d.rules[key];
    $("rules").innerHTML = r.length
      ? `<tr><th>Rule (if A → then B)</th><th>Support</th><th>Confidence</th><th>Lift</th><th>Leverage</th><th>Conviction</th></tr>` +
        r.map(x => {
          const liftCls = x.lift >= 2 ? "lift-high" : x.lift >= 1.5 ? "lift-mid" : "lift-low";
          return `<tr><td>${x.rule}</td><td>${x.support}</td><td>${x.confidence}</td>
            <td><span class="lift-badge ${liftCls}">${x.lift}</span></td>
            <td>${x.leverage}</td><td>${x.conviction}</td></tr>`;
        }).join("")
      : `<tr><td colspan="6" style="color:var(--ink-muted)">No rules met the thresholds. Try lowering min support, confidence, or lift.</td></tr>`;
  };
  document.querySelectorAll(".tab").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("on"));
    b.classList.add("on");
    showRules(b.dataset.k);
  }));
  showRules(keys[0]);
}

// ── Anomaly Section ───────────────────────────────────────────────────────
function renderAnomalySection(d) {
  const s = d.summary;
  $("anomalyKpis").innerHTML = [
    [s.anomalies, "Anomalous Customers 🚨"],
    [`${((s.anomalies / s.customers) * 100).toFixed(1)}%`, "Of Customer Base"],
    [d.profiles.reduce((mx, p) => p.anomaly_pct > mx.anomaly_pct ? p : mx).segment, "Highest Anomaly Segment"],
  ].map(([v, l]) => `<div class="kpi"><b>${v}</b><span>${l}</span></div>`).join("");

  // Anomaly ratio per segment doughnut
  mk("anomalyChart", {
    type: "doughnut",
    data: {
      labels: d.profiles.map(p => `${p.segment} (${p.anomaly_pct}%)`),
      datasets: [{
        data: d.profiles.map(p => p.anomaly_pct || 0.01),
        backgroundColor: d.profiles.map(p => alpha(p.color, .75)),
        borderColor: d.profiles.map(p => p.color), borderWidth: 2,
      }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: "Anomaly % per Segment", color: labelColor(), font: { size: 13.5, weight: "600" } },
        legend: { labels: { color: labelColor() } },
      },
    },
  });
}

// ── Insights ──────────────────────────────────────────────────────────────
function renderInsights(d) {
  $("insights").innerHTML = d.insights.map(t => `<li>${t}</li>`).join("");
}

// ── Download links ────────────────────────────────────────────────────────
function setDownloadLinks(d) {
  const rid = d.download_id;
  $("dlCsv").href   = `/api/download/${rid}`;
  $("dlExcel").href = `/api/download/${rid}/excel`;
  $("dlJson").href  = `/api/download/${rid}/json`;
}

// ══════════════════════════════════════════════════════════════════════════
// CUSTOMER LOOKUP
// ══════════════════════════════════════════════════════════════════════════
let currentRid       = null;
let allCustomerIds   = [];

function initLookup(rid) {
  currentRid = rid;
  // Populate datalist for autocomplete
  fetch(`/api/customers/${rid}`)
    .then(r => r.json())
    .then(data => {
      allCustomerIds = data.customers || [];
      const dl = $("customerList");
      dl.innerHTML = allCustomerIds.slice(0, 200)
        .map(id => `<option value="${id}"></option>`).join("");
    }).catch(() => {});
}

$("lookupBtn").addEventListener("click", doLookup);
$("lookupInput").addEventListener("keydown", e => { if (e.key === "Enter") doLookup(); });
$("lookupRandom").addEventListener("click", () => {
  if (!allCustomerIds.length) return;
  const rid = allCustomerIds[Math.floor(Math.random() * allCustomerIds.length)];
  $("lookupInput").value = rid;
  doLookup();
});

async function doLookup() {
  const cid = $("lookupInput").value.trim();
  if (!cid) { showLookupError("Please enter a Customer ID."); return; }
  if (!currentRid) { showLookupError("Run the analysis first to enable customer lookup."); return; }

  $("lookupError").hidden = true;
  $("lookupResult").hidden = true;
  $("lookupBtn").disabled = true;
  $("lookupBtn").textContent = "🔍 Searching…";

  try {
    const res  = await fetch(`/api/lookup/${currentRid}/${encodeURIComponent(cid)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Not found");
    renderProfileCard(data);
    $("lookupResult").hidden = false;
    $("lookupResult").scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    showLookupError(err.message);
  } finally {
    $("lookupBtn").disabled = false;
    $("lookupBtn").innerHTML = `<span class="btn-icon">🔍</span> Search`;
  }
}

function showLookupError(msg) {
  $("lookupError").textContent = msg;
  $("lookupError").hidden = false;
}

function renderProfileCard(c) {
  const color  = c.color || "#13a89e";
  const churnColor = c.churn_risk >= 70 ? "#ef4444" : c.churn_risk >= 40 ? "#f97316" : "#10b981";
  const revPct = c.revenue_percentile;
  const revLabel = revPct >= 80 ? "🏆 Top 20%" : revPct >= 50 ? "📊 Above Average" : "📉 Below Average";

  $("profileCard").innerHTML = `
    <!-- Banner -->
    <div class="profile-banner" style="background: linear-gradient(135deg, ${color}dd, ${color}88)">
      <div class="profile-avatar">👤</div>
      <div class="profile-banner-info">
        <h3>Customer #${c.customer_id}</h3>
        <span>Rank ${c.segment_rank} of ${c.total_segments} segments · ${revLabel}</span>
      </div>
      <div class="profile-badge">${c.segment}</div>
    </div>

    <!-- Stats Grid -->
    <div class="profile-body">
      <div class="profile-stats">
        <div class="pstat" style="--bar-color:${color}">
          <b>${c.recency}d</b><span>Recency</span>
        </div>
        <div class="pstat">
          <b>${c.frequency}</b><span>Total Orders</span>
        </div>
        <div class="pstat">
          <b>$${c.monetary.toLocaleString()}</b><span>Total Spent</span>
        </div>
        <div class="pstat">
          <b>$${c.avg_basket}</b><span>Avg Basket</span>
        </div>
        <div class="pstat">
          <b>${c.num_products}</b><span>Unique Products</span>
        </div>
        <div class="pstat">
          <b>${c.tenure}d</b><span>Tenure</span>
        </div>
        <div class="pstat">
          <b style="color: #3b82f6">$${c.clv_12m.toLocaleString()}</b><span>CLV 12-Month</span>
        </div>
        <div class="pstat">
          <b style="color:${churnColor}">${c.churn_risk}%</b><span>Churn Risk</span>
        </div>
      </div>

      <!-- Flags -->
      <div class="profile-flags">
        <div class="pflag">⚠️ Anomaly: <strong>&nbsp;${c.anomaly}</strong></div>
        <div class="pflag">📉 Churn: <strong>&nbsp;${c.churn_label}</strong></div>
        <div class="pflag">📦 Orders/30d: <strong>&nbsp;${c.velocity}</strong></div>
        <div class="pflag">📈 Revenue Percentile: <strong>&nbsp;${c.revenue_percentile}%</strong></div>
      </div>

      <!-- Action -->
      <div class="profile-action">
        <div class="action-title">🎯 Recommended Action for ${c.segment}</div>
        <p>${c.action}</p>
      </div>

      <!-- Top Rule -->
      <div class="profile-rule">
        🧺 <strong>Top product rule for this segment:</strong> ${c.top_rule}
      </div>
    </div>
  `;
}
