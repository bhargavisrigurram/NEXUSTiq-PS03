"""Deterministic Retail Analytics Engine.

Pure deterministic calculations for retail sales and inventory metrics.
Contains ZERO LLM calls, zero hallucinations, and robust mathematical edge-case guards.
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from src.config import (
    STOCKOUT_DAYS_THRESHOLD,
    DEAD_STOCK_LOOKBACK_DAYS,
    SPIKE_RATIO_THRESHOLD,
    DROP_RATIO_THRESHOLD,
    TARGET_REORDER_DAYS_COVER
)

class RetailAnalytics:
    """Performs deterministic inventory and sales calculations."""

    def __init__(self, stores_df: pd.DataFrame, products_df: pd.DataFrame, 
                 sales_df: pd.DataFrame, inventory_df: pd.DataFrame):
        self.stores_df = stores_df.copy()
        self.products_df = products_df.copy()
        self.sales_df = sales_df.copy()
        self.inventory_df = inventory_df.copy()

        # Lookup dictionaries for fast reference
        self.store_map = {row["store_id"]: row["store_name"] for _, row in self.stores_df.iterrows()}
        self.product_map = {row["product_id"]: row["product_name"] for _, row in self.products_df.iterrows()}
        self.product_cat_map = {row["product_id"]: row["category"] for _, row in self.products_df.iterrows()}
        self.price_map = {row["product_id"]: row["unit_price"] for _, row in self.products_df.iterrows()}
        self.cost_map = {row["product_id"]: float(row.get("cost_price", row["unit_price"] * 0.6)) for _, row in self.products_df.iterrows()}

        # Timeline bounds
        if not self.sales_df.empty:
            self.max_date = self.sales_df["date"].max()
            self.min_date = self.sales_df["date"].min()
        else:
            self.max_date = pd.Timestamp.now()
            self.min_date = pd.Timestamp.now()

    def calculate_stockout_risks(self, lookback_days: int = 7) -> List[Dict[str, Any]]:
        """Identifies products at imminent risk of stockout based on recent daily velocity.
        
        Formula: days_of_stock_remaining = current_stock / avg_daily_sales
        Edge cases: 
        - If avg_daily_sales == 0: days_remaining is None / inf (no stockout risk).
        - If days_remaining < STOCKOUT_DAYS_THRESHOLD (3.0): flagged as urgent stockout risk.
        """
        recent_start = self.max_date - timedelta(days=lookback_days - 1)
        recent_sales = self.sales_df[self.sales_df["date"] >= recent_start]

        # Group by store and product
        sales_agg = recent_sales.groupby(["store_id", "product_id"])["units_sold"].sum().reset_index()
        sales_agg["avg_daily_sales"] = sales_agg["units_sold"] / float(lookback_days)

        merged = pd.merge(self.inventory_df, sales_agg, on=["store_id", "product_id"], how="left")
        merged["avg_daily_sales"] = merged["avg_daily_sales"].fillna(0.0)

        risks = []
        for _, row in merged.iterrows():
            curr_stock = int(row["current_stock"])
            daily_sales = float(row["avg_daily_sales"])

            if daily_sales <= 0.0:
                # Zero sales means no stockout depletion risk
                continue

            days_remaining = round(curr_stock / daily_sales, 2)

            if days_remaining <= STOCKOUT_DAYS_THRESHOLD:
                reorder_rec = self.calculate_reorder_recommendation(
                    current_stock=curr_stock, 
                    avg_daily_sales=daily_sales, 
                    target_cover_days=TARGET_REORDER_DAYS_COVER
                )

                risks.append({
                    "type": "stockout_risk",
                    "category_title": "Stockout Risk",
                    "product_id": row["product_id"],
                    "product_name": self.product_map.get(row["product_id"], row["product_id"]),
                    "product_category": self.product_cat_map.get(row["product_id"], "General"),
                    "store_id": row["store_id"],
                    "store_name": self.store_map.get(row["store_id"], row["store_id"]),
                    "current_stock": curr_stock,
                    "avg_daily_sales": round(daily_sales, 2),
                    "days_remaining": days_remaining,
                    "recommendation": f"Replenish urgently. Recommended order: {reorder_rec['recommended_order']} units to achieve {TARGET_REORDER_DAYS_COVER} days of cover.",
                    "assumption": f"Assumes current {lookback_days}-day sales velocity of {round(daily_sales, 1)} units/day remains stable."
                })

        # Sort by most urgent (lowest days remaining first)
        risks.sort(key=lambda x: x["days_remaining"])
        return risks

    def calculate_dead_stock(self, lookback_days: int = DEAD_STOCK_LOOKBACK_DAYS) -> List[Dict[str, Any]]:
        """Identifies dead or non-moving stock with inventory on hand but zero sales over lookback window."""
        recent_start = self.max_date - timedelta(days=lookback_days - 1)
        recent_sales = self.sales_df[self.sales_df["date"] >= recent_start]

        sales_agg = recent_sales.groupby(["store_id", "product_id"])["units_sold"].sum().reset_index()

        merged = pd.merge(self.inventory_df, sales_agg, on=["store_id", "product_id"], how="left")
        merged["units_sold"] = merged["units_sold"].fillna(0)

        dead_stock = []
        for _, row in merged.iterrows():
            curr_stock = int(row["current_stock"])
            units_sold = int(row["units_sold"])

            # Condition: Has stock on shelves, but zero sales in the lookback period
            if curr_stock > 0 and units_sold == 0:
                dead_stock.append({
                    "type": "dead_stock",
                    "category_title": "Dead Stock",
                    "product_id": row["product_id"],
                    "product_name": self.product_map.get(row["product_id"], row["product_id"]),
                    "product_category": self.product_cat_map.get(row["product_id"], "General"),
                    "store_id": row["store_id"],
                    "store_name": self.store_map.get(row["store_id"], row["store_id"]),
                    "current_stock": curr_stock,
                    "avg_daily_sales": 0.0,
                    "days_remaining": None,
                    "units_sold_lookback": 0,
                    "recommendation": "Review shelf placement, consider clearance pricing, or transfer stock to higher-velocity branches.",
                    "assumption": f"Assumes {lookback_days}-day zero movement indicates lack of consumer demand rather than temporary supply disruption."
                })

        # Sort by highest stagnant stock
        dead_stock.sort(key=lambda x: x["current_stock"], reverse=True)
        return dead_stock

    def detect_sales_anomalies(self, baseline_days: int = 14, recent_days: int = 7) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Detects unusual sales spikes and drops comparing recent velocity to historical baseline.
        
        Recent window: [max_date - 6 days, max_date] (7 days)
        Baseline window: [max_date - 20 days, max_date - 7 days] (14 days)
        """
        recent_start = self.max_date - timedelta(days=recent_days - 1)
        baseline_start = self.max_date - timedelta(days=recent_days + baseline_days - 1)
        baseline_end = self.max_date - timedelta(days=recent_days)

        recent_df = self.sales_df[self.sales_df["date"] >= recent_start]
        baseline_df = self.sales_df[(self.sales_df["date"] >= baseline_start) & (self.sales_df["date"] <= baseline_end)]

        recent_agg = recent_df.groupby(["store_id", "product_id"])["units_sold"].sum().reset_index()
        recent_agg["recent_daily_avg"] = recent_agg["units_sold"] / float(recent_days)

        baseline_agg = baseline_df.groupby(["store_id", "product_id"])["units_sold"].sum().reset_index()
        baseline_agg["baseline_daily_avg"] = baseline_agg["units_sold"] / float(baseline_days)

        merged = pd.merge(recent_agg[["store_id", "product_id", "recent_daily_avg"]],
                          baseline_agg[["store_id", "product_id", "baseline_daily_avg"]],
                          on=["store_id", "product_id"], how="outer").fillna(0.0)

        # Merge current stock
        merged = pd.merge(merged, self.inventory_df[["store_id", "product_id", "current_stock"]],
                          on=["store_id", "product_id"], how="left")
        merged["current_stock"] = merged["current_stock"].fillna(0)

        spikes = []
        drops = []

        for _, row in merged.iterrows():
            recent_avg = float(row["recent_daily_avg"])
            baseline_avg = float(row["baseline_daily_avg"])
            curr_stock = int(row["current_stock"])
            store_name = self.store_map.get(row["store_id"], row["store_id"])
            prod_name = self.product_map.get(row["product_id"], row["product_id"])
            prod_cat = self.product_cat_map.get(row["product_id"], "General")

            # Edge case: If baseline is zero
            if baseline_avg <= 0.0:
                if recent_avg >= 5.0:
                    # New spike from zero baseline
                    spikes.append({
                        "type": "sales_spike",
                        "category_title": "Sales Spike",
                        "product_id": row["product_id"],
                        "product_name": prod_name,
                        "product_category": prod_cat,
                        "store_id": row["store_id"],
                        "store_name": store_name,
                        "current_stock": curr_stock,
                        "avg_daily_sales": round(recent_avg, 2),
                        "baseline_sales": 0.0,
                        "recent_sales": round(recent_avg, 2),
                        "change_pct": None,
                        "note": "Spike from zero historical baseline",
                        "recommendation": "Investigate promotional or external catalyst; verify safety stock.",
                        "assumption": "Assumes surge is genuine consumer demand rather than data artifact."
                    })
                continue

            change_ratio = recent_avg / baseline_avg
            change_pct = round((change_ratio - 1.0) * 100, 1)

            # Check for Spike
            if change_ratio >= SPIKE_RATIO_THRESHOLD:
                spikes.append({
                    "type": "sales_spike",
                    "category_title": "Sales Spike",
                    "product_id": row["product_id"],
                    "product_name": prod_name,
                    "product_category": prod_cat,
                    "store_id": row["store_id"],
                    "store_name": store_name,
                    "current_stock": curr_stock,
                    "avg_daily_sales": round(recent_avg, 2),
                    "baseline_sales": round(baseline_avg, 2),
                    "recent_sales": round(recent_avg, 2),
                    "change_pct": change_pct,
                    "recommendation": f"Monitor stock closely (+{change_pct}% surge). Reorder proactively if momentum persists.",
                    "assumption": "Assumes recent surge will sustain over upcoming replenishment cycle."
                })

            # Check for Drop
            elif change_ratio <= DROP_RATIO_THRESHOLD:
                drops.append({
                    "type": "sales_drop",
                    "category_title": "Sales Drop",
                    "product_id": row["product_id"],
                    "product_name": prod_name,
                    "product_category": prod_cat,
                    "store_id": row["store_id"],
                    "store_name": store_name,
                    "current_stock": curr_stock,
                    "avg_daily_sales": round(recent_avg, 2),
                    "baseline_sales": round(baseline_avg, 2),
                    "recent_sales": round(recent_avg, 2),
                    "change_pct": change_pct,
                    "recommendation": f"Inspect product for competitor pricing, shelf visibility, or stock expiration ({change_pct}% drop).",
                    "assumption": "Assumes drop is not due to unrecorded stockout or store closure."
                })

        spikes.sort(key=lambda x: (x["change_pct"] or 0), reverse=True)
        drops.sort(key=lambda x: (x["change_pct"] or 0))
        return spikes, drops

    def get_product_store_performance(self, store_id: str, product_id: str) -> Dict[str, Any]:
        """Calculates granular performance metrics for a specific product and store.
        
        HARD CONSTRAINT (Case 5): If there are NO records for this store/product in sales,
        returns status 'NO_DATA' without hallucinating or estimating numbers.
        """
        store_name = self.store_map.get(store_id, store_id)
        prod_name = self.product_map.get(product_id, product_id)
        prod_cat = self.product_cat_map.get(product_id, "General")
        unit_price = self.price_map.get(product_id, 0.0)

        # Get inventory record
        inv_row = self.inventory_df[
            (self.inventory_df["store_id"] == store_id) & 
            (self.inventory_df["product_id"] == product_id)
        ]
        current_stock = int(inv_row["current_stock"].iloc[0]) if not inv_row.empty else 0

        # Filter sales records
        subset = self.sales_df[
            (self.sales_df["store_id"] == store_id) & 
            (self.sales_df["product_id"] == product_id)
        ]

        # CASE 5: Missing / Null Data check
        if subset.empty:
            return {
                "status": "NO_DATA",
                "store_id": store_id,
                "store_name": store_name,
                "product_id": product_id,
                "product_name": prod_name,
                "product_category": prod_cat,
                "current_stock": current_stock,
                "message": f"No sales records exist for {prod_name} ({product_id}) at {store_name} ({store_id}) in the dataset."
            }

        total_units = int(subset["units_sold"].sum())
        total_revenue = round(float(subset["revenue"].sum()), 2)
        total_days_recorded = len(subset)
        avg_daily_sales = round(total_units / float(total_days_recorded), 2) if total_days_recorded > 0 else 0.0

        # Recent 7-day velocity
        recent_start = self.max_date - timedelta(days=6)
        recent_subset = subset[subset["date"] >= recent_start]
        recent_units = int(recent_subset["units_sold"].sum())
        recent_daily_avg = round(recent_units / 7.0, 2)

        # Days of cover based on recent rate
        if recent_daily_avg > 0:
            days_remaining = round(current_stock / recent_daily_avg, 2)
        else:
            days_remaining = None

        # Reorder advice
        reorder = self.calculate_reorder_recommendation(current_stock, recent_daily_avg)

        # Date gaps vs zero sales
        zero_sale_days = int((subset["units_sold"] == 0).sum())

        return {
            "status": "SUCCESS",
            "store_id": store_id,
            "store_name": store_name,
            "product_id": product_id,
            "product_name": prod_name,
            "product_category": prod_cat,
            "unit_price": unit_price,
            "current_stock": current_stock,
            "total_units_sold": total_units,
            "total_revenue": total_revenue,
            "total_days_recorded": total_days_recorded,
            "avg_daily_sales_overall": avg_daily_sales,
            "recent_7d_daily_avg": recent_daily_avg,
            "days_of_stock_remaining": days_remaining,
            "zero_sale_days_count": zero_sale_days,
            "reorder_recommendation": reorder,
            "first_sale_date": subset["date"].min().strftime("%Y-%m-%d"),
            "last_sale_date": subset["date"].max().strftime("%Y-%m-%d")
        }

    def calculate_reorder_recommendation(self, current_stock: int, avg_daily_sales: float, 
                                         target_cover_days: int = TARGET_REORDER_DAYS_COVER) -> Dict[str, Any]:
        """Calculates deterministic reorder quantity with explicit operational assumptions.
        
        Formula:
        target_stock = avg_daily_sales * target_cover_days
        recommended_order = max(0, ceil(target_stock - current_stock))
        """
        if avg_daily_sales <= 0.0:
            return {
                "target_cover_days": target_cover_days,
                "target_stock": current_stock,
                "recommended_order": 0,
                "assumption": "No recent sales movement; reordering is not recommended."
            }

        target_stock = int(np.ceil(avg_daily_sales * float(target_cover_days)))
        recommended_order = max(0, target_stock - current_stock)

        return {
            "target_cover_days": target_cover_days,
            "target_stock": target_stock,
            "recommended_order": recommended_order,
            "assumption": f"Assumes {target_cover_days} days of desired coverage and steady {round(avg_daily_sales, 1)} units/day sales velocity."
        }

    def get_all_attention_items(self) -> Dict[str, Any]:
        """Runs all deterministic anomaly detection routines for the Attention Panel."""
        stockout_risks = self.calculate_stockout_risks()
        dead_stock = self.calculate_dead_stock()
        spikes, drops = self.detect_sales_anomalies()

        total = len(stockout_risks) + len(dead_stock) + len(spikes) + len(drops)

        return {
            "stockout_risks": stockout_risks,
            "dead_stock": dead_stock,
            "sales_spikes": spikes,
            "sales_drops": drops,
            "total_alerts": total,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def simulate_reorder(self, store_id: str, product_id: str, target_cover_days: int = 7) -> Dict[str, Any]:
        """Performs deterministic What-If replenishment simulation for a given horizon."""
        store_name = self.store_map.get(store_id, store_id)
        prod_name = self.product_map.get(product_id, product_id)
        prod_cat = self.product_cat_map.get(product_id, "General")
        cost_price = self.cost_map.get(product_id, 0.0)
        selling_price = self.price_map.get(product_id, 0.0)

        # Get current stock
        inv_row = self.inventory_df[
            (self.inventory_df["store_id"] == store_id) & 
            (self.inventory_df["product_id"] == product_id)
        ]
        current_stock = int(inv_row["current_stock"].iloc[0]) if not inv_row.empty else 0

        # Calculate recent velocity
        recent_start = self.max_date - timedelta(days=6)
        subset = self.sales_df[
            (self.sales_df["store_id"] == store_id) & 
            (self.sales_df["product_id"] == product_id) &
            (self.sales_df["date"] >= recent_start)
        ]
        recent_units = int(subset["units_sold"].sum())
        avg_daily_sales = round(recent_units / 7.0, 2)

        if avg_daily_sales > 0:
            days_remaining = round(current_stock / avg_daily_sales, 2)
            projected_runout = (self.max_date + timedelta(days=int(np.floor(days_remaining)))).strftime("%Y-%m-%d")
        else:
            days_remaining = None
            projected_runout = "No Depletion Expected"

        target_stock_needed = int(np.ceil(avg_daily_sales * float(target_cover_days)))
        recommended_order = max(0, target_stock_needed - current_stock)

        estimated_purchase_cost = round(recommended_order * cost_price, 2)
        estimated_retail_value = round(recommended_order * selling_price, 2)

        return {
            "store_id": store_id,
            "store_name": store_name,
            "product_id": product_id,
            "product_name": prod_name,
            "product_category": prod_cat,
            "current_stock": current_stock,
            "avg_daily_sales": avg_daily_sales,
            "target_cover_days": target_cover_days,
            "target_stock_needed": target_stock_needed,
            "recommended_order_quantity": recommended_order,
            "cost_price_per_unit": cost_price,
            "selling_price_per_unit": selling_price,
            "estimated_purchase_cost": estimated_purchase_cost,
            "estimated_retail_value": estimated_retail_value,
            "projected_stockout_date": projected_runout,
            "days_of_stock_remaining": days_remaining,
            "assumption": f"Assumes steady {avg_daily_sales} units/day velocity over {target_cover_days} days of planned coverage."
        }

    def get_benchmarks(self) -> Dict[str, Any]:
        """Calculates store-to-store benchmarking and category share metrics."""
        attention = self.get_all_attention_items()
        stockouts_by_store = {}
        for item in attention["stockout_risks"]:
            stockouts_by_store[item["store_id"]] = stockouts_by_store.get(item["store_id"], 0) + 1

        dead_stock_by_store = {}
        for item in attention["dead_stock"]:
            dead_stock_by_store[item["store_id"]] = dead_stock_by_store.get(item["store_id"], 0) + 1

        store_items = []
        total_chain_revenue = float(self.sales_df["revenue"].sum())

        for _, s in self.stores_df.iterrows():
            sid = s["store_id"]
            s_sales = self.sales_df[self.sales_df["store_id"] == sid]
            tot_units = int(s_sales["units_sold"].sum())
            tot_rev = round(float(s_sales["revenue"].sum()), 2)
            days = s_sales["date"].nunique() or 1
            avg_daily = round(tot_rev / days, 2)

            so_count = stockouts_by_store.get(sid, 0)
            ds_count = dead_stock_by_store.get(sid, 0)

            # Operational health score: 100 base, penalizing active stockout risks and dead stock
            health = max(40, 100 - (so_count * 20) - (ds_count * 15))

            store_items.append({
                "store_id": sid,
                "store_name": s["store_name"],
                "city": s["city"],
                "total_units_sold": tot_units,
                "total_revenue": tot_rev,
                "avg_daily_revenue": avg_daily,
                "total_active_skus": len(self.products_df),
                "stockout_count": so_count,
                "dead_stock_count": ds_count,
                "health_score": health
            })

        # Rank stores by total revenue
        store_items.sort(key=lambda x: x["total_revenue"], reverse=True)

        # Category benchmarks
        merged_sales = pd.merge(self.sales_df, self.products_df[["product_id", "category", "product_name"]], on="product_id", how="left")
        cat_items = []

        for cat, grp in merged_sales.groupby("category"):
            c_units = int(grp["units_sold"].sum())
            c_rev = round(float(grp["revenue"].sum()), 2)
            c_share = round((c_rev / (total_chain_revenue or 1.0)) * 100, 1)

            # Top selling product in this category
            top_prod = grp.groupby("product_name")["units_sold"].sum().idxmax()

            cat_items.append({
                "category": cat,
                "total_units_sold": c_units,
                "total_revenue": c_rev,
                "revenue_share_pct": c_share,
                "top_selling_product": top_prod
            })

        cat_items.sort(key=lambda x: x["total_revenue"], reverse=True)

        return {
            "stores": store_items,
            "categories": cat_items,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_demand_forecast(self, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Computes deterministic 7-day & 14-day demand forecasts and projected stockout dates.
        
        Matches the Demand Forecasting Engine view:
        - Current Stock
        - Avg Daily Demand (recent 7d velocity)
        - 7-Day Demand Forecast
        - 14-Day Demand Forecast
        - Estimated Stockout Date (calendar date based on dataset max date)
        - Status Level: CRITICAL STOCK-OUT RISK, WARNING STOCK-OUT RISK, HEALTHY STOCK, DEAD STOCK
        """
        recent_start = self.max_date - timedelta(days=6)
        recent_sales = self.sales_df[self.sales_df["date"] >= recent_start]

        recent_agg = recent_sales.groupby(["store_id", "product_id"])["units_sold"].sum().reset_index()
        recent_agg["avg_daily_demand"] = recent_agg["units_sold"] / 7.0

        merged = pd.merge(self.inventory_df, recent_agg, on=["store_id", "product_id"], how="left")
        merged["avg_daily_demand"] = merged["avg_daily_demand"].fillna(0.0)

        if store_id and store_id != "all":
            merged = merged[merged["store_id"] == store_id]

        forecasts = []
        for _, row in merged.iterrows():
            sid = row["store_id"]
            pid = row["product_id"]
            curr_stock = int(row["current_stock"])
            daily_demand = float(row["avg_daily_demand"])

            d7 = round(daily_demand * 7.0, 1)
            d14 = round(daily_demand * 14.0, 1)

            if daily_demand > 0:
                days_left = round(curr_stock / daily_demand, 1)
                projected_dt = self.max_date + timedelta(days=float(days_left))
                est_date_str = projected_dt.strftime("%b %d, %Y")

                if days_left <= 3.0:
                    status_lvl = "CRITICAL STOCK-OUT RISK"
                    status_cls = "critical"
                    priority = 1
                elif days_left <= 7.0:
                    status_lvl = "WARNING STOCK-OUT RISK"
                    status_cls = "warning"
                    priority = 2
                else:
                    status_lvl = "HEALTHY STOCK"
                    status_cls = "healthy"
                    priority = 3
            else:
                days_left = None
                est_date_str = "Stable / No Depletion"
                status_lvl = "DEAD STOCK"
                status_cls = "dead"
                priority = 4

            forecasts.append({
                "product_id": pid,
                "product_name": self.product_map.get(pid, pid),
                "product_category": self.product_cat_map.get(pid, "General"),
                "store_id": sid,
                "store_name": self.store_map.get(sid, sid),
                "current_stock": curr_stock,
                "avg_daily_demand": round(daily_demand, 2),
                "demand_7d": d7,
                "demand_14d": d14,
                "days_remaining": days_left,
                "estimated_stockout_date": est_date_str,
                "status_level": status_lvl,
                "status_class": status_cls,
                "_priority": priority
            })

        # Sort critical items first, then by days remaining ascending
        forecasts.sort(key=lambda x: (x["_priority"], x["days_remaining"] if x["days_remaining"] is not None else 9999))
        for f in forecasts:
            del f["_priority"]

        return forecasts

