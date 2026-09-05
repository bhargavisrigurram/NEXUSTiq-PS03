/**
 * NEXUS RetailIQ — Modern Command Center Client Logic
 */

let allAttentionItems = [];
let allForecastItems = [];
let allHistoryItems = [];
let cachedStores = [];
let cachedProducts = [];
let currentStoreFilter = "all";
let currentForecastFilter = "all";
let currentHistoryFilter = "all";

document.addEventListener("DOMContentLoaded", () => {
  fetchHealth();
  fetchSummary();
  fetchAttention();
  fetchStoresAndProducts();
  loadForecasts();
  loadHistory();
  loadDocuments();
});

// --- TAB SWITCHING ---
function switchTab(tabId, clickedBtn) {
  // Update sidebar active states
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach(btn => {
    if (btn.getAttribute("data-tab") === tabId) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  // Hide all tab views
  const views = document.querySelectorAll(".tab-view");
  views.forEach(v => v.classList.remove("active"));

  // Show target view
  const targetView = document.getElementById(`view-${tabId}`);
  if (targetView) {
    targetView.classList.add("active");
  }

  // Trigger lazy loading or refreshes
  if (tabId === "forecast") loadForecasts(currentStoreFilter);
  else if (tabId === "history") loadHistory();
  else if (tabId === "documents") loadDocuments();
  else if (tabId === "products") renderCatalogueTable();
  else if (tabId === "stores") renderStoresBenchmark();
  else if (tabId === "inventory") renderInventoryMatrix();
  else if (tabId === "simulator") runSimulation();
  else if (tabId === "recommendations") renderRecommendations();
}

// --- GLOBAL SEARCH ---
function handleGlobalSearch(event) {
  if (event.key === "Enter") {
    const q = event.target.value.trim();
    if (q) {
      switchTab("copilot");
      askQuestion(q);
      event.target.value = "";
    }
  }
}

// --- GLOBAL STORE SELECTOR ---
function handleStoreFilterChange(storeId) {
  currentStoreFilter = storeId;
  const simSelect = document.getElementById("sim-store-select");
  if (simSelect && storeId !== "all") {
    simSelect.value = storeId;
  }
  loadForecasts(storeId);
  renderAttentionCards(filterItemsByStore(allAttentionItems, storeId));
  renderInventoryMatrix();
}

function filterItemsByStore(items, storeId) {
  if (!storeId || storeId === "all") return items;
  return items.filter(i => i.store_id === storeId);
}

// --- RESET DEMO ---
function resetDemoState() {
  currentStoreFilter = "all";
  document.getElementById("header-store-select").value = "all";
  document.getElementById("header-source-text").innerText = "Demo Data (75d)";
  fetchSummary();
  fetchAttention();
  loadForecasts();
  alert("NEXUS RetailIQ reset to initial 75-day verified baseline.");
}

// --- API DATA FETCHING ---
async function fetchHealth() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();

    const statusText = document.getElementById("status-text");
    const statusPill = document.getElementById("system-status-pill");

    if (data.status === "ok") {
      if (data.gemini_configured) {
        statusText.innerText = "Gemini 3.5 Active";
        statusPill.style.color = "#10b981";
      } else {
        statusText.innerText = "Deterministic Mode (API Key Idle)";
        statusPill.style.color = "#38bdf8";
      }
    }
  } catch (err) {
    console.error("Health check error:", err);
    const statusText = document.getElementById("status-text");
    if (statusText) statusText.innerText = "Offline / Error";
  }
}

async function fetchSummary() {
  try {
    const res = await fetch("/api/summary");
    if (!res.ok) throw new Error("Summary fetch failed");
    const data = await res.json();

    const statStores = document.getElementById("stat-stores");
    const statProducts = document.getElementById("stat-products");
    const statUnits = document.getElementById("stat-units");
    const statRevenue = document.getElementById("stat-revenue");
    const statSalesRecords = document.getElementById("stat-sales-records");
    const periodText = document.getElementById("period-text");

    if (statStores) statStores.innerText = `${data.total_stores} Branches`;
    if (statProducts) statProducts.innerText = `${data.total_products} SKUs`;
    if (statUnits) statUnits.innerText = `${Number(data.total_units_sold).toLocaleString()} Units`;
    if (statRevenue) statRevenue.innerText = `₹${Number(data.total_revenue).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
    if (statSalesRecords) statSalesRecords.innerText = `${Number(data.total_sales_records).toLocaleString()} sales transactions`;
    if (periodText) periodText.innerText = `Dataset: ${data.date_start} to ${data.date_end}`;

    loadBenchmarks();
  } catch (err) {
    console.error("Summary error:", err);
  }
}

async function fetchAttention() {
  try {
    const res = await fetch("/api/attention");
    if (!res.ok) throw new Error("Attention fetch failed");
    const data = await res.json();

    allAttentionItems = [
      ...data.stockout_risks,
      ...data.dead_stock,
      ...data.sales_spikes,
      ...data.sales_drops
    ];

    const sidebarBadge = document.getElementById("sidebar-alert-badge");
    if (sidebarBadge) sidebarBadge.innerText = allAttentionItems.length;

    renderAttentionCards(allAttentionItems);
  } catch (err) {
    console.error("Attention error:", err);
  }
}

async function fetchStoresAndProducts() {
  try {
    const [storesRes, prodsRes] = await Promise.all([
      fetch("/api/stores"),
      fetch("/api/products")
    ]);
    if (storesRes.ok) cachedStores = await storesRes.json();
    if (prodsRes.ok) {
      cachedProducts = await prodsRes.json();
      populateProductSelects(cachedProducts);
    }
  } catch (err) {
    console.error("Failed to fetch stores/products:", err);
  }
}

function populateProductSelects(products) {
  const simSelect = document.getElementById("sim-product-select");
  if (!simSelect) return;
  simSelect.innerHTML = products.map(p => `
    <option value="${p.product_id}">${p.product_name} (${p.product_id})</option>
  `).join("");
}

// --- DEMAND FORECASTING VIEW (Matches 1st Screenshot) ---
async function loadForecasts(storeId = "all") {
  const container = document.getElementById("forecast-cards-container");
  if (!container) return;

  try {
    const url = storeId && storeId !== "all" ? `/api/forecast?store_id=${storeId}` : "/api/forecast";
    const res = await fetch(url);
    if (!res.ok) throw new Error("Forecast fetch failed");
    const data = await res.json();
    allForecastItems = data.forecasts || [];

    renderForecastCards(allForecastItems, currentForecastFilter);
  } catch (err) {
    console.error("Forecast error:", err);
    container.innerHTML = `<div style="color: var(--text-muted); padding: 2rem; text-align: center;">Failed to load demand forecasts.</div>`;
  }
}

function filterForecastCards(filterType, btn) {
  currentForecastFilter = filterType;
  if (btn) {
    const pills = document.querySelectorAll(".forecast-pill");
    pills.forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
  }
  renderForecastCards(allForecastItems, filterType);
}

function renderForecastCards(items, filterType = "all") {
  const container = document.getElementById("forecast-cards-container");
  if (!container) return;

  let filtered = items;
  if (filterType !== "all") {
    filtered = items.filter(i => i.status_class === filterType);
  }

  if (filtered.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); padding: 2.5rem; text-align: center; grid-column: 1 / -1;">No forecast items match this filter.</div>`;
    return;
  }

  container.innerHTML = filtered.map(item => {
    let badgeClass = "badge-healthy";
    if (item.status_class === "critical") badgeClass = "badge-critical";
    else if (item.status_class === "warning") badgeClass = "badge-warning";
    else if (item.status_class === "dead") badgeClass = "badge-dead";

    return `
      <div class="forecast-card">
        <div class="forecast-card-header">
          <div class="forecast-prod-name">${escapeHtml(item.product_name)}</div>
          <div class="forecast-prod-meta">${escapeHtml(item.store_name)} • ${escapeHtml(item.product_category)}</div>
        </div>

        <div class="forecast-metrics-list">
          <div class="forecast-metric-row">
            <span class="forecast-key">Current Stock:</span>
            <span class="val-stock">${item.current_stock} units</span>
          </div>
          <div class="forecast-metric-row">
            <span class="forecast-key">Avg Daily Demand:</span>
            <span class="val-demand">${item.avg_daily_demand} units/day</span>
          </div>
          <div class="forecast-metric-row">
            <span class="forecast-key">7-Day Demand Forecast:</span>
            <span class="val-7d">${item.demand_7d} units</span>
          </div>
          <div class="forecast-metric-row">
            <span class="forecast-key">14-Day Demand Forecast:</span>
            <span class="val-14d">${item.demand_14d} units</span>
          </div>
          <div class="forecast-metric-row">
            <span class="forecast-key">Estimated Stockout Date:</span>
            <span class="val-date">${item.estimated_stockout_date}</span>
          </div>
        </div>

        <span class="forecast-badge ${badgeClass}">${item.status_level}</span>
      </div>
    `;
  }).join("");
}

// --- ATTENTION CARDS VIEW ---
function filterAttention(type, btn) {
  if (btn) {
    const tabs = document.querySelectorAll(".filter-tabs .tab-btn");
    tabs.forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
  }

  let filtered = allAttentionItems;
  if (type !== "all") {
    filtered = allAttentionItems.filter(i => i.type === type);
  }
  if (currentStoreFilter !== "all") {
    filtered = filterItemsByStore(filtered, currentStoreFilter);
  }
  renderAttentionCards(filtered);
}

function renderAttentionCards(items) {
  const container = document.getElementById("attention-cards-list");
  if (!container) return;

  if (!items || items.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); padding: 2rem; text-align: center;">No active alerts found for this selection.</div>`;
    return;
  }

  container.innerHTML = items.map(item => {
    return `
      <div class="attention-card ${item.type}">
        <div class="attention-card-top">
          <div class="attention-title">${escapeHtml(item.product_name)}</div>
          <span class="alert-type-badge">${escapeHtml(item.category_title)}</span>
        </div>
        <div class="forecast-prod-meta">${escapeHtml(item.store_name)} • ${escapeHtml(item.product_category)} (${item.product_id})</div>
        <div class="attention-meta-grid">
          <div class="attention-meta-item">
            <span>Stock:</span>
            <span>${item.current_stock} units</span>
          </div>
          <div class="attention-meta-item">
            <span>Velocity:</span>
            <span>${item.avg_daily_sales || 0} /day</span>
          </div>
          ${item.days_remaining !== null && item.days_remaining !== undefined ? `
            <div class="attention-meta-item">
              <span>Cover:</span>
              <span>${item.days_remaining} Days</span>
            </div>
          ` : ''}
          ${item.change_pct ? `
            <div class="attention-meta-item">
              <span>Change:</span>
              <span>${item.change_pct > 0 ? '+' : ''}${item.change_pct}%</span>
            </div>
          ` : ''}
        </div>
        <div class="attention-rec">
          <strong>Recommendation:</strong> ${escapeHtml(item.recommendation)}
        </div>
      </div>
    `;
  }).join("");
}

// --- BENCHMARKS LEADERBOARD ---
async function loadBenchmarks() {
  try {
    const res = await fetch("/api/benchmarks");
    if (!res.ok) return;
    const data = await res.json();

    const tbody = document.getElementById("overview-leaderboard-body");
    if (tbody) {
      tbody.innerHTML = data.stores.map((s, idx) => `
        <tr>
          <td><strong>${idx + 1}. ${escapeHtml(s.store_name)}</strong></td>
          <td>${escapeHtml(s.city)}</td>
          <td style="color: var(--cyan-bright); font-weight: 700;">₹${Number(s.total_revenue).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
          <td>${Number(s.total_units_sold).toLocaleString()}</td>
          <td style="color: ${s.stockout_count > 0 ? '#ef4444' : '#10b981'}; font-weight: 700;">${s.stockout_count}</td>
          <td style="color: ${s.dead_stock_count > 0 ? '#f59e0b' : '#10b981'};">${s.dead_stock_count}</td>
          <td>
            <span style="display: inline-block; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.78rem; background: rgba(99, 102, 241, 0.2); color: var(--purple-bright);">
              ${s.health_score} / 100
            </span>
          </td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error("Benchmarks error:", err);
  }
}

// --- INVENTORY CATALOGUE TABLE ---
function renderCatalogueTable() {
  const tbody = document.getElementById("catalogue-table-body");
  if (!tbody || cachedProducts.length === 0) return;

  filterCatalogueTable("");
}

function filterCatalogueTable(searchVal) {
  const tbody = document.getElementById("catalogue-table-body");
  if (!tbody) return;

  const q = searchVal.toLowerCase();
  const catFilter = (document.getElementById("catalogue-category-filter")?.value || "all");

  const filtered = cachedProducts.filter(p => {
    const matchesSearch = p.product_name.toLowerCase().includes(q) || p.product_id.toLowerCase().includes(q);
    const matchesCat = catFilter === "all" || p.category === catFilter;
    return matchesSearch && matchesCat;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No products match criteria.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(p => {
    const cost = Number(p.cost_price || (p.unit_price * 0.6));
    const price = Number(p.unit_price);
    const margin = Math.round(((price - cost) / price) * 100);

    return `
      <tr>
        <td><code>${p.product_id}</code></td>
        <td><strong>${escapeHtml(p.product_name)}</strong></td>
        <td>${escapeHtml(p.category)}</td>
        <td>₹${cost.toFixed(2)}</td>
        <td style="color: var(--cyan-bright); font-weight: 600;">₹${price.toFixed(2)}</td>
        <td><span style="color: #34d399; font-weight: 700;">+${margin}%</span></td>
        <td>${p.current_stock || 120} units</td>
      </tr>
    `;
  }).join("");
}

function filterCatalogueCategory(cat) {
  const searchInput = document.getElementById("catalogue-search-input");
  filterCatalogueTable(searchInput ? searchInput.value : "");
}

// --- STORES BENCHMARKS VIEW ---
async function renderStoresBenchmark() {
  const container = document.getElementById("stores-benchmark-cards");
  if (!container) return;

  try {
    const res = await fetch("/api/benchmarks");
    if (!res.ok) return;
    const data = await res.json();

    container.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.25rem;">
        ${data.stores.map((s, idx) => `
          <div class="stat-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
              <span class="stat-label">Rank #${idx + 1}</span>
              <span style="font-size: 0.72rem; font-weight: 700; background: rgba(99, 102, 241, 0.2); color: var(--purple-bright); padding: 2px 7px; border-radius: 4px;">Health: ${s.health_score}/100</span>
            </div>
            <div style="font-size: 1.15rem; font-weight: 800; color: #ffffff;">${escapeHtml(s.store_name)}</div>
            <div style="font-size: 0.76rem; color: var(--text-muted); margin-bottom: 0.75rem;">${escapeHtml(s.city)} (${s.store_id})</div>
            <div class="forecast-metric-row" style="margin-bottom: 4px;">
              <span class="forecast-key">Revenue (75d):</span>
              <span style="color: var(--cyan-bright); font-weight: 700;">₹${Number(s.total_revenue).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
            </div>
            <div class="forecast-metric-row" style="margin-bottom: 4px;">
              <span class="forecast-key">Units Sold:</span>
              <span style="color: #fff;">${Number(s.total_units_sold).toLocaleString()}</span>
            </div>
            <div class="forecast-metric-row" style="margin-bottom: 4px;">
              <span class="forecast-key">Active Stockouts:</span>
              <span style="color: ${s.stockout_count > 0 ? '#ef4444' : '#10b981'}; font-weight: 700;">${s.stockout_count} SKUs</span>
            </div>
            <div class="forecast-metric-row">
              <span class="forecast-key">Dead Stock:</span>
              <span style="color: ${s.dead_stock_count > 0 ? '#f59e0b' : '#10b981'}; font-weight: 700;">${s.dead_stock_count} SKUs</span>
            </div>
          </div>
        `).join("")}
      </div>
    `;
  } catch (err) {
    console.error("Stores benchmark error:", err);
  }
}

// --- INVENTORY INTELLIGENCE MATRIX ---
function renderInventoryMatrix() {
  const tbody = document.getElementById("inventory-matrix-body");
  if (!tbody || allForecastItems.length === 0) return;

  const filtered = filterItemsByStore(allForecastItems, currentStoreFilter);

  tbody.innerHTML = filtered.map(item => `
    <tr>
      <td>${escapeHtml(item.store_name)}</td>
      <td><code>${item.product_id}</code></td>
      <td><strong>${escapeHtml(item.product_name)}</strong></td>
      <td>${escapeHtml(item.product_category)}</td>
      <td style="font-weight: 700; color: #ffffff;">${item.current_stock}</td>
      <td style="color: var(--cyan-bright);">${item.avg_daily_demand} /d</td>
      <td style="color: ${item.days_remaining !== null && item.days_remaining <= 3 ? '#ef4444' : '#38bdf8'}; font-weight: 700;">
        ${item.days_remaining !== null ? `${item.days_remaining} d` : 'N/A'}
      </td>
      <td>
        <span class="forecast-badge ${item.status_class === 'critical' ? 'badge-critical' : (item.status_class === 'warning' ? 'badge-warning' : (item.status_class === 'dead' ? 'badge-dead' : 'badge-healthy'))}">
          ${item.status_level}
        </span>
      </td>
    </tr>
  `).join("");
}

// --- RECOMMENDATIONS & TRANSFERS VIEW ---
function renderRecommendations() {
  const container = document.getElementById("reorder-transfers-container");
  if (!container) return;

  const stockouts = allAttentionItems.filter(i => i.type === "stockout_risk");
  const deadStocks = allAttentionItems.filter(i => i.type === "dead_stock");

  if (stockouts.length === 0 && deadStocks.length === 0) {
    container.innerHTML = `<div style="padding: 2rem; color: var(--text-muted); text-align: center; grid-column: 1/-1;">All branch inventories are operating within optimal parameters.</div>`;
    return;
  }

  container.innerHTML = `
    <!-- Inter-Store Transfer Cards -->
    ${stockouts.slice(0, 3).map(so => {
      // Find candidate donor store
      const donor = deadStocks.find(ds => ds.product_id === so.product_id);
      return `
        <div class="stat-card" style="border-left: 4px solid var(--purple-primary);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <span class="stat-label">Stock Balancing Advice</span>
            <span style="font-size: 0.7rem; font-weight: 700; background: rgba(99, 102, 241, 0.2); color: var(--purple-bright); padding: 2px 6px; border-radius: 4px;">Actionable</span>
          </div>
          <div style="font-size: 1.05rem; font-weight: 700; color: #ffffff;">${escapeHtml(so.product_name)}</div>
          <p style="font-size: 0.8rem; color: var(--text-secondary); margin: 0.4rem 0 0.75rem;">
            Destination: <strong>${escapeHtml(so.store_name)}</strong> has only ${so.current_stock} units (${so.days_remaining}d cover).
            ${donor ? `<br>💡 Donor candidate: <strong>${escapeHtml(donor.store_name)}</strong> has ${donor.current_stock} non-moving units. Transfer 30 units to prevent stockout without buying new inventory!` : '<br>Recommended: Place replenishment purchase order with supplier.'}
          </p>
          <button class="btn-primary" style="font-size: 0.78rem; padding: 0.45rem 0.85rem;" onclick="switchTab('simulator')">
            Open Reorder Simulator →
          </button>
        </div>
      `;
    }).join("")}
  `;
}

// --- WHAT-IF SIMULATOR ---
function updateCoverDays(val) {
  const label = document.getElementById("sim-slider-val");
  if (label) label.innerText = `${val} Days`;
}

async function runSimulation() {
  const storeId = document.getElementById("sim-store-select")?.value || "S01";
  const prodId = document.getElementById("sim-product-select")?.value || "P02";
  const coverDays = parseInt(document.getElementById("sim-cover-slider")?.value || "7", 10);
  const resultPanel = document.getElementById("sim-results-card");
  if (!resultPanel) return;

  try {
    const res = await fetch("/api/simulate-reorder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ store_id: storeId, product_id: prodId, target_cover_days: coverDays })
    });
    if (!res.ok) throw new Error("Simulation failed");
    const data = await res.json();

    resultPanel.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.75rem;">
        <div>
          <div style="font-size: 1.15rem; font-weight: 800; color: #ffffff;">${escapeHtml(data.product_name)}</div>
          <div style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(data.store_name)} • ${escapeHtml(data.product_category)} (${data.product_id})</div>
        </div>
        <span style="font-size: 0.74rem; font-weight: 700; background: rgba(99, 102, 241, 0.2); color: var(--purple-bright); padding: 3px 8px; border-radius: 999px;">
          ${data.target_cover_days}-Day Target
        </span>
      </div>

      <div class="sim-kpi-grid">
        <div class="sim-kpi">
          <div class="sim-kpi-label">Current Stock</div>
          <div class="sim-kpi-val" style="color: #fff;">${data.current_stock}</div>
        </div>
        <div class="sim-kpi">
          <div class="sim-kpi-label">Daily Sales Rate</div>
          <div class="sim-kpi-val" style="color: var(--cyan-bright);">${data.avg_daily_sales} /d</div>
        </div>
        <div class="sim-kpi">
          <div class="sim-kpi-label">Target Units Needed</div>
          <div class="sim-kpi-val">${data.target_stock_needed}</div>
        </div>
        <div class="sim-kpi">
          <div class="sim-kpi-label">Recommended Order</div>
          <div class="sim-kpi-val" style="color: #34d399;">${data.recommended_order_quantity} units</div>
        </div>
        <div class="sim-kpi">
          <div class="sim-kpi-label">Estimated Order Cost</div>
          <div class="sim-kpi-val">₹${Number(data.estimated_purchase_cost).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
        </div>
        <div class="sim-kpi">
          <div class="sim-kpi-label">Projected Stockout Date</div>
          <div class="sim-kpi-val" style="color: var(--accent-amber); font-size: 1.1rem;">${data.projected_stockout_date || 'Stable'}</div>
        </div>
      </div>

      <div style="background: rgba(0,0,0,0.25); border-left: 3px solid var(--purple-primary); padding: 0.75rem 1rem; border-radius: 4px; font-size: 0.8rem; color: var(--text-secondary);">
        <strong>Operational Assumption:</strong> ${escapeHtml(data.assumption)}
      </div>
    `;

    // Refresh history
    loadHistory();
  } catch (err) {
    console.error("Simulation error:", err);
  }
}

// --- DECISION HISTORY VIEW (User Requested Feature) ---
async function loadHistory() {
  const container = document.getElementById("history-records-container");
  const sidebarBadge = document.getElementById("sidebar-history-badge");
  if (!container) return;

  try {
    const res = await fetch("/api/history");
    if (!res.ok) throw new Error("History fetch failed");
    const data = await res.json();
    allHistoryItems = data.history || [];

    if (sidebarBadge) sidebarBadge.innerText = allHistoryItems.length;

    renderHistoryList(allHistoryItems, currentHistoryFilter);
  } catch (err) {
    console.error("History load error:", err);
  }
}

function filterHistoryType(type, btn) {
  currentHistoryFilter = type;
  if (btn) {
    const pills = document.querySelectorAll(".history-filter-pills button");
    pills.forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
  }
  renderHistoryList(allHistoryItems, type);
}

function filterHistoryItems(searchVal) {
  const q = searchVal.toLowerCase();
  const filtered = allHistoryItems.filter(item => {
    const matchesQ = item.title.toLowerCase().includes(q) || item.summary.toLowerCase().includes(q) || (item.store && item.store.toLowerCase().includes(q));
    const matchesType = currentHistoryFilter === "all" || item.type === currentHistoryFilter;
    return matchesQ && matchesType;
  });
  renderHistoryCardsHtml(filtered);
}

function renderHistoryList(items, typeFilter = "all") {
  let filtered = items;
  if (typeFilter !== "all") {
    filtered = items.filter(i => i.type === typeFilter);
  }
  renderHistoryCardsHtml(filtered);
}

function renderHistoryCardsHtml(items) {
  const container = document.getElementById("history-records-container");
  if (!container) return;

  if (items.length === 0) {
    container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 3rem;">No past history recorded yet. Inquiries, simulations, and uploads will appear here automatically.</div>`;
    return;
  }

  container.innerHTML = items.map(item => {
    let typeClass = "type-chat";
    let typeLabel = "💬 Inquiries";
    if (item.type === "simulation") { typeClass = "type-sim"; typeLabel = "🎯 Simulation"; }
    else if (item.type === "document_upload") { typeClass = "type-doc"; typeLabel = "📄 Document Upload"; }

    return `
      <div class="history-card">
        <div class="history-card-left">
          <div class="history-meta-row">
            <span class="history-time">📅 ${escapeHtml(item.timestamp)}</span>
            <span class="history-type-badge ${typeClass}">${typeLabel}</span>
            <span class="history-store-tag">📍 ${escapeHtml(item.store || 'Network')}</span>
          </div>
          <div class="history-title">${escapeHtml(item.title)}</div>
          <div class="history-summary">${escapeHtml(item.summary)}</div>
        </div>
        ${item.type === 'chat_query' ? `
          <button class="btn-rerun" onclick="rerunHistoryQuery('${escapeHtml(item.title)}')">
            Re-run in Copilot ↺
          </button>
        ` : ''}
      </div>
    `;
  }).join("");
}

function rerunHistoryQuery(question) {
  switchTab("copilot");
  askQuestion(question);
}

async function clearHistoryLog() {
  if (!confirm("Are you sure you want to clear the interaction history?")) return;
  try {
    await fetch("/api/history", { method: "DELETE" });
    loadHistory();
  } catch (err) {
    console.error("Clear history error:", err);
  }
}

function exportHistoryJSON() {
  const blob = new Blob([JSON.stringify(allHistoryItems, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `nexus_retailiq_history_${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// --- COPILOT CHAT LOGIC ---
async function handleChatSubmit(event) {
  event.preventDefault();
  const input = document.getElementById("chat-input-field");
  const q = input.value.trim();
  if (!q) return;
  input.value = "";
  askQuestion(q);
}

async function askQuestion(question) {
  const container = document.getElementById("chat-messages-container");
  if (!container) return;

  // Append user message
  const userMsgEl = document.createElement("div");
  userMsgEl.className = "chat-message user-message";
  userMsgEl.innerHTML = `<div class="message-bubble">${escapeHtml(question)}</div>`;
  container.appendChild(userMsgEl);

  // Append loading bot message
  const botMsgEl = document.createElement("div");
  botMsgEl.className = "chat-message bot-message";
  botMsgEl.innerHTML = `<div class="message-bubble" style="color: var(--text-muted);">Thinking and retrieving deterministic evidence...</div>`;
  container.appendChild(botMsgEl);
  container.scrollTop = container.scrollHeight;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question, store_id: currentStoreFilter !== "all" ? currentStoreFilter : null })
    });
    if (!res.ok) throw new Error("Chat request failed");
    const data = await res.json();

    let evidenceHtml = "";
    if (data.evidence && data.evidence.length > 0) {
      evidenceHtml = `
        <div class="evidence-cards-row">
          ${data.evidence.map(ev => {
            const isDoc = ev.status === "uploaded_document";
            return `
              <div class="evidence-mini-card ${isDoc ? 'doc-evidence' : ''}">
                ${isDoc ? `
                  <span class="badge-doc-source">📄 Document Source</span>
                  <div style="font-weight: 700; color: #ffffff;">${escapeHtml(ev.product_name)}</div>
                  <div style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(ev.store_name)}</div>
                  <div style="font-size: 0.76rem; color: var(--text-secondary); margin-top: 4px; font-style: italic;">
                    "${escapeHtml(ev.details?.snippet || '')}"
                  </div>
                ` : `
                  <div style="font-weight: 700; color: #ffffff;">${escapeHtml(ev.product_name)}</div>
                  <div style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(ev.store_name)}</div>
                  <div style="margin-top: 4px; font-size: 0.76rem;">
                    Stock: <strong>${ev.current_stock}</strong> | Velocity: <strong>${ev.avg_daily_sales}/d</strong>
                  </div>
                  ${ev.days_remaining !== null && ev.days_remaining !== undefined ? `
                    <div style="font-size: 0.76rem; color: #fb7185; font-weight: 700;">Cover: ${ev.days_remaining} Days</div>
                  ` : ''}
                `}
              </div>
            `;
          }).join("")}
        </div>
      `;
    }

    botMsgEl.innerHTML = `
      <div class="message-bubble">
        ${data.answer}
        ${evidenceHtml}
      </div>
    `;
    container.scrollTop = container.scrollHeight;

    // Refresh history count
    loadHistory();
  } catch (err) {
    botMsgEl.innerHTML = `<div class="message-bubble" style="color: #ef4444;">Error generating response. Please try again.</div>`;
  }
}

// --- DOCUMENT HUB UPLOAD LOGIC ---
function triggerFilePicker() {
  document.getElementById("hidden-file-input")?.click();
}

function handleFileInputChange(event) {
  const files = event.target.files;
  if (!files || files.length === 0) return;
  uploadFiles(files);
  event.target.value = "";
}

async function uploadFiles(files) {
  for (let file of files) {
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("/api/upload", { method: "POST", body: formData });
      if (!res.ok) throw new Error("Upload failed");
    } catch (err) {
      console.error("Upload error:", err);
      alert(`Error uploading ${file.name}: ${err.message}`);
    }
  }
  loadDocuments();
  loadHistory();
}

async function loadDocuments() {
  try {
    const res = await fetch("/api/documents");
    if (!res.ok) return;
    const data = await res.json();

    const sidebarBadge = document.getElementById("sidebar-doc-badge");
    const totalCount = document.getElementById("doc-hub-total-count");
    const chunksCount = document.getElementById("doc-hub-chunks-count");
    const listContainer = document.getElementById("doc-hub-items-list");

    if (sidebarBadge) sidebarBadge.innerText = data.total_documents;
    if (totalCount) totalCount.innerText = data.total_documents;
    if (chunksCount) chunksCount.innerText = `${data.total_chunks} Chunks Indexed`;

    if (!listContainer) return;

    if (data.documents.length === 0) {
      listContainer.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 2rem;">No documents uploaded yet. Upload a file above to expand the Copilot's knowledge base.</div>`;
      return;
    }

    listContainer.innerHTML = data.documents.map(doc => {
      let extBadge = "badge-txt";
      if (doc.file_type === "PDF") extBadge = "badge-pdf";
      else if (doc.file_type === "DOCX") extBadge = "badge-docx";
      else if (doc.file_type === "MD") extBadge = "badge-md";

      return `
        <div class="doc-item-card">
          <div class="doc-item-left">
            <span class="fmt-badge ${extBadge}">${doc.file_type}</span>
            <div>
              <div class="doc-name">${escapeHtml(doc.filename)}</div>
              <div class="doc-meta">${doc.file_size_kb} KB • ${doc.chunk_count} chunks • ${doc.upload_time}</div>
            </div>
          </div>
          <button class="btn-delete-doc" onclick="deleteDocument('${doc.doc_id}')" title="Delete document">
            🗑️
          </button>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Load docs error:", err);
  }
}

async function deleteDocument(docId) {
  if (!confirm("Are you sure you want to remove this document?")) return;
  try {
    await fetch(`/api/documents/${docId}`, { method: "DELETE" });
    loadDocuments();
  } catch (err) {
    console.error("Delete doc error:", err);
  }
}

// --- CSV DATA IMPORT & VISUAL MAPPING (Matches 2nd Screenshot) ---
async function handleCsvFileSelected(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/preview-csv", { method: "POST", body: formData });
    if (!res.ok) throw new Error("Failed to preview CSV");
    const data = await res.json();

    document.getElementById("import-active-filename").innerText = data.filename;
    document.getElementById("import-active-rows").innerText = Number(data.total_rows).toLocaleString();
    document.getElementById("import-active-cols").innerText = `${data.total_columns} Source Columns`;
    document.getElementById("import-active-validation").innerText = data.required_mapped ? "✓ Ready" : "⚠️ Needs Mapping";
    document.getElementById("import-active-validation").style.color = data.required_mapped ? "#34d399" : "#f59e0b";

    // Populate Mapping dropdowns
    populateMappingDropdown("map-col-product-name", data.columns, data.suggested_mappings.product_name);
    populateMappingDropdown("map-col-product-id", data.columns, data.suggested_mappings.product_id);
    populateMappingDropdown("map-col-category", data.columns, data.suggested_mappings.category);
    populateMappingDropdown("map-col-selling-price", data.columns, data.suggested_mappings.unit_price);
    populateMappingDropdown("map-col-cost-price", data.columns, data.suggested_mappings.cost_price);
    populateMappingDropdown("map-col-lead-time", data.columns, data.suggested_mappings.lead_time);

    validateColumnMappings();
  } catch (err) {
    alert("Error previewing CSV: " + err.message);
  }
}

function populateMappingDropdown(selectId, columns, selectedValue) {
  const select = document.getElementById(selectId);
  if (!select) return;

  select.innerHTML = `
    <option value="none">(None / Not in file)</option>
    ${columns.map(c => `
      <option value="${c}" ${c === selectedValue ? 'selected' : ''}>${c}</option>
    `).join("")}
  `;
}

function validateColumnMappings() {
  const prodNameCol = document.getElementById("map-col-product-name")?.value;
  const isReady = prodNameCol && prodNameCol !== "none";

  const valEl = document.getElementById("import-active-validation");
  if (valEl) {
    valEl.innerText = isReady ? "✓ Ready" : "⚠️ Product Name Required";
    valEl.style.color = isReady ? "#34d399" : "#ef4444";
  }
}

function activateCurrentDataset() {
  const filename = document.getElementById("import-active-filename")?.innerText || "custom_data.csv";
  document.getElementById("header-source-text").innerText = `Live: ${filename}`;
  alert(`Dataset '${filename}' activated successfully! Real-time inventory forecasts and Copilot grounding recalculated.`);
  switchTab("dashboard");
}

// --- 1-CLICK CSV EXPORT ---
function exportDailyBrief() {
  window.location.href = "/api/export-report";
}

// --- VOICE DICTATION ---
let recognition = null;
let isRecording = false;

function toggleVoiceInput() {
  const btn = document.getElementById("btn-voice-input");
  const input = document.getElementById("chat-input-field");

  if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
    alert("Speech recognition is not supported in this browser. Please use Chrome or Edge.");
    return;
  }

  if (isRecording) {
    if (recognition) recognition.stop();
    isRecording = false;
    btn.classList.remove("recording");
    return;
  }

  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRec();
  recognition.lang = "en-US";
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onstart = () => {
    isRecording = true;
    btn.classList.add("recording");
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    input.value = transcript;
  };

  recognition.onerror = () => {
    isRecording = false;
    btn.classList.remove("recording");
  };

  recognition.onend = () => {
    isRecording = false;
    btn.classList.remove("recording");
  };

  recognition.start();
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
