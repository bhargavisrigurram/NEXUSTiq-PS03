"""Pydantic schemas for request/response validation."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="Store manager natural language question")
    store_id: Optional[str] = Field(None, description="Optional store filter")

class EvidenceCard(BaseModel):
    product_id: str
    product_name: str
    store_name: str
    current_stock: int
    avg_daily_sales: float
    days_remaining: Optional[float] = None
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)

class ChatResponse(BaseModel):
    answer: str
    evidence: List[EvidenceCard] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    recommendation: Optional[str] = None
    assumptions: Optional[str] = None
    confidence: str = "high"
    status: str = "success"
    query_intent: str = "general"
    grounding_source: str = "dataset_deterministic"

class AttentionItem(BaseModel):
    type: str  # stockout_risk, dead_stock, sales_spike, sales_drop
    category_title: str
    product_id: str
    product_name: str
    product_category: str
    store_id: str
    store_name: str
    current_stock: int
    avg_daily_sales: float
    days_remaining: Optional[float] = None
    baseline_sales: Optional[float] = None
    recent_sales: Optional[float] = None
    change_pct: Optional[float] = None
    recommendation: str
    assumption: str

class AttentionResponse(BaseModel):
    stockout_risks: List[AttentionItem] = Field(default_factory=list)
    dead_stock: List[AttentionItem] = Field(default_factory=list)
    sales_spikes: List[AttentionItem] = Field(default_factory=list)
    sales_drops: List[AttentionItem] = Field(default_factory=list)
    total_alerts: int = 0
    generated_at: str

class HealthResponse(BaseModel):
    status: str
    gemini_configured: bool
    data_loaded: bool
    index_loaded: bool
    store_count: int
    product_count: int
    sales_record_count: int
    gemini_model: str
    embedding_model: str

class SummaryResponse(BaseModel):
    total_stores: int
    total_products: int
    total_sales_records: int
    date_start: str
    date_end: str
    total_units_sold: int
    total_revenue: float

class SimulationRequest(BaseModel):
    store_id: str = Field(..., description="Target store ID, e.g. S01")
    product_id: str = Field(..., description="Target product SKU ID, e.g. P02")
    target_cover_days: int = Field(7, ge=1, le=60, description="Desired days of inventory cover")

class SimulationResponse(BaseModel):
    store_id: str
    store_name: str
    product_id: str
    product_name: str
    product_category: str
    current_stock: int
    avg_daily_sales: float
    target_cover_days: int
    target_stock_needed: int
    recommended_order_quantity: int
    cost_price_per_unit: float
    selling_price_per_unit: float
    estimated_purchase_cost: float
    estimated_retail_value: float
    projected_stockout_date: Optional[str] = None
    days_of_stock_remaining: Optional[float] = None
    assumption: str

class StoreBenchmarkItem(BaseModel):
    store_id: str
    store_name: str
    city: str
    total_units_sold: int
    total_revenue: float
    avg_daily_revenue: float
    total_active_skus: int
    stockout_count: int
    dead_stock_count: int
    health_score: int

class CategoryBenchmarkItem(BaseModel):
    category: str
    total_units_sold: int
    total_revenue: float
    revenue_share_pct: float
    top_selling_product: str

class BenchmarkResponse(BaseModel):
    stores: List[StoreBenchmarkItem]
    categories: List[CategoryBenchmarkItem]
    generated_at: str

