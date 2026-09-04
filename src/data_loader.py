"""Data loading and integrity validation module for retail dataset."""
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np

from src.config import DATA_DIR

class DataValidationError(Exception):
    """Raised when data integrity validation fails."""
    pass

class DataLoader:
    """Loads and validates retail datasets (stores, products, sales, inventory)."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        self.stores_df: Optional[pd.DataFrame] = None
        self.products_df: Optional[pd.DataFrame] = None
        self.sales_df: Optional[pd.DataFrame] = None
        self.inventory_df: Optional[pd.DataFrame] = None
        self.validation_errors: List[str] = []

    def load_and_validate(self) -> Dict[str, pd.DataFrame]:
        """Loads all four datasets, performs strict validation, and returns them."""
        self.validation_errors.clear()

        # 1. File existence checks
        required_files = ["stores.csv", "products.csv", "sales.csv", "inventory.csv"]
        for fname in required_files:
            fpath = self.data_dir / fname
            if not fpath.exists():
                raise FileNotFoundError(f"Required dataset file missing: {fpath}")

        # 2. Load CSVs
        self.stores_df = pd.read_csv(self.data_dir / "stores.csv")
        self.products_df = pd.read_csv(self.data_dir / "products.csv")
        self.sales_df = pd.read_csv(self.data_dir / "sales.csv")
        self.inventory_df = pd.read_csv(self.data_dir / "inventory.csv")

        # 3. Validate Stores
        store_cols = {"store_id", "store_name", "city"}
        if not store_cols.issubset(self.stores_df.columns):
            self.validation_errors.append(f"stores.csv missing columns: {store_cols - set(self.stores_df.columns)}")
        if self.stores_df["store_id"].duplicated().any():
            self.validation_errors.append("Duplicate store_id found in stores.csv")

        # 4. Validate Products
        product_cols = {"product_id", "product_name", "category", "unit_price", "reorder_level"}
        if not product_cols.issubset(self.products_df.columns):
            self.validation_errors.append(f"products.csv missing columns: {product_cols - set(self.products_df.columns)}")
        if self.products_df["product_id"].duplicated().any():
            self.validation_errors.append("Duplicate product_id found in products.csv")
        if (self.products_df["unit_price"] <= 0).any():
            self.validation_errors.append("Found non-positive unit_price in products.csv")

        # 5. Validate Sales
        sales_cols = {"date", "store_id", "product_id", "units_sold", "revenue"}
        if not sales_cols.issubset(self.sales_df.columns):
            self.validation_errors.append(f"sales.csv missing columns: {sales_cols - set(self.sales_df.columns)}")
        if (self.sales_df["units_sold"] < 0).any():
            self.validation_errors.append("Found negative units_sold in sales.csv")
        if (self.sales_df["revenue"] < 0).any():
            self.validation_errors.append("Found negative revenue in sales.csv")

        # Check duplicate (date, store_id, product_id)
        dup_sales = self.sales_df.duplicated(subset=["date", "store_id", "product_id"]).sum()
        if dup_sales > 0:
            self.validation_errors.append(f"Found {dup_sales} duplicate (date, store_id, product_id) records in sales.csv")

        # 6. Validate Inventory
        inv_cols = {"store_id", "product_id", "current_stock"}
        if not inv_cols.issubset(self.inventory_df.columns):
            self.validation_errors.append(f"inventory.csv missing columns: {inv_cols - set(self.inventory_df.columns)}")
        if (self.inventory_df["current_stock"] < 0).any():
            self.validation_errors.append("Found negative current_stock in inventory.csv")
        if self.inventory_df.duplicated(subset=["store_id", "product_id"]).any():
            self.validation_errors.append("Duplicate (store_id, product_id) found in inventory.csv")

        # 7. Foreign Key Integrity
        valid_store_ids = set(self.stores_df["store_id"])
        valid_product_ids = set(self.products_df["product_id"])

        invalid_sales_stores = set(self.sales_df["store_id"]) - valid_store_ids
        if invalid_sales_stores:
            self.validation_errors.append(f"sales.csv references unknown store_ids: {invalid_sales_stores}")

        invalid_sales_products = set(self.sales_df["product_id"]) - valid_product_ids
        if invalid_sales_products:
            self.validation_errors.append(f"sales.csv references unknown product_ids: {invalid_sales_products}")

        invalid_inv_stores = set(self.inventory_df["store_id"]) - valid_store_ids
        if invalid_inv_stores:
            self.validation_errors.append(f"inventory.csv references unknown store_ids: {invalid_inv_stores}")

        invalid_inv_products = set(self.inventory_df["product_id"]) - valid_product_ids
        if invalid_inv_products:
            self.validation_errors.append(f"inventory.csv references unknown product_ids: {invalid_inv_products}")

        # Date normalization
        self.sales_df["date"] = pd.to_datetime(self.sales_df["date"])
        self.sales_df = self.sales_df.sort_values(by=["store_id", "product_id", "date"]).reset_index(drop=True)

        if self.validation_errors:
            error_msg = "; ".join(self.validation_errors)
            raise DataValidationError(f"Dataset validation failed: {error_msg}")

        return {
            "stores": self.stores_df,
            "products": self.products_df,
            "sales": self.sales_df,
            "inventory": self.inventory_df
        }

    def detect_date_gaps(self, store_id: str, product_id: str) -> Tuple[List[str], int]:
        """Detects missing dates in the recorded timeline for a store-product combination.
        
        Distinguishes missing dates from recorded 0-unit sales.
        Returns: (list_of_missing_date_strings, count_of_recorded_zero_sales)
        """
        if self.sales_df is None:
            self.load_and_validate()

        subset = self.sales_df[
            (self.sales_df["store_id"] == store_id) & 
            (self.sales_df["product_id"] == product_id)
        ]

        if subset.empty:
            return [], 0

        # Count explicit zero sales
        zero_sales_count = int((subset["units_sold"] == 0).sum())

        # Determine full date range from overall dataset
        min_date = self.sales_df["date"].min()
        max_date = self.sales_df["date"].max()
        full_date_range = pd.date_range(start=min_date, end=max_date)

        recorded_dates = set(subset["date"].dt.strftime("%Y-%m-%d"))
        all_dates = set(full_date_range.strftime("%Y-%m-%d"))

        missing_dates = sorted(list(all_dates - recorded_dates))
        return missing_dates, zero_sales_count
