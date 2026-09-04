"""Generate realistic synthetic retail sales and inventory dataset with 6 mandatory hard cases.

Generates:
1. data/stores.csv
2. data/products.csv
3. data/sales.csv
4. data/inventory.csv
"""
import os
import random
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Set random seeds for deterministic reproducibility
random.seed(42)
np.random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = datetime(2026, 6, 15)
END_DATE = datetime(2026, 8, 28)
NUM_DAYS = (END_DATE - START_DATE).days + 1  # 75 days

def generate_stores():
    stores = [
        {"store_id": "S01", "store_name": "Store Hyderabad", "city": "Hyderabad", "region": "South", "sqft": 4500, "manager": "Ramesh Kumar"},
        {"store_id": "S02", "store_name": "Store Vijayawada", "city": "Vijayawada", "region": "South", "sqft": 3200, "manager": "Lakshmi Narayana"},
        {"store_id": "S03", "store_name": "Store Chennai", "city": "Chennai", "region": "South", "sqft": 5100, "manager": "Anand Sundaram"},
        {"store_id": "S04", "store_name": "Store Bengaluru", "city": "Bengaluru", "region": "South", "sqft": 6000, "manager": "Pooja Hegde"},
    ]
    df = pd.DataFrame(stores)
    df.to_csv(DATA_DIR / "stores.csv", index=False)
    print(f"Generated {len(df)} stores -> {DATA_DIR / 'stores.csv'}")
    return df

def generate_products():
    products = [
        # Beverages
        {"product_id": "P01", "product_name": "Sparkle Water 1L", "category": "Beverages", "unit_price": 45.0, "cost_price": 25.0, "reorder_level": 50, "typical_daily_sales": 15},
        {"product_id": "P02", "product_name": "Fresh Orange Juice 500ml", "category": "Beverages", "unit_price": 85.0, "cost_price": 50.0, "reorder_level": 40, "typical_daily_sales": 12},
        {"product_id": "P03", "product_name": "Cold Brew Coffee 250ml", "category": "Beverages", "unit_price": 120.0, "cost_price": 70.0, "reorder_level": 30, "typical_daily_sales": 8},
        {"product_id": "P04", "product_name": "Masala Chai Premix 200g", "category": "Beverages", "unit_price": 160.0, "cost_price": 95.0, "reorder_level": 25, "typical_daily_sales": 6},
        {"product_id": "P05", "product_name": "Energy Boost 250ml", "category": "Beverages", "unit_price": 110.0, "cost_price": 60.0, "reorder_level": 45, "typical_daily_sales": 10},

        # Snacks
        {"product_id": "P06", "product_name": "Artisanal Butter Cookies 200g", "category": "Snacks", "unit_price": 150.0, "cost_price": 85.0, "reorder_level": 35, "typical_daily_sales": 14},
        {"product_id": "P07", "product_name": "Roasted Almonds 150g", "category": "Snacks", "unit_price": 240.0, "cost_price": 160.0, "reorder_level": 20, "typical_daily_sales": 5},
        {"product_id": "P08", "product_name": "Spicy Banana Chips 100g", "category": "Snacks", "unit_price": 60.0, "cost_price": 30.0, "reorder_level": 50, "typical_daily_sales": 16},
        {"product_id": "P09", "product_name": "Multigrain Crackers 150g", "category": "Snacks", "unit_price": 90.0, "cost_price": 50.0, "reorder_level": 30, "typical_daily_sales": 9},
        {"product_id": "P10", "product_name": "Dark Chocolate 80g", "category": "Snacks", "unit_price": 130.0, "cost_price": 75.0, "reorder_level": 25, "typical_daily_sales": 7},

        # Packaged Food
        {"product_id": "P11", "product_name": "Basmati Rice 5kg", "category": "Packaged Food", "unit_price": 550.0, "cost_price": 380.0, "reorder_level": 20, "typical_daily_sales": 4},
        {"product_id": "P12", "product_name": "Cold Pressed Mustard Oil 1L", "category": "Packaged Food", "unit_price": 260.0, "cost_price": 180.0, "reorder_level": 25, "typical_daily_sales": 5},
        {"product_id": "P13", "product_name": "Organic Quinoa 500g", "category": "Packaged Food", "unit_price": 320.0, "cost_price": 210.0, "reorder_level": 15, "typical_daily_sales": 3},
        {"product_id": "P14", "product_name": "Durum Wheat Pasta 500g", "category": "Packaged Food", "unit_price": 140.0, "cost_price": 80.0, "reorder_level": 30, "typical_daily_sales": 8},
        {"product_id": "P15", "product_name": "Instant Oats 1kg", "category": "Packaged Food", "unit_price": 190.0, "cost_price": 120.0, "reorder_level": 25, "typical_daily_sales": 7},

        # Personal Care
        {"product_id": "P16", "product_name": "Herbal Shampoo 250ml", "category": "Personal Care", "unit_price": 210.0, "cost_price": 125.0, "reorder_level": 20, "typical_daily_sales": 5},
        {"product_id": "P17", "product_name": "Neem Face Wash 150ml", "category": "Personal Care", "unit_price": 175.0, "cost_price": 95.0, "reorder_level": 25, "typical_daily_sales": 6},
        {"product_id": "P18", "product_name": "Organic Lip Balm 15g", "category": "Personal Care", "unit_price": 125.0, "cost_price": 60.0, "reorder_level": 30, "typical_daily_sales": 4},
        {"product_id": "P19", "product_name": "Moisturizing Lotion 200ml", "category": "Personal Care", "unit_price": 280.0, "cost_price": 170.0, "reorder_level": 15, "typical_daily_sales": 3},
        {"product_id": "P20", "product_name": "Bamboo Toothbrush 4pk", "category": "Personal Care", "unit_price": 180.0, "cost_price": 90.0, "reorder_level": 20, "typical_daily_sales": 4},

        # Household
        {"product_id": "P21", "product_name": "Biodegradable Dish Soap 500ml", "category": "Household", "unit_price": 145.0, "cost_price": 80.0, "reorder_level": 30, "typical_daily_sales": 8},
        {"product_id": "P22", "product_name": "Lavender Floor Cleaner 1L", "category": "Household", "unit_price": 220.0, "cost_price": 130.0, "reorder_level": 25, "typical_daily_sales": 6},
        {"product_id": "P23", "product_name": "Recycled Paper Towels 2pk", "category": "Household", "unit_price": 160.0, "cost_price": 95.0, "reorder_level": 35, "typical_daily_sales": 9},
        {"product_id": "P24", "product_name": "Microfiber Cloth 3pk", "category": "Household", "unit_price": 135.0, "cost_price": 70.0, "reorder_level": 25, "typical_daily_sales": 5},
        {"product_id": "P25", "product_name": "Compostable Waste Bags 30pk", "category": "Household", "unit_price": 195.0, "cost_price": 110.0, "reorder_level": 20, "typical_daily_sales": 5},
    ]
    df = pd.DataFrame(products)
    df.to_csv(DATA_DIR / "products.csv", index=False)
    print(f"Generated {len(df)} products -> {DATA_DIR / 'products.csv'}")
    return df

def generate_sales_and_inventory(stores_df, products_df):
    sales_records = []
    inventory_records = []

    price_map = {row["product_id"]: row["unit_price"] for _, row in products_df.iterrows()}
    base_sales_map = {row["product_id"]: row["typical_daily_sales"] for _, row in products_df.iterrows()}

    # Generate dates
    date_list = [START_DATE + timedelta(days=i) for i in range(NUM_DAYS)]
    recent_7_start = END_DATE - timedelta(days=6)
    prev_14_start = END_DATE - timedelta(days=20)
    prev_14_end = END_DATE - timedelta(days=7)

    for store_id in stores_df["store_id"]:
        for prod_id in products_df["product_id"]:
            # CASE 5: Missing/Null Data
            # Store S03 (Chennai) + Product P17 (Neem Face Wash) -> NO SALES DATA AT ALL!
            if store_id == "S03" and prod_id == "P17":
                # Create inventory entry to show product is in catalogue, but zero sales records ever logged
                inventory_records.append({
                    "store_id": store_id,
                    "product_id": prod_id,
                    "current_stock": 40,
                    "last_restocked_date": "2026-06-10",
                    "reorder_quantity": 30
                })
                continue

            base_rate = base_sales_map[prod_id]

            # Store specific adjustments
            if store_id == "S01":  # Hyderabad
                store_multiplier = 1.15
            elif store_id == "S02": # Vijayawada
                store_multiplier = 0.85
            elif store_id == "S03": # Chennai
                store_multiplier = 1.05
            else: # Bengaluru
                store_multiplier = 1.25

            expected_daily = max(1, int(round(base_rate * store_multiplier)))

            # Track cumulative sales in the last 7 days and last 14 days for exact inventory calibration
            recent_7_sales = 0
            recent_14_sales = 0

            for d in date_list:
                date_str = d.strftime("%Y-%m-%d")

                # CASE 6: Date gap vs zero sales
                # Product P03 (Cold Brew Coffee) at Store S02 (Vijayawada):
                # 5 days missing completely: 2026-07-10 to 2026-07-14
                if store_id == "S02" and prod_id == "P03" and datetime(2026, 7, 10) <= d <= datetime(2026, 7, 14):
                    continue  # Deliberate missing row (not 0 sales, completely absent record)

                # CASE 6 (b): Explicit Zero Sales recorded on 2026-07-20 to 2026-07-22
                if store_id == "S02" and prod_id == "P03" and datetime(2026, 7, 20) <= d <= datetime(2026, 7, 22):
                    units_sold = 0
                    revenue = 0.0
                    sales_records.append({
                        "date": date_str,
                        "store_id": store_id,
                        "product_id": prod_id,
                        "units_sold": units_sold,
                        "revenue": revenue
                    })
                    continue

                # CASE 1: Imminent Stockout
                # P02 (Fresh Orange Juice 500ml) at S01 (Hyderabad):
                # In last 7 days, exact daily sales = 11. (77 total in 7 days, avg = 11.0).
                # Current stock will be set to exactly 8 units -> 8 / 11.0 = 0.73 days of stock!
                if store_id == "S01" and prod_id == "P02":
                    if d >= recent_7_start:
                        units_sold = 11
                    elif prev_14_start <= d <= prev_14_end:
                        units_sold = 12
                    else:
                        units_sold = random.choice([10, 11, 12, 13])

                # Case 1 (b): P01 (Sparkle Water 1L) at S01 (Hyderabad):
                # In last 7 days, exact daily sales = 18. (Avg = 18.0).
                # Current stock set to 24 units -> 24 / 18.0 = 1.33 days of stock!
                elif store_id == "S01" and prod_id == "P01":
                    if d >= recent_7_start:
                        units_sold = 18
                    elif prev_14_start <= d <= prev_14_end:
                        units_sold = 16
                    else:
                        units_sold = random.choice([14, 15, 16, 17, 18])

                # CASE 2: Dead / Non-Moving Stock
                # P12 (Cold Pressed Mustard Oil 1L) at S02 (Vijayawada):
                # Zero sales in the last 14 days! Current stock = 87 units.
                elif store_id == "S02" and prod_id == "P12":
                    if d >= (END_DATE - timedelta(days=13)):
                        units_sold = 0
                    else:
                        units_sold = random.choice([0, 1, 2])

                # Case 2 (b): P18 (Organic Lip Balm 15g) at S03 (Chennai):
                # Zero sales in the last 14 days! Current stock = 65 units.
                elif store_id == "S03" and prod_id == "P18":
                    if d >= (END_DATE - timedelta(days=13)):
                        units_sold = 0
                    else:
                        units_sold = random.choice([0, 1, 2])

                # CASE 3: Sales Spike
                # P05 (Energy Boost 250ml) at S04 (Bengaluru):
                # Previous 14-day average = 10.0/day. Recent 7-day average = 29.0/day (+190% increase!).
                elif store_id == "S04" and prod_id == "P05":
                    if d >= recent_7_start:
                        units_sold = 29
                    elif prev_14_start <= d <= prev_14_end:
                        units_sold = 10
                    else:
                        units_sold = random.choice([8, 9, 10, 11])

                # CASE 4: Sales Drop
                # P06 (Artisanal Butter Cookies 200g) at S01 (Hyderabad):
                # Previous 14-day average = 20.0/day. Recent 7-day average = 5.0/day (-75% drop!).
                elif store_id == "S01" and prod_id == "P06":
                    if d >= recent_7_start:
                        units_sold = 5
                    elif prev_14_start <= d <= prev_14_end:
                        units_sold = 20
                    else:
                        units_sold = random.choice([18, 19, 20, 21])

                # Normal random sales around expected_daily with realistic weekly fluctuations
                else:
                    weekday = d.weekday()
                    weekend_boost = 1.3 if weekday in (5, 6) else 1.0
                    noise = random.uniform(0.7, 1.3)
                    units_sold = max(0, int(round(expected_daily * weekend_boost * noise)))

                revenue = round(units_sold * price_map[prod_id], 2)
                sales_records.append({
                    "date": date_str,
                    "store_id": store_id,
                    "product_id": prod_id,
                    "units_sold": units_sold,
                    "revenue": revenue
                })

                if d >= recent_7_start:
                    recent_7_sales += units_sold
                if d >= (END_DATE - timedelta(days=13)):
                    recent_14_sales += units_sold

            # Current Inventory Level Settings
            if store_id == "S01" and prod_id == "P02":
                current_stock = 8    # Case 1: 8 units / 11 avg = 0.73 days cover
            elif store_id == "S01" and prod_id == "P01":
                current_stock = 24   # Case 1 (b): 24 units / 18 avg = 1.33 days cover
            elif store_id == "S02" and prod_id == "P12":
                current_stock = 87   # Case 2: 87 units, 0 sales in 14 days
            elif store_id == "S03" and prod_id == "P18":
                current_stock = 65   # Case 2 (b): 65 units, 0 sales in 14 days
            elif store_id == "S04" and prod_id == "P05":
                current_stock = 140  # Case 3: Spiking item, healthy stock but accelerating
            elif store_id == "S01" and prod_id == "P06":
                current_stock = 95   # Case 4: Dropping item, risk of excess inventory
            else:
                # Balanced standard inventory covering ~8-14 days
                avg_daily = recent_7_sales / 7.0 if recent_7_sales > 0 else 5.0
                current_stock = int(round(avg_daily * random.uniform(8.0, 14.0)))

            inventory_records.append({
                "store_id": store_id,
                "product_id": prod_id,
                "current_stock": current_stock,
                "last_restocked_date": (END_DATE - timedelta(days=random.randint(3, 18))).strftime("%Y-%m-%d"),
                "reorder_quantity": int(round(base_sales_map[prod_id] * 10))
            })

    sales_df = pd.DataFrame(sales_records)
    sales_df.to_csv(DATA_DIR / "sales.csv", index=False)
    print(f"Generated {len(sales_df)} sales records -> {DATA_DIR / 'sales.csv'}")

    inv_df = pd.DataFrame(inventory_records)
    inv_df.to_csv(DATA_DIR / "inventory.csv", index=False)
    print(f"Generated {len(inv_df)} inventory records -> {DATA_DIR / 'inventory.csv'}")

    return sales_df, inv_df

if __name__ == "__main__":
    print("=== Generating Synthetic Retail Dataset for NexusTiq24 PS03 ===")
    stores = generate_stores()
    products = generate_products()
    sales, inv = generate_sales_and_inventory(stores, products)
    print("Dataset generation successfully completed.")
