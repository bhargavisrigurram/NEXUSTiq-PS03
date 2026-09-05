"""Integration tests for FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)

def test_health_endpoint():
    """Verify system health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["data_loaded"] is True
    assert data["index_loaded"] is True
    assert data["store_count"] == 4
    assert data["product_count"] == 25
    assert data["sales_record_count"] > 5000

def test_summary_endpoint():
    """Verify high-level summary KPIs."""
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_stores"] == 4
    assert data["total_products"] == 25
    assert data["total_units_sold"] > 0
    assert data["total_revenue"] > 0

def test_attention_endpoint():
    """Verify deterministic attention anomaly alerts."""
    response = client.get("/api/attention")
    assert response.status_code == 200
    data = response.json()
    assert len(data["stockout_risks"]) >= 1
    assert len(data["dead_stock"]) >= 1
    assert len(data["sales_spikes"]) >= 1
    assert len(data["sales_drops"]) >= 1

def test_chat_stockout_query():
    """Verify chat endpoint for stockout query."""
    response = client.post("/api/chat", json={"question": "What products are running out in Hyderabad?"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["answer"]) > 10
    assert len(data["evidence"]) >= 1

def test_chat_null_case_refusal():
    """HARD CONSTRAINT (Case 5): Verifies system refuses to guess for missing data."""
    response = client.post("/api/chat", json={"question": "How did Product P17 perform in Chennai?"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["grounding_source"] == "null_case_detector"
    assert "I don't have sales data for Product P17" in data["answer"]
    assert "without guessing" in data["answer"]

def test_frontend_index_serving():
    """Verify single-command frontend root endpoint serves index.html."""
    response = client.get("/")
    assert response.status_code == 200
    assert "NexusTiq24" in response.text
    assert "PS03" in response.text

def test_simulate_reorder_endpoint():
    """Verify POST /api/simulate-reorder returns accurate deterministic replenishment calculations."""
    payload = {
        "store_id": "S01",
        "product_id": "P02",
        "target_cover_days": 14
    }
    response = client.post("/api/simulate-reorder", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["store_id"] == "S01"
    assert data["product_id"] == "P02"
    assert data["target_cover_days"] == 14
    assert data["target_stock_needed"] > 0
    assert data["recommended_order_quantity"] >= 0
    assert data["estimated_purchase_cost"] >= 0.0
    assert data["estimated_retail_value"] >= 0.0
    assert "assumption" in data

def test_benchmarks_endpoint():
    """Verify GET /api/benchmarks returns store rankings and category breakdowns."""
    response = client.get("/api/benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert "stores" in data
    assert "categories" in data
    assert len(data["stores"]) == 4
    assert len(data["categories"]) >= 4
    for store in data["stores"]:
        assert "health_score" in store
        assert "total_revenue" in store
        assert "avg_daily_revenue" in store

def test_export_report_endpoint():
    """Verify GET /api/export-report returns valid CSV content attachment."""
    response = client.get("/api/export-report")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    csv_lines = response.text.splitlines()
    assert len(csv_lines) > 5
    assert "Stockout Risk" in response.text
    assert "Dead Stock" in response.text

def test_chat_cache():
    """Verify that repeated identical questions are answered from cache with high speed."""
    query_payload = {"question": "What is the stockout situation in Hyderabad?"}
    res1 = client.post("/api/chat", json=query_payload)
    assert res1.status_code == 200
    
    # Second call should return immediately from CHAT_CACHE
    res2 = client.post("/api/chat", json=query_payload)
    assert res2.status_code == 200
    assert res2.json()["answer"] == res1.json()["answer"]

def test_document_upload_and_retrieval_flow():
    """Verify end-to-end document upload, listing, querying via chat, and deletion."""
    test_content = (
        "Store Hygiene and Pest Control Policy 2026.\n\n"
        "All perishable food displays must undergo inspection every morning at 08:00.\n"
        "Vendor delivery temperature for dairy and cold brew coffee must remain below 4 degrees Celsius."
    )
    files = {"file": ("store_hygiene_policy.txt", test_content.encode("utf-8"), "text/plain")}
    
    # 1. Upload document
    upload_res = client.post("/api/upload", files=files)
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["status"] == "success"
    doc_id = upload_data["document"]["doc_id"]
    assert upload_data["document"]["filename"] == "store_hygiene_policy.txt"
    assert upload_data["document"]["chunk_count"] >= 1

    # 2. List documents
    list_res = client.get("/api/documents")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total_documents"] >= 1
    assert any(d["doc_id"] == doc_id for d in list_data["documents"])

    # 3. Query document content via Chat
    chat_res = client.post("/api/chat", json={"question": "What is the vendor delivery temperature requirement in the hygiene policy document?"})
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["status"] == "success"
    # Evidence cards should contain the uploaded document
    doc_cards = [e for e in chat_data["evidence"] if e["status"] == "uploaded_document"]
    assert len(doc_cards) >= 1
    assert doc_cards[0]["product_name"] == "store_hygiene_policy.txt"

    # 4. Delete document
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["status"] == "success"

    # 5. Verify deleted from list
    list_res_after = client.get("/api/documents")
    assert not any(d["doc_id"] == doc_id for d in list_res_after.json()["documents"])

def test_forecast_endpoint():
    """Test /api/forecast returns deterministic 7-day and 14-day forecasts."""
    res = client.get("/api/forecast")
    assert res.status_code == 200
    data = res.json()
    assert "forecasts" in data
    assert data["total_items"] > 0
    assert "critical_count" in data
    first = data["forecasts"][0]
    assert "demand_7d" in first
    assert "demand_14d" in first
    assert "estimated_stockout_date" in first
    assert "status_level" in first

def test_history_endpoints_flow():
    """Test /api/history retrieval, creation, and clearing."""
    # 1. Fetch history
    res = client.get("/api/history")
    assert res.status_code == 200
    data = res.json()
    assert "history" in data
    initial_count = data["total_count"]

    # 2. Append new record
    new_record = {
        "id": "hist_test_1",
        "timestamp": "Sep 05, 2026 • 10:45 AM",
        "type": "chat_query",
        "title": "What products need urgent reorder?",
        "store": "Hyderabad Flagship",
        "summary": "Identified Fresh Orange Juice and Sparkle Water.",
        "details": {"test": True}
    }
    post_res = client.post("/api/history", json=new_record)
    assert post_res.status_code == 200
    assert post_res.json()["title"] == "What products need urgent reorder?"

    # 3. Verify count increased
    res_after = client.get("/api/history")
    assert res_after.json()["total_count"] == initial_count + 1

    # 4. Clear history
    del_res = client.delete("/api/history")
    assert del_res.status_code == 200
    assert client.get("/api/history").json()["total_count"] == 0

def test_preview_csv_endpoint():
    """Test /api/preview-csv parses columns and sample rows for visual column mapping."""
    sample_csv = "product_name,sku,category,unit_price,cost_price\nWireless Mouse,P30,Electronics,500,300\n"
    files = {"file": ("test_products.csv", sample_csv.encode("utf-8"), "text/csv")}
    res = client.post("/api/preview-csv", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "test_products.csv"
    assert data["total_rows"] == 1
    assert "product_name" in data["columns"]
    assert data["required_mapped"] is True
    assert data["validation_status"] == "Ready"


