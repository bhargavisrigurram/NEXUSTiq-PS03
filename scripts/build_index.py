"""Builds pre-computed evidence chunks and vector embeddings index for NexusTiq24 PS03.

Outputs:
- generated_index/evidence_chunks.json
- generated_index/embeddings.npy

Guarantees instantaneous startup (< 3 seconds) without runtime indexing delays.
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import pandas as pd

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import INDEX_DIR, DATA_DIR, EMBEDDING_MODEL, is_gemini_configured
from src.data_loader import DataLoader
from src.analytics import RetailAnalytics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_index")

INDEX_DIR.mkdir(parents=True, exist_ok=True)

def create_evidence_chunks(analytics: RetailAnalytics) -> List[Dict[str, Any]]:
    """Creates rich, structured evidence chunks across all stores, products, and anomaly categories."""
    chunks = []
    chunk_id = 0

    # 1. Attention Items: Stockouts, Dead Stock, Spikes, Drops
    attention = analytics.get_all_attention_items()

    for item in attention["stockout_risks"]:
        chunk_id += 1
        text = (
            f"ALERT TYPE: IMMINENT STOCKOUT RISK\n"
            f"Store: {item['store_name']} ({item['store_id']})\n"
            f"Product: {item['product_name']} ({item['product_id']})\n"
            f"Category: {item['product_category']}\n"
            f"Current Stock: {item['current_stock']} units\n"
            f"Average Daily Sales (Recent 7d): {item['avg_daily_sales']} units/day\n"
            f"Estimated Days of Stock Remaining: {item['days_remaining']} days\n"
            f"Status: URGENT_DEPLETION_RISK\n"
            f"Recommendation: {item['recommendation']}\n"
            f"Assumption: {item['assumption']}"
        )
        chunks.append({
            "chunk_id": f"chunk_{chunk_id:04d}",
            "type": "stockout_risk",
            "store_id": item["store_id"],
            "store_name": item["store_name"],
            "product_id": item["product_id"],
            "product_name": item["product_name"],
            "category": item["product_category"],
            "text": text,
            "metrics": item
        })

    for item in attention["dead_stock"]:
        chunk_id += 1
        text = (
            f"ALERT TYPE: DEAD / NON-MOVING STOCK\n"
            f"Store: {item['store_name']} ({item['store_id']})\n"
            f"Product: {item['product_name']} ({item['product_id']})\n"
            f"Category: {item['product_category']}\n"
            f"Current Stock: {item['current_stock']} units\n"
            f"Sales in Last 14 Days: 0 units\n"
            f"Status: STAGNANT_INVENTORY\n"
            f"Recommendation: {item['recommendation']}\n"
            f"Assumption: {item['assumption']}"
        )
        chunks.append({
            "chunk_id": f"chunk_{chunk_id:04d}",
            "type": "dead_stock",
            "store_id": item["store_id"],
            "store_name": item["store_name"],
            "product_id": item["product_id"],
            "product_name": item["product_name"],
            "category": item["product_category"],
            "text": text,
            "metrics": item
        })

    for item in attention["sales_spikes"]:
        chunk_id += 1
        text = (
            f"ALERT TYPE: UNUSUAL SALES SPIKE\n"
            f"Store: {item['store_name']} ({item['store_id']})\n"
            f"Product: {item['product_name']} ({item['product_id']})\n"
            f"Category: {item['product_category']}\n"
            f"Baseline Daily Sales (Previous 14d): {item.get('baseline_sales', 'N/A')} units/day\n"
            f"Recent Daily Sales (Latest 7d): {item.get('recent_sales', 'N/A')} units/day\n"
            f"Growth: +{item.get('change_pct', 'N/A')}%\n"
            f"Current Stock: {item['current_stock']} units\n"
            f"Status: DEMAND_SURGE\n"
            f"Recommendation: {item['recommendation']}\n"
            f"Assumption: {item['assumption']}"
        )
        chunks.append({
            "chunk_id": f"chunk_{chunk_id:04d}",
            "type": "sales_spike",
            "store_id": item["store_id"],
            "store_name": item["store_name"],
            "product_id": item["product_id"],
            "product_name": item["product_name"],
            "category": item["product_category"],
            "text": text,
            "metrics": item
        })

    for item in attention["sales_drops"]:
        chunk_id += 1
        text = (
            f"ALERT TYPE: UNUSUAL SALES DROP\n"
            f"Store: {item['store_name']} ({item['store_id']})\n"
            f"Product: {item['product_name']} ({item['product_id']})\n"
            f"Category: {item['product_category']}\n"
            f"Baseline Daily Sales (Previous 14d): {item.get('baseline_sales', 'N/A')} units/day\n"
            f"Recent Daily Sales (Latest 7d): {item.get('recent_sales', 'N/A')} units/day\n"
            f"Drop: {item.get('change_pct', 'N/A')}%\n"
            f"Current Stock: {item['current_stock']} units\n"
            f"Status: DEMAND_CONTRACTION\n"
            f"Recommendation: {item['recommendation']}\n"
            f"Assumption: {item['assumption']}"
        )
        chunks.append({
            "chunk_id": f"chunk_{chunk_id:04d}",
            "type": "sales_drop",
            "store_id": item["store_id"],
            "store_name": item["store_name"],
            "product_id": item["product_id"],
            "product_name": item["product_name"],
            "category": item["product_category"],
            "text": text,
            "metrics": item
        })

    # 2. Store + Product Performance Summaries (All combinations)
    for store_id in analytics.stores_df["store_id"]:
        for prod_id in analytics.products_df["product_id"]:
            perf = analytics.get_product_store_performance(store_id, prod_id)
            chunk_id += 1

            if perf["status"] == "NO_DATA":
                text = (
                    f"DATA RECORD STATUS: NO_DATA (MISSING SALES RECORDS)\n"
                    f"Store: {perf['store_name']} ({perf['store_id']})\n"
                    f"Product: {perf['product_name']} ({perf['product_id']})\n"
                    f"Category: {perf['product_category']}\n"
                    f"Catalogue Current Stock: {perf['current_stock']} units\n"
                    f"Sales History: ABSENT. No sales transaction records exist in the dataset.\n"
                    f"Analytical Finding: Performance cannot be evaluated without guessing."
                )
            else:
                days_cover_str = f"{perf['days_of_stock_remaining']} days" if perf['days_of_stock_remaining'] is not None else "N/A (zero recent sales)"
                reorder_info = perf.get("reorder_recommendation", {})
                rec_order = reorder_info.get("recommended_order", 0)
                reorder_str = f"Recommended reorder {rec_order} units (assumption: 7-day cover)" if rec_order > 0 else "Stock is currently sufficient"

                text = (
                    f"STORE PRODUCT PERFORMANCE SUMMARY\n"
                    f"Store: {perf['store_name']} ({perf['store_id']})\n"
                    f"Product: {perf['product_name']} ({perf['product_id']})\n"
                    f"Category: {perf['product_category']}\n"
                    f"Unit Price: ₹{perf['unit_price']}\n"
                    f"Total Units Sold (Period): {perf['total_units_sold']} units\n"
                    f"Total Revenue: ₹{perf['total_revenue']}\n"
                    f"Overall Daily Sales Average: {perf['avg_daily_sales_overall']} units/day\n"
                    f"Recent 7-Day Velocity: {perf['recent_7d_daily_avg']} units/day\n"
                    f"Current Inventory: {perf['current_stock']} units\n"
                    f"Days of Stock Remaining: {days_cover_str}\n"
                    f"Zero Sales Days Recorded: {perf['zero_sale_days_count']} days\n"
                    f"Replenishment Status: {reorder_str}"
                )

            chunks.append({
                "chunk_id": f"chunk_{chunk_id:04d}",
                "type": "performance_summary",
                "store_id": store_id,
                "store_name": perf["store_name"],
                "product_id": prod_id,
                "product_name": perf["product_name"],
                "category": perf["product_category"],
                "text": text,
                "metrics": perf
            })

    # 3. Store Overview Summaries
    for store_id in analytics.stores_df["store_id"]:
        store_name = analytics.store_map[store_id]
        store_sales = analytics.sales_df[analytics.sales_df["store_id"] == store_id]
        total_units = int(store_sales["units_sold"].sum())
        total_rev = round(float(store_sales["revenue"].sum()), 2)
        total_days = store_sales["date"].nunique()
        chunk_id += 1

        text = (
            f"STORE OVERVIEW SUMMARY\n"
            f"Store: {store_name} ({store_id})\n"
            f"Total Units Sold: {total_units} units\n"
            f"Total Revenue: ₹{total_rev}\n"
            f"Recorded Days: {total_days} days\n"
            f"Average Daily Revenue: ₹{round(total_rev / total_days, 2) if total_days else 0}\n"
            f"Active Products Stocked: {len(analytics.products_df)}"
        )

        chunks.append({
            "chunk_id": f"chunk_{chunk_id:04d}",
            "type": "store_overview",
            "store_id": store_id,
            "store_name": store_name,
            "product_id": None,
            "product_name": None,
            "category": None,
            "text": text,
            "metrics": {"total_units": total_units, "total_revenue": total_rev, "recorded_days": total_days}
        })

    logger.info(f"Generated {len(chunks)} total structured evidence chunks.")
    return chunks

def generate_embeddings_matrix(chunks: List[Dict[str, Any]]) -> np.ndarray:
    """Generates 768-dimensional normalized embedding vectors.
    
    If Gemini API key is configured, uses gemini-embedding-001.
    If not, creates deterministic normalized bag-of-words / TF-IDF representations
    projected into 768 dimensions so that the local vector index is immediately demo-ready.
    """
    dim = 768
    num_chunks = len(chunks)

    if is_gemini_configured():
        try:
            from src.gemini_client import GeminiClient
            client = GeminiClient()
            if client.is_available:
                logger.info(f"Generating embeddings using Gemini {EMBEDDING_MODEL}...")
                test_vec = client.embed_text(chunks[0]["text"])
                if test_vec is not None:
                    actual_dim = len(test_vec)
                    gemini_embeddings = np.zeros((num_chunks, actual_dim), dtype=np.float32)
                    gemini_embeddings[0] = test_vec / (np.linalg.norm(test_vec) + 1e-9)
                    success_count = 1

                    for idx in range(1, num_chunks):
                        vec = client.embed_text(chunks[idx]["text"])
                        if vec is not None and len(vec) == actual_dim:
                            gemini_embeddings[idx] = vec / (np.linalg.norm(vec) + 1e-9)
                            success_count += 1
                        else:
                            break

                    if success_count == num_chunks:
                        logger.info(f"Successfully generated all {num_chunks} embeddings via Gemini API (dim={actual_dim}).")
                        return gemini_embeddings
                    else:
                        logger.warning(f"Gemini embedding incomplete ({success_count}/{num_chunks}). Falling back to local representation.")
        except Exception as e:
            logger.warning(f"Gemini embedding failed: {e}. Generating hybrid vector representation.")

    # Deterministic hybrid semantic projection for offline reliability
    logger.info("Generating deterministic local feature embeddings (offline-ready)...")
    embeddings = np.zeros((num_chunks, dim), dtype=np.float32)
    vocabulary = {}
    for chunk in chunks:
        words = chunk["text"].lower().replace("\n", " ").replace(":", " ").replace("₹", " ").split()
        for w in words:
            if len(w) > 2 and not w.isdigit():
                if w not in vocabulary:
                    vocabulary[w] = len(vocabulary)

    vocab_size = len(vocabulary)
    # Fixed random projection matrix from vocab_size -> 768 dimensions
    np.random.seed(42)
    projection = np.random.randn(vocab_size, dim).astype(np.float32)

    for idx, chunk in enumerate(chunks):
        words = chunk["text"].lower().replace("\n", " ").replace(":", " ").replace("₹", " ").split()
        vec = np.zeros(dim, dtype=np.float32)
        for w in words:
            if w in vocabulary:
                vec += projection[vocabulary[w]]
        # Normalize vector
        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            embeddings[idx] = vec / norm
        else:
            embeddings[idx] = np.ones(dim, dtype=np.float32) / np.sqrt(dim)

    return embeddings

def build_index():
    """Main build index orchestration."""
    logger.info("Starting index build process...")
    loader = DataLoader(DATA_DIR)
    data = loader.load_and_validate()
    analytics = RetailAnalytics(data["stores"], data["products"], data["sales"], data["inventory"])

    chunks = create_evidence_chunks(analytics)

    # Save evidence chunks JSON
    chunks_path = INDEX_DIR / "evidence_chunks.json"
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved evidence chunks to {chunks_path}")

    # Generate and save embeddings
    embeddings = generate_embeddings_matrix(chunks)
    embeddings_path = INDEX_DIR / "embeddings.npy"
    np.save(embeddings_path, embeddings)
    logger.info(f"Saved embeddings matrix (shape {embeddings.shape}) to {embeddings_path}")

    print(f"=== Successfully built index: {len(chunks)} evidence chunks, embeddings shape {embeddings.shape} ===")

if __name__ == "__main__":
    build_index()
