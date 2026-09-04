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

