TRACK_ID=PS03

# NexusTiq24 — PS03 Retail Sales & Inventory Copilot

A grounded, deterministic-first AI Copilot designed for store managers operating a multi-store retail business. It delivers real-time visibility into stockout risks, stagnant inventory, sales spikes, sales drops, and replenishment needs while ensuring 100% mathematical fidelity with zero hallucinations.

---

## 1. What the Project Does

NexusTiq24 Retail Copilot serves as an intelligent operational assistant for retail store managers across branches in Hyderabad, Vijayawada, Chennai, and Bengaluru. Rather than forcing managers to manually write complex spreadsheet queries, the Copilot allows managers to converse naturally:
- Ask about impending stockouts ("What products are running out soon?")
- Discover non-moving capital ("Which products are not moving?")
- Investigate sales anomalies ("What unusual sales changes should I investigate?")
- Check branch performance ("How did Product X perform in Hyderabad?")
- Calculate deterministic reorder advice ("What should I reorder for Fresh Orange Juice?")

The system prioritizes mathematical truth: all metrics are computed deterministically in Python before being synthesized by Google Gemini (Gemini 3.5 Flash Lite) or rendered directly into structured evidence cards.

---

## 2. Problem Statement

**Problem Statement: PS03 — Retail Sales & Inventory Copilot**

Store managers in small-to-medium retail businesses face high operational friction:
1. Stockouts lead to immediate lost revenue and frustrated shoppers.
2. Dead stock locks working capital and takes up costly shelf space.
3. Conventional LLMs hallucinate numbers, miscalculate days of stock, and invent non-existent inventory data.
4. If a store has no transaction records for an item, generic chatbots fabricate plausible-sounding sales figures.

NexusTiq24 PS03 solves this by pairing a deterministic analytics engine with local RAG, pre-computed embeddings (`gemini-embedding-001`), and Google Gemini 3.5, enforcing strict grounding and refusing to guess when data is missing.

---

## 3. Key Capabilities

- **Needs Attention Today Panel**: Real-time anomaly dashboard grouping store issues into:
  - 🔴 **Stockout Risks**: High-velocity products with under 3 days of stock remaining.
  - 🟠 **Dead Stock**: Inventory sitting on shelves with zero sales in the last 14 days.
  - 🔵 **Sales Spikes**: Products experiencing >= +50% demand surge over their 14-day baseline.
  - 🟡 **Sales Drops**: Products suffering >= -50% sales contractions requiring investigation.
- **Demand Forecasting Engine**: Deterministic 7-day and 14-day velocity-based demand forecasts with calendar runout dates (e.g. `Sep 07, 2026`) and color-coded risk classifications (`CRITICAL STOCK-OUT RISK`, `WARNING STOCK-OUT RISK`, `HEALTHY STOCK`, `DEAD STOCK`).
- **Decision & Query History Audit Trail**: Persistent history of all past questions, simulations, document uploads, and analytical exports with filter pills, search, 1-click query re-run, and JSON export.
- **Visual Column Mapping & CSV Ingestion Engine**: Interactive tabular data mapper allowing managers to upload POS transaction sheets or CSVs, inspect columns, visually map schema attributes (`Product Name`, `SKU`, `Category`, `Selling Price`, `Cost Price`, `Lead Time`), and trigger dynamic recalculations.
- **Multi-Format Document Knowledge Hub (PDF, DOCX, TXT, MD)**: Drag-and-drop or attach store operations manuals, supplier contracts, return policies, SLA agreements, and invoice sheets. Uploaded documents are parsed with zero external binaries, semantically chunked, and dynamically indexed for real-time retrieval.
- **Verifiable Document Citation Cards**: Inquiries citing uploaded documents return dedicated `📄 Document Source` citation cards with exact filename, page number, and grounded text excerpt for zero-hallucination compliance.
- **What-If Reorder Simulator**: Interactive simulation drawer allowing store managers to test variable target cover horizons (3 to 30 days) and instantly inspect required order quantities, projected runout dates, and estimated procurement costs (₹) with zero LLM guesswork.
- **Store & Category Benchmarks Matrix**: Cross-store leaderboard ranking branches by gross revenue, tracking operational health scores (100-point index penalizing stockouts and dead stock), and breaking down category market share.
- **1-Click Executive Daily Brief Export**: Generates and downloads instant operational CSV reports of all active stockouts, stagnant inventory, and demand anomalies for floor staff.
- **Native Voice Dictation**: Hands-free voice inquiry via browser-native SpeechRecognition (Web Speech API) with zero third-party dependencies.
- **In-Memory Query Response Cache**: Sub-100ms ultra-fast response for repeated inquiries.
- **Natural Language Chat**: Natural language interface with interactive scenario chips and instant query answering.
- **Dual Presentation (Answer + Evidence Cards)**: Every natural language response is accompanied by Python-computed structured evidence cards displaying exact stock, velocity, and days of cover.
- **Human-in-the-Loop Reorder Engine**: Calculates deterministic order quantities based on target coverage assumptions (default 7 days) while requiring human manager approval.
- **Strict Null-Case Refusal**: Identifies unrecorded or missing store/product records and explicitly refuses to guess.
- **Catalogue Explorer**: Live inspection modal allowing managers to audit all 4 store locations and 25 catalogued SKUs.

---

## 4. Architecture

```
[ Store Manager / Web Browser ]
             │
             │ HTTP (localhost:8000)
             ▼
[ Python app.py (FastAPI + Uvicorn) ]
   ├── Static Frontend (/Frontend: HTML5, CSS3, Vanilla JS, Web Speech API)
   ├── In-Memory Query Cache (CHAT_CACHE for sub-100ms repeat latency)
   └── REST API Endpoints:
         ├── /api/health, /api/summary, /api/attention, /api/chat
         ├── /api/forecast (Demand Forecasting Engine: 7d & 14d)
         ├── /api/history (Decision & Query History Audit Trail)
         ├── /api/preview-csv (Visual Column Mapping & Tabular Ingestion)
         ├── /api/upload, /api/documents, /api/documents/{doc_id} (Multi-Format Hub)
         ├── /api/simulate-reorder (What-If Cover Simulator)
         ├── /api/benchmarks (Cross-Store Leaderboard & Category Share)
         └── /api/export-report (1-Click CSV Attention Brief)
             │
             ├──► [ src/document_parser.py ] (Pure Python PDF, DOCX, TXT, MD Parser & Chunking)
             │          │
             │          ▼
             │    [ data/uploads/* ] (Extracted chunks dynamically embedded & indexed)
             │
             ├──► [ src/data_loader.py ] (Validates CSV schema, foreign keys, date gaps)
             │          │
             │          ▼
             │    [ data/*.csv ] (stores.csv, products.csv, sales.csv, inventory.csv)
             │
             ├──► [ src/analytics.py ] (Pure Deterministic Math - Zero LLM Calls)
             │          │
             │          ├── Stockout Prediction (days_remaining = stock / avg_daily_sales)
             │          ├── Dead Stock Detection (stock > 0 & 14d_sales == 0)
             │          ├── Anomaly Detection (7d velocity vs 14d baseline ratio)
             │          ├── What-If Simulator (target_cover_days -> order_qty, cost_price)
             │          └── Cross-Store Benchmarks (health score & category share)
             │
             ├──► [ src/retrieval.py ] (Local Hybrid RAG)
             │          │
             │          ├── Entity Extraction (Stores: Hyderabad, Chennai, etc.; Products: P01-P25)
             │          ├── Intent Classification (Stockout, Dead Stock, Spike, Drop, Reorder, Sim, Doc QA)
             │          ├── Null-Case Detector (Guards missing combinations)
             │          └── NumPy Cosine Similarity against [ generated_index/embeddings.npy ] + Uploaded Index
             │
             └──► [ src/gemini_client.py ]
                        │
                        └──► Google GenAI API (Gemini 3.5 Flash Lite / gemini-embedding-001)
                             * Fallback to deterministic synthesis if offline/unconfigured
```

---

## 5. How to Install

Prerequisites: Python 3.10+ (tested on Python 3.13.5)

Clone the repository and install all dependencies (FastAPI, Uvicorn, Pandas, Google GenAI, and lightweight pure-Python document parsers `pypdf`, `python-docx`, `python-multipart`):

```bash
pip install -r requirements.txt
```

---

## 6. How to Run

Launch the application with a single command from the project root:

```bash
python app.py
```

Then open your browser and navigate to:

```
http://localhost:8000
```

This single command starts the FastAPI backend and serves the interactive Frontend dashboard together without requiring any second terminal, node/npm build, or external server.

---

## 7. Dataset Description

The system includes a realistic synthetic retail dataset spanning 75 days (2026-06-15 to 2026-08-28):
- **Stores (`data/stores.csv`)**: 4 retail stores across South India:
  - `S01`: Store Hyderabad (Hi-Tech City)
  - `S02`: Store Vijayawada (MG Road)
  - `S03`: Store Chennai (T. Nagar)
  - `S04`: Store Bengaluru (Indiranagar)
- **Products (`data/products.csv`)**: 25 catalogued SKUs across 5 core retail categories:
  - Beverages (Sparkle Water 1L, Fresh Orange Juice 500ml, Cold Brew Coffee 250ml, Masala Chai Premix 200g, Energy Boost 250ml)
  - Snacks (Artisanal Butter Cookies 200g, Roasted Almonds 150g, Banana Chips 100g, Multigrain Crackers, Dark Chocolate)
  - Packaged Food (Basmati Rice 5kg, Cold Pressed Mustard Oil 1L, Organic Quinoa, Durum Wheat Pasta, Instant Oats)
  - Personal Care (Herbal Shampoo, Neem Face Wash, Organic Lip Balm, Moisturizing Lotion, Bamboo Toothbrush)
  - Household (Dish Soap 500ml, Floor Cleaner 1L, Paper Towels 2pk, Microfiber Cloth, Waste Bags 30pk)
- **Sales (`data/sales.csv`)**: 7,420 transaction records with daily `units_sold` and `revenue`.
- **Inventory (`data/inventory.csv`)**: 100 store-product inventory records detailing `current_stock`, `last_restocked_date`, and `reorder_quantity`.

---

## 8. How the Synthetic Data Was Generated

The synthetic dataset was generated by `scripts/generate_synthetic_data.py` using fixed random seeds (`random.seed(42)`, `np.random.seed(42)`) to ensure complete reproducibility.

Sales quantities were modeled using baseline daily sales per product modulated by:
1. Store location demographic multipliers (e.g. Bengaluru 1.25x, Hyderabad 1.15x).
2. Weekend demand surges (1.3x boost on Saturdays and Sundays).
3. Realistic Gaussian noise.
4. Intentional hard cases planted at exact dates and thresholds (described in Sections 11 & 12).

---

## 9. Grounding/RAG Approach

To eliminate hallucinations while keeping startup under 3 seconds:
1. **Pre-computed Evidence Chunks (`generated_index/evidence_chunks.json`)**: 113 structured evidence summaries covering store performance, stockout risks, dead stock, spikes, and drops are generated offline.
2. **Pre-computed Vector Embeddings (`generated_index/embeddings.npy`)**: 3072-dimensional normalized embedding vectors generated via Google's `gemini-embedding-001` model are saved locally in the repository.
3. **Hybrid Retrieval**:
   - Deterministic entity extractor resolves store city names and product names/SKUs.
   - Intent classifier detects manager intent (stockout, dead stock, reorder, spike, drop, simulation, benchmark).
   - Local NumPy cosine similarity scores and ranks the most relevant chunks.
   - Exact entity filters prioritize store/product matches over generic text.
4. **Top-K Grounded Context**: Only the Top-4 relevant evidence chunks are passed into the Gemini prompt. The full dataset is never dumped into the prompt.

---

## 10. Deterministic Analytics Approach

All retail arithmetic is executed by pure deterministic functions in `src/analytics.py`. LLMs are never allowed to perform division, multiplication, or inventory math.

Key formulas:
- **Stockout Depletion Rate**:
  $$\text{days\_of\_stock\_remaining} = \frac{\text{current\_stock}}{\text{avg\_daily\_sales (recent 7d)}}$$
- **Sales Velocity Ratio**:
  $$\text{change\_ratio} = \frac{\text{recent\_daily\_avg (latest 7d)}}{\text{baseline\_daily\_avg (previous 14d)}}$$
- **Deterministic Reorder Advisory**:
  $$\text{target\_stock} = \lceil \text{avg\_daily\_sales} \times \text{target\_cover\_days} \rceil$$
  $$\text{recommended\_order} = \max(0, \text{target\_stock} - \text{current\_stock})$$

---

## 11. Edge Cases Handled

The deterministic engine explicitly protects against real-world retail edge cases:
- **Case 1 (Imminent Stockout)**:
  - Fresh Orange Juice 500ml (`P02`) in Hyderabad: stock = 8 units, velocity = 11.0/day $\rightarrow$ **0.73 days of stock remaining**.
  - Sparkle Water 1L (`P01`) in Hyderabad: stock = 24 units, velocity = 18.0/day $\rightarrow$ **1.33 days of stock remaining**.
- **Case 2 (Dead / Non-Moving Stock)**:
  - Cold Pressed Mustard Oil 1L (`P12`) in Vijayawada: current stock = 87 units, sales in last 14 days = **0 units**.
  - Organic Lip Balm 15g (`P18`) in Chennai: current stock = 65 units, sales in last 14 days = **0 units**.
- **Case 3 (Sales Spike)**:
  - Energy Boost 250ml (`P05`) in Bengaluru: 14-day baseline = 10.0/day, recent 7-day = 29.0/day $\rightarrow$ **+190.0% demand spike**.
- **Case 4 (Sales Drop)**:
  - Artisanal Butter Cookies 200g (`P06`) in Hyderabad: 14-day baseline = 20.0/day, recent 7-day = 5.0/day $\rightarrow$ **-75.0% drop**.
- **Case 6 (Date Gap vs Zero Sales)**:
  - Cold Brew Coffee (`P03`) in Vijayawada:
    - 5 days missing from timeline (2026-07-10 to 2026-07-14) representing store renovation or system closure.
    - 3 days recorded with 0 units sold (2026-07-20 to 2026-07-22).
    - `DataLoader.detect_date_gaps()` strictly differentiates missing records from zero-unit transactions.
- **Zero Sales Division Guard**:
  - When average daily sales is 0, days remaining is safely marked as `None / inf` (rendered as "N/A - zero recent sales") rather than causing a `ZeroDivisionError`.
- **Zero Baseline Guard**:
  - When historical baseline is 0, percentage growth is flagged as "New demand from zero baseline" rather than calculating infinite percentages.

---

## 12. Null-Case Behavior

**Case 5 (Missing / Null Data — Mandatory Refusal)**:
- Store Chennai (`S03`) + Product Neem Face Wash (`P17`) has **zero rows** in `sales.csv`.
- When asked: *"How did Product P17 perform in Chennai?"*
- The backend's `HybridRetriever.check_null_case()` and `RetailAnalytics.get_product_store_performance()` immediately detect `status: NO_DATA`.
- The system returns:
  > *"I don't have sales data for Product P17 (Neem Face Wash 150ml) at the Chennai store in the available dataset, so I cannot determine its performance without guessing."*
- Gemini is prevented from hallucinating or estimating hypothetical sales figures.

---

## 13. Gemini Usage

Gemini is the **only external API** utilized in this project:
- **SDK**: Current official `google-genai` Python library (`from google import genai`).
- **Generation Model**: `gemini-3.5-flash-lite` (with graceful fallback to `gemini-2.5-flash` or `gemini-3.7-flash` if requested).
- **Embedding Model**: `gemini-embedding-001`.
- **System Instructions**: Enforces strict grounding, forbids guessing, requires exact numerical fidelity, and mandates that recommendations remain advisory.
- **Deterministic Offline Resilience**: If no API key is provided or the network is unavailable, the application starts cleanly and serves verified deterministic evidence cards and templated answers.

---

## 14. API-Key Setup

The repository contains zero hardcoded keys and zero secret leaks.

1. Open `.env` in the repository root.
2. Add your Google Gemini API key:
   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   GEMINI_MODEL=gemini-3.5-flash-lite
   EMBEDDING_MODEL=gemini-embedding-001
   PORT=8000
   HOST=0.0.0.0
   ```
3. Save the file. The Python backend reads this variable securely via `python-dotenv`. The key is never exposed to the frontend, browser, or client responses.

---

## 15. Testing Instructions

The repository features automated tests covering analytics, data validation, and API contracts.

Run the test suite with:

```bash
python -m pytest tests/ -v
```

Expected output:
```
tests/test_analytics.py::test_stockout_prediction PASSED
tests/test_analytics.py::test_zero_sales_division_guard PASSED
tests/test_analytics.py::test_dead_stock_detection PASSED
tests/test_analytics.py::test_sales_spike_detection PASSED
tests/test_analytics.py::test_null_case_handling PASSED
tests/test_analytics.py::test_reorder_calculation PASSED
tests/test_analytics.py::test_simulate_reorder PASSED
tests/test_analytics.py::test_benchmarks PASSED
tests/test_analytics.py::test_demand_forecast PASSED
tests/test_api.py::test_health_endpoint PASSED
tests/test_api.py::test_summary_endpoint PASSED
tests/test_api.py::test_attention_endpoint PASSED
tests/test_api.py::test_chat_stockout_query PASSED
tests/test_api.py::test_chat_null_case_refusal PASSED
tests/test_api.py::test_frontend_index_serving PASSED
tests/test_api.py::test_simulate_reorder_endpoint PASSED
tests/test_api.py::test_benchmarks_endpoint PASSED
tests/test_api.py::test_export_report_endpoint PASSED
tests/test_api.py::test_chat_cache PASSED
tests/test_api.py::test_document_upload_and_retrieval_flow PASSED
tests/test_api.py::test_forecast_endpoint PASSED
tests/test_api.py::test_history_endpoints_flow PASSED
tests/test_api.py::test_preview_csv_endpoint PASSED
tests/test_data_loader.py::test_data_loader_valid_dataset PASSED
tests/test_data_loader.py::test_date_gap_vs_zero_sales PASSED
tests/test_document_parser.py::test_supported_extensions PASSED
tests/test_document_parser.py::test_parse_text_file PASSED
tests/test_document_parser.py::test_parse_markdown_file PASSED
tests/test_document_parser.py::test_parse_pdf_file PASSED
tests/test_document_parser.py::test_parse_docx_file PASSED
tests/test_document_parser.py::test_unsupported_file_error PASSED

======================== 31 passed in 10.47s ========================
```

---

## 16. Demo Video Link Placeholder

- **Video Demo**: `[NexusTiq24_PS03_Demo_Video_Placeholder]` *(2–5 minute walkthrough demonstrating the 4 core judging scenarios)*

---

## 17. Known Limitations

- **Synthetic Scope**: The dataset models 4 stores, 25 products, and 75 days. Extremely large retail chains (e.g. 5,000+ stores with millions of SKUs) would require partitioned vector indexes or distributed SQL databases (BigQuery/PostgreSQL).
- **Single-Turn Grounding**: The current chat API operates statelessly on a per-question basis. Multi-turn dialogue memory can be added if required.
- **Lead Time Assumptions**: The reorder quantity recommendation assumes a standard 7-day cover horizon; custom supplier lead-time variance is not currently modeled.

---

## 18. Human-in-the-Loop Decisions

NexusTiq24 PS03 enforces strict human-in-the-loop operational safety:
1. **Advisory Recommendations Only**: The Copilot recommends replenishment quantities and clearance actions, but **never automatically places orders** or executes financial transactions.
2. **Explicit Stated Assumptions**: Every recommendation prominently displays the operational assumption behind it (e.g., *"Assumes current 7-day sales velocity remains stable"*).
3. **Manager Discretion**: The final reordering decision remains entirely with the human store manager.
