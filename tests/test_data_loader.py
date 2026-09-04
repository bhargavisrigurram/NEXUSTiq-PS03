"""Unit tests for data loader and validation."""
import pytest
from pathlib import Path
import pandas as pd

from src.data_loader import DataLoader, DataValidationError
from src.config import DATA_DIR

def test_data_loader_valid_dataset():
    """Verify loading and integrity validation on generated synthetic dataset."""
    loader = DataLoader(DATA_DIR)
    data = loader.load_and_validate()

    assert "stores" in data
    assert "products" in data
    assert "sales" in data
    assert "inventory" in data

    assert len(data["stores"]) == 4
    assert len(data["products"]) == 25
    assert len(data["sales"]) > 5000
    assert len(data["inventory"]) == 100

def test_date_gap_vs_zero_sales():
    """Case 6: Distinguish missing date gap from explicit zero-sale records."""
    loader = DataLoader(DATA_DIR)
    loader.load_and_validate()

    # Product P03 in Store S02 has a 5-day date gap and explicit zero-sale days
    missing_dates, zero_sales = loader.detect_date_gaps("S02", "P03")
    assert len(missing_dates) >= 5
    assert zero_sales >= 3
