/**
 * NexusTiq24 PS03 Retail Copilot Client Logic
 */

let allAttentionItems = [];
let cachedStores = [];
let cachedProducts = [];

document.addEventListener("DOMContentLoaded", () => {
  fetchHealth();
  fetchSummary();
  fetchAttention();
});

// --- API DATA FETCHING ---

async function fetchHealth() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();

    const statusPill = document.getElementById("system-status-pill");
    const statusText = document.getElementById("status-text");

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
    document.getElementById("status-text").innerText = "Offline / Error";
  }
}

async function fetchSummary() {
  try {
    const res = await fetch("/api/summary");
    if (!res.ok) throw new Error("Summary fetch failed");
    const data = await res.json();

    document.getElementById("stat-stores").innerText = `${data.total_stores} Branches`;
    document.getElementById("stat-products").innerText = `${data.total_products} SKUs`;
    document.getElementById("stat-units").innerText = `${Number(data.total_units_sold).toLocaleString()} Units`;
    document.getElementById("stat-revenue").innerText = `₹${Number(data.total_revenue).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
    document.getElementById("stat-sales-records").innerText = `${Number(data.total_sales_records).toLocaleString()} sales transactions`;
    document.getElementById("period-text").innerText = `Dataset: ${data.date_start} to ${data.date_end}`;
  } catch (err) {
    console.error("Summary error:", err);
  }
}

async function fetchAttention() {
  const container = document.getElementById("attention-cards-list");
  try {
    const res = await fetch("/api/attention");
    if (!res.ok) throw new Error("Attention fetch failed");
    const data = await res.json();

    // Flatten all items with their category
    allAttentionItems = [
      ...data.stockout_risks,
      ...data.dead_stock,
      ...data.sales_spikes,
      ...data.sales_drops
    ];

    document.getElementById("alerts-count-badge").innerText = `${allAttentionItems.length} Issues`;
    renderAttentionCards(allAttentionItems);
  } catch (err) {
    console.error("Attention error:", err);
    container.innerHTML = `<div style="color: var(--text-muted); padding: 1rem;">Failed to load attention items.</div>`;
  }
}

// --- ATTENTION CARDS RENDERING ---

function renderAttentionCards(items) {
  const container = document.getElementById("attention-cards-list");
  if (!items || items.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); padding: 1.5rem; text-align: center;">No critical alerts for this category.</div>`;
    return;
  }

  container.innerHTML = items.map(item => {
    let typeClass = item.type;
    let badgeTitle = item.category_title;
    let metricPills = "";
    let askPrompt = "";

    if (item.type === "stockout_risk") {
      metricPills = `
        <div class="metric-pill">
          <span class="metric-pill-label">Stock</span>
          <span class="metric-pill-val" style="color: #fb7185;">${item.current_stock}</span>
        </div>
        <div class="metric-pill">
          <span class="metric-pill-label">Daily Sales</span>
          <span class="metric-pill-val">${item.avg_daily_sales} /d</span>
        </div>
        <div class="metric-pill">
          <span class="metric-pill-label">Cover Remaining</span>
          <span class="metric-pill-val" style="color: #fb7185;">${item.days_remaining} Days</span>
        </div>
      `;
      askPrompt = `What is the stockout risk for ${item.product_name} in ${item.store_name}?`;
    } else if (item.type === "dead_stock") {
      metricPills = `
        <div class="metric-pill">
          <span class="metric-pill-label">Stagnant Stock</span>
          <span class="metric-pill-val" style="color: #fbbf24;">${item.current_stock} Units</span>
        </div>
        <div class="metric-pill">
          <span class="metric-pill-label">14-Day Sales</span>
          <span class="metric-pill-val" style="color: #fbbf24;">0 Units</span>
        </div>
      `;
      askPrompt = `Why is ${item.product_name} not moving in ${item.store_name}?`;
    } else if (item.type === "sales_spike") {
      metricPills = `
        <div class="metric-pill">
          <span class="metric-pill-label">Surge Growth</span>
          <span class="metric-pill-val" style="color: #38bdf8;">+${item.change_pct}%</span>
        </div>
        <div class="metric-pill">
          <span class="metric-pill-label">Recent 7d Rate</span>
          <span class="metric-pill-val">${item.recent_sales} /d</span>
        </div>
        <div class="metric-pill">
          <span class="metric-pill-label">Baseline Rate</span>
          <span class="metric-pill-val">${item.baseline_sales} /d</span>
        </div>
      `;
      askPrompt = `Tell me about the sales spike of ${item.product_name} in ${item.store_name}`;
    } else if (item.type === "sales_drop") {
      metricPills = `
        <div class="metric-pill">
          <span class="metric-pill-label">Sales Drop</span>
          <span class="metric-pill-val" style="color: #facc15;">${item.change_pct}%</span>
        </div>
        <div class="metric-pill">
          <span class="metric-pill-label">Recent 7d Rate</span>
          <span class="metric-pill-val">${item.recent_sales} /d</span>
        </div>
        <div class="metric-pill">
          <span class="metric-pill-label">Baseline Rate</span>
          <span class="metric-pill-val">${item.baseline_sales} /d</span>
        </div>
      `;
      askPrompt = `Why did sales drop for ${item.product_name} in ${item.store_name}?`;
    }

    return `
      <article class="attention-card ${typeClass}">
        <div class="card-top-row">
          <span class="card-type-tag ${typeClass}">${badgeTitle}</span>
          <span class="card-store-tag">📍 ${item.store_name}</span>
        </div>
        <h4 class="card-product-name">${item.product_name}</h4>
        <div class="card-metrics-box">
          ${metricPills}
        </div>
        <div class="card-recommendation-box">
          <strong>Recommended:</strong> ${item.recommendation}
        </div>
        <div class="card-assumption-text">
          Assumption: ${item.assumption}
        </div>
        <button class="card-action-btn" onclick="submitPrompt('${askPrompt.replace(/'/g, "\\'")}')">
          <span>💬 Ask Copilot About This</span>
        </button>
      </article>
    `;
  }).join("");
}

function filterAttention(category, btnElement) {
  // Update active tab button
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  if (btnElement) btnElement.classList.add("active");

  if (category === "all") {
    renderAttentionCards(allAttentionItems);
  } else {
    const filtered = allAttentionItems.filter(item => item.type === category);
    renderAttentionCards(filtered);
  }
}

// --- CHAT INTERFACE ---

function submitPrompt(text) {
  const input = document.getElementById("chat-input-field");
  input.value = text;
  handleChatSubmit();
}

async function handleChatSubmit(e) {
  if (e) e.preventDefault();
  const input = document.getElementById("chat-input-field");
  const query = input.value.trim();
  if (!query) return;

  const stream = document.getElementById("chat-messages-stream");
  const sendBtn = document.getElementById("btn-send-chat");

  // 1. Append User message
  appendMessage("user", query);
  input.value = "";
  input.disabled = true;
  sendBtn.disabled = true;

  // 2. Append Skeleton Loading
  const loadingId = "loading-" + Date.now();
  const loadingHtml = `
    <div class="message-bubble copilot" id="${loadingId}">
      <div class="copilot-response-card skeleton-pulse" style="min-height: 120px;">
        <div style="color: var(--text-muted); font-size: 0.85rem;">
          Evaluating deterministic data and calculating grounded response...
        </div>
      </div>
    </div>
  `;
  stream.insertAdjacentHTML("beforeend", loadingHtml);
  stream.scrollTop = stream.scrollHeight;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: query })
    });

    const data = await res.json();
    const loadingElem = document.getElementById(loadingId);
    if (loadingElem) loadingElem.remove();

    renderCopilotResponse(data);
  } catch (err) {
    console.error("Chat error:", err);
    const loadingElem = document.getElementById(loadingId);
    if (loadingElem) loadingElem.remove();

    appendMessage("copilot", "Error connecting to the backend server. Please check that app.py is running on localhost:8000.");
  } finally {
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
    stream.scrollTop = stream.scrollHeight;
  }
}

function appendMessage(sender, text) {
  const stream = document.getElementById("chat-messages-stream");
  const bubble = document.createElement("div");
  bubble.className = `message-bubble ${sender}`;

  if (sender === "user") {
    bubble.innerHTML = `<div class="bubble-body">${escapeHtml(text)}</div>`;
  } else {
    bubble.innerHTML = `
      <div class="copilot-response-card">
        <div class="copilot-answer-text">${escapeHtml(text)}</div>
      </div>
    `;
  }

  stream.appendChild(bubble);
  stream.scrollTop = stream.scrollHeight;
}

function renderCopilotResponse(resp) {
  const stream = document.getElementById("chat-messages-stream");
  const bubble = document.createElement("div");
  bubble.className = "message-bubble copilot";

  let evidenceSectionHtml = "";
  if (resp.evidence && resp.evidence.length > 0) {
    const cardsHtml = resp.evidence.map(item => `
      <div class="evidence-mini-card">
        <h4>${item.product_name}</h4>
        <div class="store-sub">📍 ${item.store_name}</div>
        <table class="evidence-table">
          <tr>
            <td>Current Stock:</td>
            <td>${item.current_stock} units</td>
          </tr>
          <tr>
            <td>Recent Sales Rate:</td>
            <td>${item.avg_daily_sales} /day</td>
          </tr>
          <tr>
            <td>Stock Cover:</td>
            <td>${item.days_remaining !== null && item.days_remaining !== undefined ? `${item.days_remaining} days` : 'N/A'}</td>
          </tr>
        </table>
      </div>
    `).join("");

    evidenceSectionHtml = `
      <div class="evidence-section">
        <div class="evidence-title">
          <span>📊</span> Grounded Data Evidence (Python Computed)
        </div>
        <div class="evidence-cards-grid">
          ${cardsHtml}
        </div>
      </div>
    `;
  }

  let recommendationHtml = "";
  if (resp.recommendation) {
    recommendationHtml = `
      <div class="copilot-action-callout">
        <div class="callout-header">
          <span>Recommended Action</span>
          <span class="hitl-badge">Human-in-the-Loop Decision</span>
        </div>
        <div class="callout-body">
          ${escapeHtml(resp.recommendation)}
        </div>
      </div>
    `;
  }

  let assumptionsHtml = "";
  if (resp.assumptions) {
    assumptionsHtml = `
      <div class="assumptions-pill">
        <strong>Explicit Operational Assumption:</strong> ${escapeHtml(resp.assumptions)}
      </div>
    `;
  }

  const isNullCase = resp.grounding_source === "null_case_detector";
  const badgeLabel = isNullCase ? "🛑 Zero Hallucination (No Data Refusal)" : "🛡️ Grounded in Verified Data";
  const badgeClass = isNullCase ? "color: #fb7185; border-color: rgba(244, 63, 94, 0.4);" : "";

  bubble.innerHTML = `
    <div class="copilot-response-card">
      <div class="copilot-badge-row">
        <div class="copilot-author">
          <img src="/static/assets/logo.svg" alt="" width="20" height="20">
          <span>Retail Copilot</span>
        </div>
        <div class="grounding-tag" style="${badgeClass}">
          <span>${isNullCase ? '🛑' : '🛡️'}</span> ${badgeLabel}
        </div>
      </div>

      <div class="copilot-answer-text">
        ${formatMarkdown(resp.answer)}
      </div>

      ${evidenceSectionHtml}
      ${recommendationHtml}
      ${assumptionsHtml}
    </div>
  `;

  stream.appendChild(bubble);
  stream.scrollTop = stream.scrollHeight;
}

// --- CATALOG EXPLORER MODAL ---

async function openCatalogModal() {
  const modal = document.getElementById("catalog-modal");
  modal.style.display = "flex";

  if (cachedStores.length === 0) {
    try {
      const sRes = await fetch("/api/stores");
      cachedStores = await sRes.json();
      renderModalStores();

      const pRes = await fetch("/api/products");
      cachedProducts = await pRes.json();
      renderModalProducts();
    } catch (e) {
      console.error("Modal load error:", e);
    }
  }
}

function closeCatalogModal() {
  document.getElementById("catalog-modal").style.display = "none";
}

function renderModalStores() {
  const container = document.getElementById("modal-stores-list");
  container.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Store ID</th>
          <th>Store Name</th>
          <th>City</th>
          <th>Store Manager</th>
        </tr>
      </thead>
      <tbody>
        ${cachedStores.map(s => `
          <tr>
            <td><code>${s.store_id}</code></td>
            <td><strong>${s.store_name}</strong></td>
            <td>${s.city}</td>
            <td>${s.manager}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderModalProducts() {
  const container = document.getElementById("modal-products-list");
  container.innerHTML = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Product ID</th>
          <th>Product Name</th>
          <th>Category</th>
          <th>Price</th>
          <th>Reorder Point</th>
        </tr>
      </thead>
      <tbody>
        ${cachedProducts.map(p => `
          <tr>
            <td><code>${p.product_id}</code></td>
            <td><strong>${p.product_name}</strong></td>
            <td>${p.category}</td>
            <td>₹${p.unit_price}</td>
            <td>${p.reorder_level} units</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

// --- WHAT-IF REORDER SIMULATOR ---

let simStoresLoaded = false;

async function openSimulatorModal() {
  const modal = document.getElementById("simulator-modal");
  modal.style.display = "flex";

  if (!simStoresLoaded) {
    if (cachedStores.length === 0) {
      const sRes = await fetch("/api/stores");
      cachedStores = await sRes.json();
    }
    if (cachedProducts.length === 0) {
      const pRes = await fetch("/api/products");
      cachedProducts = await pRes.json();
    }

    const storeSelect = document.getElementById("sim-store-select");
    storeSelect.innerHTML = cachedStores.map(s => `<option value="${s.store_id}">${s.store_name} (${s.city})</option>`).join("");

    const prodSelect = document.getElementById("sim-product-select");
    prodSelect.innerHTML = cachedProducts.map(p => `<option value="${p.product_id}">${p.product_name} (₹${p.unit_price})</option>`).join("");

    simStoresLoaded = true;
  }

  runSimulation();
}

function closeSimulatorModal() {
  document.getElementById("simulator-modal").style.display = "none";
}

function updateSimSlider(val) {
  document.getElementById("sim-days-display").innerText = `${val} Days`;
  runSimulation();
}

async function runSimulation() {
  const storeId = document.getElementById("sim-store-select").value || "S01";
  const prodId = document.getElementById("sim-product-select").value || "P02";
  const days = parseInt(document.getElementById("sim-days-slider").value, 10) || 14;

  const resultsGrid = document.getElementById("sim-results-grid");
  const noteElem = document.getElementById("sim-assumption-note");

  try {
    const res = await fetch("/api/simulate-reorder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ store_id: storeId, product_id: prodId, target_cover_days: days })
    });

    if (!res.ok) throw new Error("Simulation failed");
    const d = await res.json();

    resultsGrid.innerHTML = `
      <div class="sim-result-card">
        <span class="sim-card-label">Current Stock</span>
        <span class="sim-card-val">${d.current_stock} Units</span>
      </div>
      <div class="sim-result-card">
        <span class="sim-card-label">Daily Sales Velocity</span>
        <span class="sim-card-val">${d.avg_daily_sales} /day</span>
      </div>
      <div class="sim-result-card">
        <span class="sim-card-label">Stock Cover</span>
        <span class="sim-card-val" style="color: ${d.days_of_stock_remaining && d.days_of_stock_remaining < 3 ? '#fb7185' : '#34d399'};">
          ${d.days_of_stock_remaining !== null ? `${d.days_of_stock_remaining}d` : 'N/A'}
        </span>
      </div>
      <div class="sim-result-card">
        <span class="sim-card-label">Target Buffer Needed</span>
        <span class="sim-card-val" style="color: #a5b4fc;">${d.target_stock_needed} Units</span>
      </div>
      <div class="sim-result-card">
        <span class="sim-card-label">Recommended Order</span>
        <span class="sim-card-val" style="color: #38bdf8;">${d.recommended_order_quantity} Units</span>
      </div>
      <div class="sim-result-card">
        <span class="sim-card-label">Estimated Order Value</span>
        <span class="sim-card-val" style="color: #fbbf24;">₹${Number(d.estimated_purchase_cost).toLocaleString('en-IN')}</span>
      </div>
    `;

    noteElem.innerHTML = `
      <strong>Operational Policy:</strong> ${escapeHtml(d.assumption)} &bull; 
      Projected Runout Date: <code style="color: #f1f5f9;">${d.projected_stockout_date}</code>
    `;
  } catch (err) {
    console.error("Simulation error:", err);
    resultsGrid.innerHTML = `<div style="color: var(--text-muted); padding: 1rem;">Simulation unavailable.</div>`;
  }
}

// --- STORE BENCHMARKS MODAL ---

async function openBenchmarksModal() {
  const modal = document.getElementById("benchmarks-modal");
  modal.style.display = "flex";

  const storesContainer = document.getElementById("benchmarks-stores-container");
  const catsContainer = document.getElementById("benchmarks-categories-container");

  try {
    const res = await fetch("/api/benchmarks");
    if (!res.ok) throw new Error("Benchmarks failed");
    const data = await res.json();

    const maxRev = Math.max(...data.stores.map(s => s.total_revenue), 1);

    storesContainer.innerHTML = data.stores.map((s, idx) => {
      const pct = Math.round((s.total_revenue / maxRev) * 100);
      return `
        <div class="benchmark-card">
          <div class="benchmark-card-header">
            <div>
              <span style="color: #a5b4fc; font-weight: 700; margin-right: 0.5rem;">#${idx + 1}</span>
              <strong>${s.store_name}</strong> &bull; <span style="color: var(--text-muted); font-size: 0.8rem;">${s.city}</span>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center;">
              <span style="font-size: 0.78rem; color: var(--text-secondary); font-family: 'JetBrains Mono', monospace;">
                ₹${Number(s.total_revenue).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </span>
              <span class="benchmark-health-pill">Health: ${s.health_score}%</span>
            </div>
          </div>
          <div class="progress-track">
            <div class="progress-fill" style="width: ${pct}%;"></div>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--text-muted); margin-top: 0.35rem;">
            <span>Units Sold: ${s.total_units_sold.toLocaleString()}</span>
            <span>Stockouts: <strong style="color: #fb7185;">${s.stockout_count}</strong> &bull; Dead Stock: <strong style="color: #fbbf24;">${s.dead_stock_count}</strong></span>
          </div>
        </div>
      `;
    }).join("");

    catsContainer.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Category</th>
            <th>Revenue</th>
            <th>Revenue Share</th>
            <th>Top Performer SKU</th>
          </tr>
        </thead>
        <tbody>
          ${data.categories.map(c => `
            <tr>
              <td><strong>${c.category}</strong></td>
              <td>₹${Number(c.total_revenue).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
              <td><span style="color: #38bdf8; font-weight: 600;">${c.revenue_share_pct}%</span></td>
              <td>${c.top_selling_product}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  } catch (err) {
    console.error("Benchmarks error:", err);
    storesContainer.innerHTML = `<div style="color: var(--text-muted); padding: 1rem;">Failed to load benchmarks.</div>`;
  }
}

function closeBenchmarksModal() {
  document.getElementById("benchmarks-modal").style.display = "none";
}

// --- 1-CLICK EXPORT BRIEF ---

function exportDailyBrief() {
  window.location.href = "/api/export-report";
}

// --- HANDS-FREE VOICE DICTATION ---

let recognition = null;
let isRecording = false;

function toggleVoiceInput() {
  const micBtn = document.getElementById("btn-mic");
  const inputField = document.getElementById("chat-input-field");

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert("Speech recognition is not supported in this browser. Please use Chrome or Edge for voice input.");
    return;
  }

  if (isRecording && recognition) {
    recognition.stop();
    return;
  }

  try {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      isRecording = true;
      micBtn.classList.add("listening");
      inputField.placeholder = "Listening... Speak your question now!";
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      inputField.value = transcript;
      handleChatSubmit();
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      stopVoice();
    };

    recognition.onend = () => {
      stopVoice();
    };

    recognition.start();
  } catch (err) {
    console.error("Speech recognition startup error:", err);
    stopVoice();
  }
}

function stopVoice() {
  isRecording = false;
  const micBtn = document.getElementById("btn-mic");
  const inputField = document.getElementById("chat-input-field");
  if (micBtn) micBtn.classList.remove("listening");
  if (inputField) inputField.placeholder = "Ask your store data or click 🎤 to speak...";
}

