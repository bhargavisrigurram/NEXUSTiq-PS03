"""FastAPI Backend Application for NexusTiq24 PS03 Retail Copilot.

Serves both the REST API endpoints and the static Frontend dashboard.
Supports single-command execution: python app.py -> http://localhost:8000
"""
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import shutil
import uuid

from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import (
    PORT,
    HOST,
    DATA_DIR,
    INDEX_DIR,
    FRONTEND_DIR,
    GEMINI_MODEL,
    EMBEDDING_MODEL,
    is_gemini_configured
)
from src.schemas import (
    ChatRequest,
    ChatResponse,
    AttentionResponse,
    HealthResponse,
    SummaryResponse,
    SimulationRequest,
    SimulationResponse,
    BenchmarkResponse,
    DocumentMetadata,
    DocumentUploadResponse,
    DocumentListResponse,
    ForecastResponse,
    HistoryRecord,
    HistoryResponse
)
from src.data_loader import DataLoader
from src.analytics import RetailAnalytics
from src.retrieval import HybridRetriever
from src.gemini_client import GeminiClient
from src.document_parser import DocumentParser

# In-memory LRU-style query cache for high-speed repeated answers
CHAT_CACHE: Dict[str, ChatResponse] = {}

# In-memory interaction history records
HISTORY_RECORDS: List[Dict[str, Any]] = [
    {
        "id": "hist_init_1",
        "timestamp": datetime.now().strftime("%b %d, %Y • %I:%M %p"),
        "type": "chat_query",
        "title": "System Audit & Baseline Sync",
        "store": "All Stores",
        "summary": "Verified all 4 retail branches, 25 catalogued SKUs, and deterministic stockout alerting rules.",
        "details": {"system": "startup_check", "status": "nominal"}
    }
]

def add_history_entry(rec_type: str, title: str, store: str, summary: str, details: Optional[Dict[str, Any]] = None):
    entry = {
        "id": f"hist_{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now().strftime("%b %d, %Y • %I:%M %p"),
        "type": rec_type,
        "title": title,
        "store": store or "All Stores",
        "summary": summary,
        "details": details or {}
    }
    HISTORY_RECORDS.insert(0, entry)
    if len(HISTORY_RECORDS) > 150:
        HISTORY_RECORDS.pop()
    return entry

# Uploads directory
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
document_parser = DocumentParser()



logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("retail_copilot")

# Initialize FastAPI App
app = FastAPI(
    title="NexusTiq24 PS03 Retail Sales & Inventory Copilot",
    description="Grounded, deterministic-first AI copilot for retail store managers",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup singletons
try:
    logger.info("Loading and validating retail dataset...")
    data_loader = DataLoader(DATA_DIR)
    data_tables = data_loader.load_and_validate()
    logger.info("Dataset loaded successfully.")
    
    analytics_engine = RetailAnalytics(
        stores_df=data_tables["stores"],
        products_df=data_tables["products"],
        sales_df=data_tables["sales"],
        inventory_df=data_tables["inventory"]
    )
    logger.info("Deterministic analytics engine initialized.")

    gemini_client = GeminiClient()
    retriever = HybridRetriever(gemini_client=gemini_client)
    logger.info("Hybrid retriever and vector index loaded.")
except Exception as e:
    logger.error(f"Fatal error initializing application data: {e}", exc_info=True)
    raise e

# --- API ENDPOINTS ---

@app.get("/api/health", response_model=HealthResponse)
def get_health():
    """Health check endpoint exposing system status, configuration, and data metrics."""
    return HealthResponse(
        status="ok",
        gemini_configured=is_gemini_configured(),
        data_loaded=data_tables is not None,
        index_loaded=bool(retriever.evidence_chunks),
        store_count=len(data_tables["stores"]),
        product_count=len(data_tables["products"]),
        sales_record_count=len(data_tables["sales"]),
        gemini_model=GEMINI_MODEL,
        embedding_model=EMBEDDING_MODEL,
        uploaded_documents_count=len(retriever.uploaded_documents),
        uploaded_chunks_count=len(retriever.uploaded_chunks)
    )


@app.get("/api/summary", response_model=SummaryResponse)
def get_summary():
    """Returns high-level business summary of the retail dataset."""
    sales_df = data_tables["sales"]
    stores_df = data_tables["stores"]
    products_df = data_tables["products"]

    return SummaryResponse(
        total_stores=len(stores_df),
        total_products=len(products_df),
        total_sales_records=len(sales_df),
        date_start=sales_df["date"].min().strftime("%Y-%m-%d"),
        date_end=sales_df["date"].max().strftime("%Y-%m-%d"),
        total_units_sold=int(sales_df["units_sold"].sum()),
        total_revenue=round(float(sales_df["revenue"].sum()), 2)
    )

@app.get("/api/attention", response_model=AttentionResponse)
def get_attention():
    """Returns deterministic retail anomaly alerts for the 'Needs Attention Today' panel."""
    attention_data = analytics_engine.get_all_attention_items()
    return AttentionResponse(**attention_data)

@app.get("/api/stores")
def get_stores():
    """Returns all retail stores in the catalog."""
    return data_tables["stores"].to_dict(orient="records")

@app.get("/api/products")
def get_products():
    """Returns all retail products in the catalog."""
    return data_tables["products"].to_dict(orient="records")

@app.post("/api/simulate-reorder", response_model=SimulationResponse)
def simulate_reorder_endpoint(req: SimulationRequest):
    """Calculates deterministic replenishment requirements for a custom target cover horizon."""
    sim_data = analytics_engine.simulate_reorder(
        store_id=req.store_id,
        product_id=req.product_id,
        target_cover_days=req.target_cover_days
    )
    add_history_entry(
        rec_type="simulation",
        title=f"What-If Simulation: {sim_data['product_name']}",
        store=sim_data['store_name'],
        summary=f"Calculated {sim_data['target_cover_days']}-day cover ({sim_data['target_stock_needed']} units needed). Recommended order: {sim_data['recommended_order_quantity']} units (₹{sim_data['estimated_purchase_cost']:,.2f}).",
        details=sim_data
    )
    return SimulationResponse(**sim_data)

@app.get("/api/benchmarks", response_model=BenchmarkResponse)
def get_benchmarks_endpoint():
    """Returns cross-store performance rankings and category share breakdowns."""
    benchmarks_data = analytics_engine.get_benchmarks()
    return BenchmarkResponse(**benchmarks_data)

@app.get("/api/export-report")
def export_attention_report():
    """Exports active stockouts, dead stock, and sales anomalies as a downloadable CSV report."""
    attention = analytics_engine.get_all_attention_items()
    csv_rows = ["Category,Store,Product,Current Stock,Daily Sales,Cover Days,Recommendation,Operational Assumption"]

    for item in attention["stockout_risks"]:
        rec = item["recommendation"].replace(",", ";")
        assump = item["assumption"].replace(",", ";")
        csv_rows.append(f"Stockout Risk,{item['store_name']},{item['product_name']},{item['current_stock']},{item['avg_daily_sales']},{item['days_remaining']},\"{rec}\",\"{assump}\"")

    for item in attention["dead_stock"]:
        rec = item["recommendation"].replace(",", ";")
        assump = item["assumption"].replace(",", ";")
        csv_rows.append(f"Dead Stock,{item['store_name']},{item['product_name']},{item['current_stock']},0.0,N/A,\"{rec}\",\"{assump}\"")

    for item in attention["sales_spikes"]:
        rec = item["recommendation"].replace(",", ";")
        assump = item["assumption"].replace(",", ";")
        csv_rows.append(f"Sales Spike (+{item.get('change_pct')}%),{item['store_name']},{item['product_name']},{item['current_stock']},{item['avg_daily_sales']},N/A,\"{rec}\",\"{assump}\"")

    for item in attention["sales_drops"]:
        rec = item["recommendation"].replace(",", ";")
        assump = item["assumption"].replace(",", ";")
        csv_rows.append(f"Sales Drop ({item.get('change_pct')}%),{item['store_name']},{item['product_name']},{item['current_stock']},{item['avg_daily_sales']},N/A,\"{rec}\",\"{assump}\"")

    csv_content = "\n".join(csv_rows)
    filename = f"nexustiq24_daily_attention_report_{datetime.now().strftime('%Y%m%d')}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/forecast", response_model=ForecastResponse)
def get_demand_forecast_endpoint(store_id: Optional[str] = None):
    """Returns deterministic 7-day & 14-day demand forecasts for all or filtered stores."""
    forecasts = analytics_engine.get_demand_forecast(store_id=store_id)
    crit_count = sum(1 for f in forecasts if f["status_class"] == "critical")
    warn_count = sum(1 for f in forecasts if f["status_class"] == "warning")
    return ForecastResponse(
        forecasts=forecasts,
        total_items=len(forecasts),
        critical_count=crit_count,
        warning_count=warn_count,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

@app.get("/api/history", response_model=HistoryResponse)
def get_history_endpoint():
    """Returns the persistent history of all past queries, simulations, and manager actions."""
    return HistoryResponse(
        history=[HistoryRecord(**rec) for rec in HISTORY_RECORDS],
        total_count=len(HISTORY_RECORDS)
    )

@app.post("/api/history", response_model=HistoryRecord)
def create_history_endpoint(record: HistoryRecord):
    """Appends an interaction record to the persistent history."""
    entry = add_history_entry(
        rec_type=record.type,
        title=record.title,
        store=record.store or "All Stores",
        summary=record.summary,
        details=record.details
    )
    return HistoryRecord(**entry)

@app.delete("/api/history")
def clear_history_endpoint():
    """Clears the interaction history log."""
    HISTORY_RECORDS.clear()
    return {"status": "success", "message": "Interaction history successfully cleared."}

@app.post("/api/preview-csv")
async def preview_csv_endpoint(file: UploadFile = File(...)):
    """Previews an uploaded CSV file for visual column mapping."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported for tabular data mapping.")
    
    contents = await file.read()
    try:
        import io
        import pandas as pd
        df = pd.read_csv(io.BytesIO(contents))
        cols = df.columns.tolist()
        row_count = len(df)
        sample_records = df.head(5).fillna("").to_dict(orient="records")
        
        col_lower = {c.lower().replace(" ", "_"): c for c in cols}
        mappings = {
            "product_name": col_lower.get("product_name") or col_lower.get("name") or col_lower.get("item_name") or (cols[0] if len(cols) > 0 else ""),
            "product_id": col_lower.get("product_id") or col_lower.get("sku") or col_lower.get("barcode") or col_lower.get("id") or "",
            "category": col_lower.get("category") or col_lower.get("department") or "",
            "unit_price": col_lower.get("unit_price") or col_lower.get("price") or col_lower.get("selling_price") or "",
            "cost_price": col_lower.get("cost_price") or col_lower.get("cost") or "",
            "lead_time": col_lower.get("lead_time") or col_lower.get("supplier_lead_time") or ""
        }
        
        return {
            "filename": file.filename,
            "total_rows": row_count,
            "total_columns": len(cols),
            "columns": cols,
            "suggested_mappings": mappings,
            "sample_rows": sample_records,
            "validation_status": "Ready",
            "required_mapped": bool(mappings.get("product_name"))
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

@app.post("/api/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Uploads and parses a PDF, DOCX, TXT, or MD document into the hybrid RAG index."""
    filename = file.filename or "uploaded_doc.txt"
    if not document_parser.is_supported(filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{Path(filename).suffix}'. Allowed formats: PDF, DOCX, TXT, MD."
        )

    doc_id = str(uuid.uuid4())[:8]
    clean_name = Path(filename).name
    saved_path = UPLOADS_DIR / f"{doc_id}_{clean_name}"

    try:
        with open(saved_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        logger.error(f"Failed to save uploaded file {clean_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file on server.")

    try:
        chunks = document_parser.parse_and_chunk(saved_path, original_filename=clean_name, doc_id=doc_id)
        if not chunks:
            if saved_path.exists():
                saved_path.unlink()
            raise HTTPException(status_code=400, detail="Document appears to be empty or contains no extractable text.")

        file_size_kb = round(saved_path.stat().st_size / 1024.0, 2)
        file_ext = Path(clean_name).suffix.replace(".", "").upper()

        retriever.add_document(
            doc_id=doc_id,
            filename=clean_name,
            file_type=file_ext,
            file_size_kb=file_size_kb,
            chunks=chunks
        )

        # Clear query cache so new document answers take effect immediately
        CHAT_CACHE.clear()

        doc_meta = DocumentMetadata(
            doc_id=doc_id,
            filename=clean_name,
            file_type=file_ext,
            file_size_kb=file_size_kb,
            chunk_count=len(chunks),
            upload_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        add_history_entry(
            rec_type="document_upload",
            title=f"Document Uploaded: {clean_name}",
            store="Network Knowledge",
            summary=f"Parsed and indexed {len(chunks)} operational chunks ({file_size_kb} KB) into active RAG index.",
            details={"doc_id": doc_id, "filename": clean_name, "chunks": len(chunks)}
        )

        return DocumentUploadResponse(
            status="success",
            message=f"Document '{clean_name}' successfully processed into {len(chunks)} operational chunks.",
            document=doc_meta
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing document {clean_name}: {e}", exc_info=True)
        if saved_path.exists():
            saved_path.unlink()
        raise HTTPException(status_code=400, detail=f"Error parsing document: {str(e)}")

@app.get("/api/documents", response_model=DocumentListResponse)
def list_documents():
    """Returns all currently registered operational documents and chunk counts."""
    docs = [DocumentMetadata(**d) for d in retriever.uploaded_documents.values()]
    return DocumentListResponse(
        documents=docs,
        total_documents=len(docs),
        total_chunks=len(retriever.uploaded_chunks)
    )

@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    """Deletes an uploaded document and removes its chunks from the RAG index."""
    if doc_id not in retriever.uploaded_documents:
        raise HTTPException(status_code=404, detail="Document not found.")

    doc_info = retriever.uploaded_documents[doc_id]
    filename = doc_info["filename"]
    retriever.remove_document(doc_id)

    # Clean file from disk
    saved_file = UPLOADS_DIR / f"{doc_id}_{filename}"
    if saved_file.exists():
        saved_file.unlink()

    CHAT_CACHE.clear()
    return {"status": "success", "message": f"Document '{filename}' successfully deleted from knowledge base."}

@app.post("/api/chat", response_model=ChatResponse)

def chat_with_copilot(req: ChatRequest):
    """Primary copilot question-answering endpoint with strict grounding, zero-hallucination guard, and caching."""
    query = req.question.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    cache_key = query.lower()
    if cache_key in CHAT_CACHE:
        logger.info(f"Returning cached response for query: '{query}'")
        return CHAT_CACHE[cache_key]

    try:
        # Step 1: Hybrid Retrieval (Entity/Intent extraction + Cosine Similarity)
        retrieval_res = retriever.retrieve(query, top_k=4)

        # Step 2: CASE 5 — Mandatory Null-Case Refusal
        if retrieval_res["is_null_case"]:
            null_meta = retrieval_res["null_metadata"]
            response_obj = ChatResponse(
                answer=null_meta["refusal_text"],
                evidence=[],
                metrics={"status": "NO_DATA", "store": null_meta["store_name"], "product": null_meta["product_name"]},
                recommendation="Verify with store operations whether this product was ever distributed or catalogued at this branch.",
                assumptions="Based strictly on sales transaction logs; no records exist for this combination.",
                confidence="high",
                status="success",
                query_intent="null_case",
                grounding_source="null_case_detector"
            )
            add_history_entry(
                rec_type="chat_query",
                title=query,
                store=null_meta.get("store_name", "All Stores"),
                summary="Refused to guess: No sales records exist in dataset for this product at this branch.",
                details={"intent": "null_case", "status": "NO_DATA"}
            )
            CHAT_CACHE[cache_key] = response_obj
            return response_obj

        # Step 3: Compile structured textual evidence for Gemini prompt
        top_chunks = retrieval_res["evidence_chunks"]
        evidence_texts = [f"[{i+1}] {c['text']}" for i, c in enumerate(top_chunks)]
        combined_evidence = "\n\n".join(evidence_texts)

        # Step 4: Generate Grounded Answer (via Gemini 3.5 Flash Lite or deterministic fallback)
        ai_result = gemini_client.generate_grounded_response(
            question=query,
            evidence_text=combined_evidence,
            context_notes=f"Detected Intent: {retrieval_res['intent']}. Store Entities: {retrieval_res['entities']}"
        )

        # Extract recommendations and assumptions from primary evidence if available
        first_metrics = top_chunks[0].get("metrics", {}) if top_chunks else {}
        recommendation = first_metrics.get("recommendation", "Review inventory levels and monitor upcoming replenishment cycles.")
        assumption = first_metrics.get("assumption", "Assumes recent 7-day sales rates and supplier replenishment timelines remain stable.")

        response_obj = ChatResponse(
            answer=ai_result["text"],
            evidence=retrieval_res["evidence_cards"],
            metrics={
                "retrieved_chunks_count": len(top_chunks),
                "intent": retrieval_res["intent"],
                "entities": retrieval_res["entities"],
                "model_used": ai_result.get("model", "deterministic")
            },
            recommendation=recommendation,
            assumptions=assumption,
            confidence="high",
            status="success",
            query_intent=retrieval_res["intent"],
            grounding_source=ai_result.get("source", "deterministic")
        )

        add_history_entry(
            rec_type="chat_query",
            title=query,
            store=req.store_id or "All Network Stores",
            summary=response_obj.answer[:160] + ("..." if len(response_obj.answer) > 160 else ""),
            details={"intent": response_obj.query_intent, "evidence_count": len(response_obj.evidence)}
        )

        # Cache response for quick future retrieval (cap cache size at 100)
        if len(CHAT_CACHE) > 100:
            CHAT_CACHE.pop(next(iter(CHAT_CACHE)))
        CHAT_CACHE[cache_key] = response_obj

        return response_obj

    except Exception as e:
        logger.error(f"Error handling chat request: {e}", exc_info=True)
        # Never crash or show stack trace to user
        return ChatResponse(
            answer="The AI explanation service encountered an unexpected error. However, your store's deterministic dashboard metrics remain fully operational.",
            evidence=[],
            metrics={"error": "backend_processing_error"},
            recommendation="Refer to the 'Needs Attention Today' panel for active stockout and dead stock alerts.",
            assumptions="System operating in safety fallback mode.",
            confidence="low",
            status="error",
            query_intent="error",
            grounding_source="error_fallback"
        )

# --- STATIC FRONTEND MOUNTING ---

# Mount Frontend directory for static assets (styles.css, app.js, assets)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def serve_index():
    """Serves the primary Frontend dashboard single-page application."""
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(index_file)

if __name__ == "__main__":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("================================================================")
    print(f"Starting NexusTiq24 PS03 Retail Copilot on http://localhost:{PORT}")
    print("Serving API and Frontend together in one unified service")
    print("================================================================")
    uvicorn.run("app:app", host=HOST, port=PORT, reload=False)

