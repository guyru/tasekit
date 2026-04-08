"""Tests for tasekit.parsers."""

from __future__ import annotations

import pandas as pd
import pytest

from tasekit.parsers import (
    extract_security_name,
    parse_eod_csv,
    parse_etf_eod_csv,
    parse_index_eod_csv,
    parse_maya_fund_csv,
)
from tasekit.exceptions import TaseParsingError


class TestExtractSecurityName:
    """Tests for :func:`extract_security_name`."""

    def test_english_stock_name(self) -> None:
        csv = " Historical Data - End of Day LEUMI,,,,,,\nline2\n"
        assert extract_security_name(csv) == "LEUMI"

    def test_english_etf_name(self) -> None:
        csv = " Historical Data - End of Day ISHARES MSCI ACWI,,,,\n"
        assert extract_security_name(csv) == "ISHARES MSCI ACWI"

    def test_hebrew_stock_name(self) -> None:
        csv = (
            "\u05e0\u05ea\u05d5\u05e0\u05d9\u05dd \u05d4\u05d9\u05e1\u05d8\u05d5\u05e8\u05d9\u05d9\u05dd"
            " - \u05e1\u05d5\u05e3 \u05d9\u05d5\u05dd "
            "\u05dc\u05d0\u05d5\u05de\u05d9,,,,,,\n"
            "line2\n"
        )
        assert extract_security_name(csv) == "\u05dc\u05d0\u05d5\u05de\u05d9"

    def test_from_sample_fixture(self, sample_eod_csv: str) -> None:
        name = extract_security_name(sample_eod_csv)
        assert name is not None
        assert name == "LEUMI"

    def test_returns_none_for_garbage(self) -> None:
        assert extract_security_name("some random text") is None

    def test_returns_none_for_empty(self) -> None:
        assert extract_security_name("") is None


class TestParseEodCsv:
    """Tests for :func:`parse_eod_csv`."""

    def test_returns_dataframe_with_correct_columns(self, sample_eod_csv: str) -> None:
        df = parse_eod_csv(sample_eod_csv)
        assert list(df.columns) == ["Open", "High", "Low", "Close", "Adj Close", "Volume"]

    def test_index_is_datetime(self, sample_eod_csv: str) -> None:
        df = parse_eod_csv(sample_eod_csv)
        assert df.index.name == "Date"
        assert pd.api.types.is_datetime64_any_dtype(df.index)

    def test_rows_sorted_ascending(self, sample_eod_csv: str) -> None:
        df = parse_eod_csv(sample_eod_csv)
        assert df.index.is_monotonic_increasing

    def test_numeric_columns(self, sample_eod_csv: str) -> None:
        df = parse_eod_csv(sample_eod_csv)
        for col in df.columns:
            assert pd.api.types.is_numeric_dtype(df[col]), f"{col} is not numeric"

    def test_no_nan_in_ohlc(self, sample_eod_csv: str) -> None:
        df = parse_eod_csv(sample_eod_csv)
        for col in ["Open", "High", "Low", "Close", "Adj Close"]:
            assert not df[col].isna().any(), f"NaN found in {col}"

    def test_non_empty(self, sample_eod_csv: str) -> None:
        df = parse_eod_csv(sample_eod_csv)
        assert len(df) > 0

    def test_open_positive(self, sample_eod_csv: str) -> None:
        df = parse_eod_csv(sample_eod_csv)
        assert (df["Open"] > 0).all()

    def test_high_geq_low(self, sample_eod_csv: str) -> None:
        df = parse_eod_csv(sample_eod_csv)
        assert (df["High"] >= df["Low"]).all()

    def test_empty_csv_raises(self) -> None:
        csv = "title\ndate range\ncol1,col2\n"
        with pytest.raises(TaseParsingError):
            parse_eod_csv(csv)

    def test_garbage_raises(self) -> None:
        with pytest.raises(TaseParsingError):
            parse_eod_csv("")

    def test_missing_columns_raises(self) -> None:
        csv = "title\ndate range\nA,B,C\n1,2,3\n"
        with pytest.raises(TaseParsingError, match="Missing required columns"):
            parse_eod_csv(csv)


class TestParseEtfEodCsv:
    """Tests for :func:`parse_etf_eod_csv`."""

    def test_returns_dataframe_with_standard_columns(
        self, sample_etf_eod_csv: str
    ) -> None:
        df = parse_etf_eod_csv(sample_etf_eod_csv)
        for col in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
            assert col in df.columns, f"Missing standard column: {col}"

    def test_includes_etf_specific_columns(self, sample_etf_eod_csv: str) -> None:
        df = parse_etf_eod_csv(sample_etf_eod_csv)
        # The fixture has some rows with Purchase/Redemption/NAV/fees data.
        assert "Purchase Price" in df.columns
        assert "Redemption Price" in df.columns
        assert "NAV" in df.columns
        assert "Management Fee" in df.columns
        assert "Trustee Fee" in df.columns

    def test_includes_market_cap(self, sample_etf_eod_csv: str) -> None:
        df = parse_etf_eod_csv(sample_etf_eod_csv)
        assert "Market Cap" in df.columns

    def test_index_is_datetime(self, sample_etf_eod_csv: str) -> None:
        df = parse_etf_eod_csv(sample_etf_eod_csv)
        assert df.index.name == "Date"
        assert pd.api.types.is_datetime64_any_dtype(df.index)

    def test_rows_sorted_ascending(self, sample_etf_eod_csv: str) -> None:
        df = parse_etf_eod_csv(sample_etf_eod_csv)
        assert df.index.is_monotonic_increasing

    def test_numeric_columns(self, sample_etf_eod_csv: str) -> None:
        df = parse_etf_eod_csv(sample_etf_eod_csv)
        for col in df.columns:
            assert pd.api.types.is_numeric_dtype(df[col]), f"{col} is not numeric"

    def test_non_empty(self, sample_etf_eod_csv: str) -> None:
        df = parse_etf_eod_csv(sample_etf_eod_csv)
        assert len(df) > 0

    def test_open_positive(self, sample_etf_eod_csv: str) -> None:
        df = parse_etf_eod_csv(sample_etf_eod_csv)
        assert (df["Open"] > 0).all()

    def test_high_geq_low(self, sample_etf_eod_csv: str) -> None:
        df = parse_etf_eod_csv(sample_etf_eod_csv)
        assert (df["High"] >= df["Low"]).all()

    def test_omits_all_empty_etf_columns(self) -> None:
        """ETF-specific columns that are entirely empty should be omitted."""
        csv = (
            "title\ndate range\n"
            "Date,Adjusted Closing Price,Type,Closing Price (0.01 ILS),"
            "Change,Turnover (K ILS),Purchase Price,Redemption Price,"
            "Unit Price,LastUpdate,Base,Opening Price,Low Price,High Price,"
            "Chg,Volume,Txns,Market Cap (K ILS),Ex,Capital,"
            "Management Fee (%),Trustee Fee (%)\n"
            "01/01/2026,100.00,Closing Price,100.00,1.0,50.0,,,,"
            ",99.00,99.00,98.00,101.00,1.0,1000,10,5000,,1000,,\n"
        )
        df = parse_etf_eod_csv(csv)
        assert "Purchase Price" not in df.columns
        assert "Redemption Price" not in df.columns
        assert "NAV" not in df.columns
        assert "Management Fee" not in df.columns
        assert "Trustee Fee" not in df.columns

    def test_empty_csv_raises(self) -> None:
        csv = "title\ndate range\ncol1,col2\n"
        with pytest.raises(TaseParsingError):
            parse_etf_eod_csv(csv)

    def test_garbage_raises(self) -> None:
        with pytest.raises(TaseParsingError):
            parse_etf_eod_csv("")

    def test_missing_columns_raises(self) -> None:
        csv = "title\ndate range\nA,B,C\n1,2,3\n"
        with pytest.raises(TaseParsingError, match="Missing required columns"):
            parse_etf_eod_csv(csv)


class TestParseMayaFundCsv:
    """Tests for :func:`parse_maya_fund_csv`."""

    def test_returns_dataframe(self, sample_maya_csv: str) -> None:
        df = parse_maya_fund_csv(sample_maya_csv)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    def test_columns(self, sample_maya_csv: str) -> None:
        df = parse_maya_fund_csv(sample_maya_csv)
        assert list(df.columns) == ["Close"]

    def test_index_is_datetime(self, sample_maya_csv: str) -> None:
        df = parse_maya_fund_csv(sample_maya_csv)
        assert df.index.name == "Date"
        assert pd.api.types.is_datetime64_any_dtype(df.index)

    def test_sorted_ascending(self, sample_maya_csv: str) -> None:
        df = parse_maya_fund_csv(sample_maya_csv)
        assert df.index.is_monotonic_increasing

    def test_close_values(self, sample_maya_csv: str) -> None:
        df = parse_maya_fund_csv(sample_maya_csv)
        assert df["Close"].iloc[-1] == 295.51  # latest date after sort

    def test_empty_raises(self) -> None:
        with pytest.raises(TaseParsingError):
            parse_maya_fund_csv("")

    def test_too_few_columns_raises(self) -> None:
        csv = "A,B\n1,2\n"
        with pytest.raises(TaseParsingError, match="too few columns"):
            parse_maya_fund_csv(csv)


class TestParseIndexEodCsv:
    """Tests for :func:`parse_index_eod_csv`."""

    def test_returns_dataframe(self, sample_index_eod_csv: str) -> None:
        df = parse_index_eod_csv(sample_index_eod_csv)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_columns(self, sample_index_eod_csv: str) -> None:
        df = parse_index_eod_csv(sample_index_eod_csv)
        assert "Open" in df.columns
        assert "Close" in df.columns
        assert "Market Cap" in df.columns

    def test_index_is_datetime(self, sample_index_eod_csv: str) -> None:
        df = parse_index_eod_csv(sample_index_eod_csv)
        assert df.index.name == "Date"
        assert pd.api.types.is_datetime64_any_dtype(df.index)

    def test_sorted_ascending(self, sample_index_eod_csv: str) -> None:
        df = parse_index_eod_csv(sample_index_eod_csv)
        assert df.index.is_monotonic_increasing

    def test_close_positive(self, sample_index_eod_csv: str) -> None:
        df = parse_index_eod_csv(sample_index_eod_csv)
        assert (df["Close"] > 0).all()

    def test_empty_raises(self) -> None:
        with pytest.raises(TaseParsingError):
            parse_index_eod_csv("")

    def test_too_few_columns(self) -> None:
        csv = "title\nrange\nA,B\n1,2\n"
        with pytest.raises(TaseParsingError, match="too few columns"):
            parse_index_eod_csv(csv)
