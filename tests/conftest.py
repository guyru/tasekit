"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent / "data"


def _load_json(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture()
def hedge_detail() -> dict:
    """Maya ``funds/hedge/{id}`` detail for fund 1194141."""
    return _load_json("hedge_detail_1194141.json")


@pytest.fixture()
def hedge_metadata() -> dict:
    """Maya history-page metadata (monthly series list) for fund 1194141."""
    return _load_json("hedge_metadata_1194141.json")


@pytest.fixture()
def hedge_snapshot() -> list:
    """Current redemption snapshot (6 live series) for fund 1194141."""
    return _load_json("hedge_history_snapshot_1194141.json")


@pytest.fixture()
def hedge_anchor_history() -> list:
    """Full-life history of the anchor series 1194869 (41 monthly rows)."""
    return _load_json("hedge_history_anchor_1194869.json")


@pytest.fixture()
def hedge_list_page() -> list:
    """A page of the mutual hedge-fund listing (3 funds)."""
    return _load_json("hedge_list_page1.json")


@pytest.fixture()
def sample_eod_csv() -> str:
    """Return the raw CSV text of the sample EOD file."""
    return (DATA_DIR / "sample_eod.csv").read_text(encoding="utf-8-sig")


@pytest.fixture()
def sample_etf_eod_csv() -> str:
    """Return the raw CSV text of the sample ETF EOD file."""
    return (DATA_DIR / "sample_etf_eod.csv").read_text(encoding="utf-8-sig")


@pytest.fixture()
def sample_index_eod_csv() -> str:
    """Return the raw CSV text of the sample index EOD file."""
    return (DATA_DIR / "sample_index_eod.csv").read_text(encoding="utf-8-sig")


@pytest.fixture()
def sample_maya_csv() -> str:
    """Return a small Maya mutual-fund history CSV."""
    return (
        "\ufeff"
        "מס' קרן,תאריך,מחיר קניה,מחיר פדיון,דמי ניהול (%),שווי נכסים במיל' ₪,"
        "דמי נאמנות (%),שיעור הוספה (%)\n"
        "05122627,31.03.2026,295.51,295.51,0.000,2030.2,0.030,0.000\n"
        "05122627,30.03.2026,288.24,288.24,0.000,2030.2,0.030,0.000\n"
        "05122627,26.03.2026,289.83,289.83,0.000,2030.2,0.030,0.000\n"
    )
