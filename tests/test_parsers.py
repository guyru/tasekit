"""Tests for tasekit.parsers."""

from __future__ import annotations

import pandas as pd
import pytest

from tasekit.parsers import (
    add_hedge_fund_adj_close,
    extract_security_name,
    parse_eod_csv,
    parse_etf_eod_csv,
    parse_hedge_fund_history,
    parse_hedge_fund_list,
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


class TestParseHedgeFundHistory:
    """Tests for :func:`parse_hedge_fund_history`."""

    def test_basic_shape(self) -> None:
        rows = [
            {"fundId": "01194869", "tradeDate": "2026-05-28T00:00:00",
             "purchasePrice": 360.41, "sellPrice": 346.15},
            {"fundId": "01194869", "tradeDate": "2026-04-30T00:00:00",
             "purchasePrice": 349.94, "sellPrice": 337.78},
        ]
        df = parse_hedge_fund_history(rows)

        assert list(df.columns) == ["Gross", "Net"]
        assert df.index.name == "Date"
        # Sorted ascending.
        assert df.index[0] < df.index[1]
        assert df["Net"].iloc[-1] == 346.15

    def test_empty_raises(self) -> None:
        with pytest.raises(TaseParsingError):
            parse_hedge_fund_history([])

    def test_real_anchor_fixture(self, hedge_anchor_history: list) -> None:
        df = parse_hedge_fund_history(hedge_anchor_history)
        assert len(df) == 41
        assert df["Gross"].iloc[0] == 100.0


class TestParseHedgeFundList:
    """Tests for :func:`parse_hedge_fund_list`."""

    def test_basic_shape(self) -> None:
        rows = [
            {"fundId": 1194166, "name": "B", "managerName": "SIGMA",
             "trusteeName": "HERMETIC", "managementFee": 2.0, "successFee": 20.0,
             "trusteeFee": 0.04, "assetValue": 113.0, "taxStatusName": "Tax Exempt",
             "classification": {"major": "Hedge fund"}},
            {"fundId": 1194141, "name": "A", "managerName": "HAREL",
             "trusteeName": "UBANK", "managementFee": 1.5, "successFee": 20.0,
             "trusteeFee": 0.04, "assetValue": 1244.3, "taxStatusName": "Tax Exempt",
             "classification": {"major": "Hedge fund"}},
        ]
        df = parse_hedge_fund_list(rows)

        assert df.index.name == "Fund ID"
        assert list(df.columns) == [
            "Name", "Manager", "Trustee", "Management Fee", "Success Fee",
            "Trustee Fee", "AUM", "Tax Status", "Classification",
        ]
        # Sorted ascending by numeric fund ID.
        assert list(df.index) == ["1194141", "1194166"]
        assert df.loc["1194141", "Manager"] == "HAREL"
        assert df.loc["1194141", "AUM"] == 1244.3

    def test_handles_missing_classification(self) -> None:
        df = parse_hedge_fund_list([{"fundId": 1, "name": "X", "classification": None}])
        assert df.loc["1", "Classification"] is None

    def test_empty_raises(self) -> None:
        with pytest.raises(TaseParsingError):
            parse_hedge_fund_list([])

    def test_real_fixture(self, hedge_list_page: list) -> None:
        df = parse_hedge_fund_list(hedge_list_page)
        assert len(df) == 3
        assert "1194141" in df.index


class TestAddHedgeFundAdjClose:
    """Tests for :func:`add_hedge_fund_adj_close`."""

    def test_removes_reset_jumps(self, hedge_anchor_history: list) -> None:
        df = add_hedge_fund_adj_close(parse_hedge_fund_history(hedge_anchor_history))

        # Gross is continuous: full-life ratio ~3.6041.
        gross_ratio = df["Gross"].iloc[-1] / df["Gross"].iloc[0]
        assert gross_ratio == pytest.approx(3.6041, abs=1e-3)

        # Net total return with reset jumps removed ~2.952.
        net_tr = df["Adj Close"].iloc[-1] / df["Adj Close"].iloc[0]
        assert net_tr == pytest.approx(2.952, abs=1e-3)

        # Recent == actual (yfinance convention).
        assert df["Adj Close"].iloc[-1] == pytest.approx(df["Net"].iloc[-1])

    def test_adj_close_has_no_reset_spike(self, hedge_anchor_history: list) -> None:
        df = add_hedge_fund_adj_close(parse_hedge_fund_history(hedge_anchor_history))
        # The raw net jumps +9.6% across 2025-12-31 -> 2026-01-01; Adj Close
        # must not (value is preserved across crystallization).
        adj = df["Adj Close"]
        step = adj.loc["2026-01-01"] / adj.loc["2025-12-31"]
        assert step == pytest.approx(1.0, abs=1e-6)

    def test_single_row(self) -> None:
        df = parse_hedge_fund_history(
            [{"fundId": "1", "tradeDate": "2026-05-28", "purchasePrice": 10.0,
              "sellPrice": 9.0}]
        )
        out = add_hedge_fund_adj_close(df)
        assert out["Adj Close"].iloc[0] == 9.0

    def test_mid_period_net_meets_gross_is_not_a_reset(self) -> None:
        """A success-fee fund whose gross falls to its high-water mark mid-year
        has ``net == gross`` with *no* crystallization.  The genuine loss must
        be kept, so net return can never exceed gross return (fee drag >= 0)."""
        rows = [
            # Inception.
            {"fundId": "1", "tradeDate": "2025-01-01", "purchasePrice": 100.0,
             "sellPrice": 100.0},
            # Gross rises, success + management fees accrue (net < gross).
            {"fundId": "1", "tradeDate": "2025-02-27", "purchasePrice": 102.34,
             "sellPrice": 101.87},
            # Gross *falls* 6.9% below the high-water mark: success fee zeroes
            # out so net rises to meet gross, but this is NOT a reset.
            {"fundId": "1", "tradeDate": "2025-03-31", "purchasePrice": 95.29,
             "sellPrice": 95.29},
        ]
        df = add_hedge_fund_adj_close(parse_hedge_fund_history(rows))

        # The -6.5% net move must survive (old bug froze Adj Close flat).
        adj_step = df["Adj Close"].iloc[-1] / df["Adj Close"].iloc[-2]
        assert adj_step == pytest.approx(95.29 / 101.87, abs=1e-6)

        # Net return must not exceed gross return (net = gross - fees).
        gross_ratio = df["Gross"].iloc[-1] / df["Gross"].iloc[0]
        net_ratio = df["Adj Close"].iloc[-1] / df["Adj Close"].iloc[0]
        assert net_ratio <= gross_ratio + 1e-9

    def test_real_year_end_reset_is_removed(self) -> None:
        """A true crystallization (net jumps up to meet gross at the year boundary)
        is detected and removed."""
        rows = [
            {"fundId": "1", "tradeDate": "2025-12-01", "purchasePrice": 150.0,
             "sellPrice": 140.0},
            {"fundId": "1", "tradeDate": "2025-12-31", "purchasePrice": 160.0,
             "sellPrice": 148.0},
            # One-day-apart reset: gross flat, net jumps up to gross.
            {"fundId": "1", "tradeDate": "2026-01-01", "purchasePrice": 160.0,
             "sellPrice": 160.0},
        ]
        df = add_hedge_fund_adj_close(parse_hedge_fund_history(rows))
        step = df["Adj Close"].loc["2026-01-01"] / df["Adj Close"].loc["2025-12-31"]
        assert step == pytest.approx(1.0, abs=1e-6)

    def test_year_end_reset_detected_when_gross_moves(self) -> None:
        """A crystallization where gross moved >0.5% at the year boundary must
        still be detected.  The old gross_flat check caused this to be missed,
        inflating Adj Close and making net CAGR > gross CAGR."""
        rows = [
            {"fundId": "1", "tradeDate": "2025-12-31", "purchasePrice": 160.0,
             "sellPrice": 148.0},
            # Reset: gross moved 0.625% (above the old 0.5% step_tol), net jumps
            # up to the new gross.  Must still be treated as a crystallization.
            {"fundId": "1", "tradeDate": "2026-01-01", "purchasePrice": 161.0,
             "sellPrice": 161.0},
        ]
        df = add_hedge_fund_adj_close(parse_hedge_fund_history(rows))
        step = df["Adj Close"].loc["2026-01-01"] / df["Adj Close"].loc["2025-12-31"]
        assert step == pytest.approx(1.0, abs=1e-6)
