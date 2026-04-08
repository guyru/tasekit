"""Tests for tasekit.index.Index."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from tasekit.index import Index
from tasekit.api import TaseClient
from tasekit.exceptions import SecurityNotFoundError


SAMPLE_INDEX_DETAILS = {
    "Id": "142",
    "Name": "TA-35",
    "Description": "The TA-35 Index is the TASE's flagship index.",
    "BaseRate": 4189.31,
    "OpenRate": 4197.94,
    "HighRate": 4248.43,
    "LowRate": 4193.94,
    "LastRate": 4248.43,
    "Change": 1.41,
    "MonthYield": 3.65,
    "AnnualYield": 16.99,
    "MarketValue": 1254234.0,
    "MarketValueDate": "06/04/2026",
    "TradeDate": "06/04/2026",
    "IsBond": False,
}


@pytest.fixture()
def mock_client(sample_index_eod_csv: str) -> TaseClient:
    client = MagicMock(spec=TaseClient)
    client.fetch_index_eod_csv.return_value = sample_index_eod_csv
    client.fetch_index_details.return_value = SAMPLE_INDEX_DETAILS
    return client


class TestIndexInit:
    def test_accepts_numeric_id(self) -> None:
        idx = Index("142")
        assert idx.id == "142"

    def test_rejects_non_numeric(self) -> None:
        with pytest.raises(ValueError, match="must be numeric"):
            Index("TA-35")


class TestIndexHistory:
    def test_returns_dataframe(self, mock_client: TaseClient) -> None:
        df = Index("142", client=mock_client).history()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_columns(self, mock_client: TaseClient) -> None:
        df = Index("142", client=mock_client).history()
        assert "Open" in df.columns
        assert "Close" in df.columns

    def test_default_years(self, mock_client: TaseClient) -> None:
        Index("142", client=mock_client).history()
        assert mock_client.fetch_index_eod_csv.call_args[0][1] == 5  # 2y → ptype 5

    def test_days_param(self, mock_client: TaseClient) -> None:
        Index("142", client=mock_client).history(days=30)
        assert mock_client.fetch_index_eod_csv.call_args[0][1] == 1

    def test_start_trims(self, mock_client: TaseClient) -> None:
        df = Index("142", client=mock_client).history(start="2026-03-25")
        assert df.index.min() >= pd.Timestamp("2026-03-25")

    def test_end_trims(self, mock_client: TaseClient) -> None:
        df = Index("142", client=mock_client).history(end="2026-03-20")
        assert df.index.max() <= pd.Timestamp("2026-03-20")

    def test_empty_range_raises(self, mock_client: TaseClient) -> None:
        with pytest.raises(SecurityNotFoundError):
            Index("142", client=mock_client).history(
                start="2099-01-01", end="2099-12-31"
            )


class TestIndexInfo:
    def test_basic_fields(self, mock_client: TaseClient) -> None:
        info = Index("142", client=mock_client).info()
        assert info["name"] == "TA-35"
        assert info["id"] == "142"
        assert info["last_rate"] == 4248.43
        assert info["change_pct"] == 1.41

    def test_rates(self, mock_client: TaseClient) -> None:
        info = Index("142", client=mock_client).info()
        assert info["base_rate"] == 4189.31
        assert info["high_rate"] == 4248.43
        assert info["low_rate"] == 4193.94

    def test_yields(self, mock_client: TaseClient) -> None:
        info = Index("142", client=mock_client).info()
        assert info["month_yield"] == 3.65
        assert info["annual_yield"] == 16.99

    def test_market_value(self, mock_client: TaseClient) -> None:
        info = Index("142", client=mock_client).info()
        assert info["market_value"] == 1254234.0

    def test_description(self, mock_client: TaseClient) -> None:
        info = Index("142", client=mock_client).info()
        assert "flagship" in info["description"]

    def test_not_found_raises(self) -> None:
        client = MagicMock(spec=TaseClient)
        client.fetch_index_details.return_value = {"Name": None}
        with pytest.raises(SecurityNotFoundError):
            Index("999", client=client).info()
