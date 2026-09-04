"""Unit tests for deterministic retail analytics."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.analytics import RetailAnalytics
from src.config import TARGET_REORDER_DAYS_COVER

@pytest.fixture
def sample_analytics():
    """Builds a miniature mock dataset to test edge cases deterministically."""
    stores_df = pd.DataFrame([
        {"store_id": "S01", "store_name": "Store Hyderabad", "city": "Hyderabad"},
        {"store_id": "S02", "store_name": "Store Vijayawada", "city": "Vijayawada"},
        {"store_id": "S03", "store_name": "Store Chennai", "city": "Chennai"}
    ])

    products_df = pd.DataFrame([
        {"product_id": "P01", "product_name": "Sparkle Water", "category": "Beverages", "unit_price": 50.0, "reorder_level": 30},
        {"product_id": "P02", "product_name": "Juice", "category": "Beverages", "unit_price": 80.0, "reorder_level": 25},
        {"product_id": "P03", "product_name": "Cookies", "category": "Snacks", "unit_price": 100.0, "reorder_level": 20},
        {"product_id": "P17", "product_name": "Face Wash", "category": "Personal Care", "unit_price": 150.0, "reorder_level": 15}
    ])

    # End date: 2026-08-28
    end_date = datetime(2026, 8, 28)
    sales = []

    # S01, P01: Imminent Stockout: 10 units/day in recent 7d. Current stock = 20 -> 2.0 days
    for i in range(21):
        d = end_date - timedelta(days=i)
        sales.append({
            "date": d,
            "store_id": "S01",
            "product_id": "P01",
            "units_sold": 10,
            "revenue": 500.0
        })

    # S02, P02: Dead Stock: 0 sales in last 14 days! (sales only 15-20 days ago)
    for i in range(14, 21):
        d = end_date - timedelta(days=i)
        sales.append({
            "date": d,
            "store_id": "S02",
            "product_id": "P02",
            "units_sold": 5,
            "revenue": 400.0
        })

    # S01, P03: Spike: baseline (days 8-21) avg = 10/day; recent 7d avg = 25/day (+150%)
    for i in range(21):
        d = end_date - timedelta(days=i)
        units = 25 if i < 7 else 10
        sales.append({
            "date": d,
            "store_id": "S01",
            "product_id": "P03",
            "units_sold": units,
            "revenue": units * 100.0
        })

    # Note: S03 + P17 has ZERO sales rows!

    sales_df = pd.DataFrame(sales)

    inventory_df = pd.DataFrame([
        {"store_id": "S01", "product_id": "P01", "current_stock": 20},  # 20 / 10 = 2.0 days remaining
        {"store_id": "S02", "product_id": "P02", "current_stock": 87},  # Dead stock (0 sales in 14d)
        {"store_id": "S01", "product_id": "P03", "current_stock": 60},  # Spiking item
        {"store_id": "S03", "product_id": "P17", "current_stock": 40},  # No sales data
        {"store_id": "S02", "product_id": "P01", "current_stock": 100}  # Zero sales product (test division by zero)
    ])

    return RetailAnalytics(stores_df, products_df, sales_df, inventory_df)

def test_stockout_prediction(sample_analytics):
    """Test stockout risk calculation: stock = 20, daily_sales = 10 -> days_remaining = 2.0."""
    risks = sample_analytics.calculate_stockout_risks(lookback_days=7)
    p01_risk = next((r for r in risks if r["store_id"] == "S01" and r["product_id"] == "P01"), None)
    assert p01_risk is not None
    assert p01_risk["current_stock"] == 20
    assert p01_risk["avg_daily_sales"] == 10.0
    assert p01_risk["days_remaining"] == 2.0

def test_zero_sales_division_guard(sample_analytics):
    """Test that zero recent sales does not cause division by zero or negative days."""
    # S02, P01 has stock = 100, but 0 recent sales
    risks = sample_analytics.calculate_stockout_risks(lookback_days=7)
    # Zero sales items should NOT be flagged as imminent stockout (no depletion)
    s02_p01 = next((r for r in risks if r["store_id"] == "S02" and r["product_id"] == "P01"), None)
    assert s02_p01 is None

def test_dead_stock_detection(sample_analytics):
    """Test dead stock detection: current_stock > 0 and 14-day sales == 0."""
    dead_stock = sample_analytics.calculate_dead_stock(lookback_days=14)
    p02_dead = next((d for d in dead_stock if d["store_id"] == "S02" and d["product_id"] == "P02"), None)
    assert p02_dead is not None
    assert p02_dead["current_stock"] == 87
    assert p02_dead["units_sold_lookback"] == 0

def test_sales_spike_detection(sample_analytics):
    """Test sales spike: baseline = 10/day, recent = 25/day (+150% growth)."""
    spikes, _ = sample_analytics.detect_sales_anomalies(baseline_days=14, recent_days=7)
    p03_spike = next((s for s in spikes if s["store_id"] == "S01" and s["product_id"] == "P03"), None)
    assert p03_spike is not None
    assert p03_spike["baseline_sales"] == 10.0
    assert p03_spike["recent_sales"] == 25.0
    assert p03_spike["change_pct"] == 150.0

def test_null_case_handling(sample_analytics):
    """HARD CONSTRAINT (Case 5): Store Chennai + Product P17 has no rows -> status is NO_DATA."""
    res = sample_analytics.get_product_store_performance("S03", "P17")
    assert res["status"] == "NO_DATA"
    assert "No sales records exist" in res["message"]

def test_reorder_calculation(sample_analytics):
    """Test deterministic reorder quantity: target = avg_daily * cover, order = max(0, target - stock)."""
    # stock = 8, avg_sales = 11, cover = 7 -> target = 77 -> reorder = 69
    rec = sample_analytics.calculate_reorder_recommendation(current_stock=8, avg_daily_sales=11.0, target_cover_days=7)
    assert rec["target_stock"] == 77
    assert rec["recommended_order"] == 69
    assert "Assumes 7 days" in rec["assumption"]

    # When stock exceeds target, reorder is 0
    rec_surplus = sample_analytics.calculate_reorder_recommendation(current_stock=100, avg_daily_sales=5.0, target_cover_days=7)
    assert rec_surplus["recommended_order"] == 0

def test_simulate_reorder(sample_analytics):
    """Test What-If simulation: custom cover days, purchase cost, retail value, projected stockout."""
    # S01, P01: stock = 20, 7d sales = 70 -> avg_daily = 10.0
    # Simulate 14 days: target = 140 -> order = 140 - 20 = 120 units
    sim = sample_analytics.simulate_reorder(store_id="S01", product_id="P01", target_cover_days=14)
    assert sim["store_id"] == "S01"
    assert sim["product_id"] == "P01"
    assert sim["current_stock"] == 20
    assert sim["avg_daily_sales"] == 10.0
    assert sim["target_cover_days"] == 14
    assert sim["target_stock_needed"] == 140
    assert sim["recommended_order_quantity"] == 120
    assert sim["estimated_purchase_cost"] > 0
    assert sim["estimated_retail_value"] == 120 * 50.0  # unit_price = 50.0
    assert sim["days_of_stock_remaining"] == 2.0
    assert "Assumes steady 10.0 units/day" in sim["assumption"]

def test_benchmarks(sample_analytics):
    """Test cross-store ranking and category breakdown benchmarks."""
    benchmarks = sample_analytics.get_benchmarks()
    assert "stores" in benchmarks
    assert "categories" in benchmarks
    assert len(benchmarks["stores"]) == 3
    
    # Store ranking by total_revenue
    stores = benchmarks["stores"]
    assert stores[0]["total_revenue"] >= stores[1]["total_revenue"]
    for s in stores:
        assert "health_score" in s
        assert 0 <= s["health_score"] <= 100
        assert "avg_daily_revenue" in s
    
    # Categories verification
    categories = benchmarks["categories"]
    assert len(categories) >= 2
    cat_names = [c["category"] for c in categories]
    assert "Beverages" in cat_names
    assert "Snacks" in cat_names
    for c in categories:
        assert c["total_revenue"] > 0
        assert c["revenue_share_pct"] > 0
        assert c["top_selling_product"] != ""

