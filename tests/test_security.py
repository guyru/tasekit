"""Tests for tasekit.security.Security."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from tasekit.security import Security
from tasekit.api import TaseClient
from tasekit.exceptions import SecurityNotFoundError, TaseNetworkError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_MAYA_CSV = (
    "\ufeff"
    "מס' קרן,תאריך,מחיר קניה,מחיר פדיון,דמי ניהול (%),שווי נכסים במיל' ₪,"
    "דמי נאמנות (%),שיעור הוספה (%)\n"
    "05122627,31.03.2026,295.51,295.51,0.000,2030.2,0.030,0.000\n"
    "05122627,30.03.2026,288.24,288.24,0.000,2030.2,0.030,0.000\n"
    "05122627,26.03.2026,289.83,289.83,0.000,2030.2,0.030,0.000\n"
)

SAMPLE_SECURITY_DATA_EN = {
    "Name": "LEUMI",
    "SecurityLongName": "BANK LEUMI LE- ISRAEL B.M.",
    "LongName": None,
    "CompanyName": "LEUMI BANK",
    "Symbol": "LUMI",
    "ISIN": "IL0006046119",
    "Type": "Shares",
    "SecuritySubType": "Stock",
    "FullBranch": "Finance-Banks-Banks",
    "LastRate": 7011.0,
    "Change": 0.46,
    "TradeDate": "03/04/2026",
    "MonthYield": 3.7,
    "AnnualYield": 4.3,
    "MarketValue": 103664078,
    "CompanyId": 604,
    "Id": "00604611",
    "RedemptionDate": "",
    "AnnualInterest": None,
    "Linkage": "Unlinked",
    "DaysUntilRedemption": None,
    "BaseIndices": None,
    "UAssetName": "",
    "ForeignMarket": "",
    "FundUpdateDate": "",
    "CreationPrice": None,
    "SellPrice": None,
    "UnitPrice": None,
    "IsForeignETF": False,
    "GreenIndicators": [{"Key": "MM", "Value": True, "Desc": "Market Maker Appointed"}],
    "RedIndicators": [],
}

SAMPLE_SECURITY_DATA_HE = {
    "Name": "\u05dc\u05d0\u05d5\u05de\u05d9",
    "SecurityLongName": '\u05d1\u05e0\u05e7 \u05dc\u05d0\u05d5\u05de\u05d9 \u05dc\u05d9\u05e9\u05e8\u05d0\u05dc \u05d1\u05e2"\u05de',
    "CompanyName": "\u05dc\u05d0\u05d5\u05de\u05d9",
}

SAMPLE_MAJORDATA = {
    "CompanyDetails": {
        "Id": "000604",
        "Name": "LEUMI BANK",
        "Description": "THE BANK PROVIDES A VARIETY OF BANKING & FINANCIAL SERVICES.",
        "FullBranch": "Finance - Banks - Banks",
        "Logo": "000604.gif",
        "Site": "WWW.LEUMI.CO.IL",
        "ProfileFooterLink_Eng": "",
    },
    "LastDaysData": [
        {"TradeDate": "03/04/2026", "LastRate": 7011.0, "Change": 0.46,
         "TurnOver": None, "TurnOver1000": 155165.61,
         "IfTraded": True, "ShareTradingStatus": None, "IsOfferingPrice": False},
    ],
    "LastRates": [
        {"Rate": 7240.0, "Change": 3.27, "DealTime": "14:29",
         "DealDate": "06/04/2026", "RateType": "L",
         "TradingStage": "\u05e9\u05e0", "TradingStageDesc": "Closing price",
         "TradingStageMob": "", "OverallTurnover": 217.2,
         "InDay": True, "TradeDate": "06/04/2026", "TradeTime": "14:47"},
    ],
    "SecurityInIndices": {
        "Items": [
            {"IndexId": 142, "IndexName": "TA-35",
             "IndexCategoryName": "Market Cap. Indices",
             "Weight": 5.97, "WeightFactor": 0.43},
        ],
        "TotalRec": 1,
        "TradeDate": "06/04/2026",
    },
    "ShortSales": {"Value": 9936.18, "TradeDate": "27/03/2026"},
    "Statistics": {
        "DateFrom": "01/02/2026", "DateTo": "28/02/2026",
        "DailyTurnoverInExchange": 262852.9,
        "Month6AvgTurnover": 230384.89, "SDYield": 3.07,
        "MedianTurnover6M": 221177.66, "DailyAvgTransactions": 9597.6,
    },
    "YieldsRates": [],
}

SAMPLE_MAYA_INFO = {
    "fundId": 5122627,
    "name": "MTF מח SP500",
    "longName": "MTF מחקה (S&P 500 (4D",
    "fundType": "קרן מחקה",
    "fundTypeId": 4,
    "isin": "IL0051226277",
    "deleted": False,
    "managerId": 10040,
    "managerName": "מגדל",
    "trusteeId": 10030,
    "trusteeName": "מזרחי טפחות נאמנות",
    "managementFee": 0.0,
    "trusteeFee": 0.03,
    "purchasePrice": 295.51,
    "redemptionPrice": 295.51,
    "ratesAsOf": "2026-03-31",
    "assetValueNISMillions": 2030.2,
    "taxStatusName": "פטורה",
    "classification": {"major": "מניות בחו\"ל", "main": "מניות", "secondary": "אמריקה"},
    "yields": {"dayYield": 2.52, "monthYield": -4.74, "yearYield": -5.16,
               "last12MonthYield": -0.12, "standardDeviation": 1.51},
    "underlyingAssets": [{"name": "S&P 500 - NTR", "indexId": None, "weight": 100.0}],
    "exposureProfile": {"shareSymbol": "4", "fxSymbol": "D",
                        "sharesDesc": "up to 120%", "fxDesc": "up to 120%"},
}


@pytest.fixture()
def mock_client(sample_eod_csv: str) -> TaseClient:
    """A TaseClient whose fetch_eod_csv always returns the sample CSV."""
    client = MagicMock(spec=TaseClient)
    client.fetch_eod_csv.return_value = sample_eod_csv
    return client


@pytest.fixture()
def mock_client_fund() -> TaseClient:
    """A TaseClient that returns null securitydata but valid Maya data."""
    client = MagicMock(spec=TaseClient)
    client.fetch_eod_csv.return_value = (
        "title\ndate range\n"
        "Date,Adjusted Closing Price,x,Closing Price (0.01 ILS),y,Opening Price,"
        "z,High Price,Low Price,a,b,c,Volume\n"
    )
    client.fetch_maya_fund_history_csv.return_value = SAMPLE_MAYA_CSV
    client.fetch_security_data.return_value = None  # mutual fund -> Maya
    client.fetch_maya_fund_info.return_value = SAMPLE_MAYA_INFO
    return client


# ---------------------------------------------------------------------------
# Security.__init__
# ---------------------------------------------------------------------------


class TestSecurityInit:
    """Tests for Security construction and ID normalisation."""

    def test_zero_pads_short_id(self) -> None:
        sec = Security("604611")
        assert sec.id == "00604611"

    def test_keeps_already_padded_id(self) -> None:
        sec = Security("00604611")
        assert sec.id == "00604611"

    def test_rejects_non_numeric(self) -> None:
        with pytest.raises(ValueError, match="must be numeric"):
            Security("LEUMI")


# ---------------------------------------------------------------------------
# Security.history — exchange-traded
# ---------------------------------------------------------------------------


class TestSecurityHistory:
    """Tests for Security.history() with exchange-traded securities."""

    def test_returns_dataframe(self, mock_client: TaseClient) -> None:
        df = Security("604611", client=mock_client).history()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_default_years(self, mock_client: TaseClient) -> None:
        Security("604611", client=mock_client).history()
        mock_client.fetch_eod_csv.assert_called_once()
        # Default is 2 years → pType 5
        assert mock_client.fetch_eod_csv.call_args[0][1] == 5

    def test_explicit_years(self, mock_client: TaseClient) -> None:
        Security("604611", client=mock_client).history(years=5)
        assert mock_client.fetch_eod_csv.call_args[0][1] == 7  # 5y → ptype 7

    def test_days_param(self, mock_client: TaseClient) -> None:
        Security("604611", client=mock_client).history(days=30)
        assert mock_client.fetch_eod_csv.call_args[0][1] == 1  # 30d → ptype 1 (1 month)

    def test_days_overrides_years(self, mock_client: TaseClient) -> None:
        Security("604611", client=mock_client).history(years=5, days=7)
        # days takes precedence; 7 days → ptype 1 (1 month)
        assert mock_client.fetch_eod_csv.call_args[0][1] == 1

    def test_start_date_trims(self, mock_client: TaseClient) -> None:
        df = Security("604611", client=mock_client).history(start="2026-03-25")
        assert df.index.min() >= pd.Timestamp("2026-03-25")

    def test_end_date_trims(self, mock_client: TaseClient) -> None:
        df = Security("604611", client=mock_client).history(end="2026-03-20")
        assert df.index.max() <= pd.Timestamp("2026-03-20")

    def test_start_and_end(self, mock_client: TaseClient) -> None:
        df = Security("604611", client=mock_client).history(
            start="2026-03-15", end="2026-03-25"
        )
        assert df.index.min() >= pd.Timestamp("2026-03-15")
        assert df.index.max() <= pd.Timestamp("2026-03-25")

    def test_empty_range_raises(self, mock_client: TaseClient) -> None:
        with pytest.raises(SecurityNotFoundError):
            Security("604611", client=mock_client).history(
                start="2099-01-01", end="2099-12-31"
            )

    def test_columns(self, mock_client: TaseClient) -> None:
        df = Security("604611", client=mock_client).history()
        assert list(df.columns) == [
            "Open", "High", "Low", "Close", "Adj Close", "Volume"
        ]


# ---------------------------------------------------------------------------
# Security.etf_history
# ---------------------------------------------------------------------------


class TestSecurityEtfHistory:
    """Tests for Security.etf_history()."""

    @pytest.fixture()
    def mock_client_etf(self, sample_etf_eod_csv: str) -> TaseClient:
        client = MagicMock(spec=TaseClient)
        client.fetch_etf_eod_csv.return_value = sample_etf_eod_csv
        return client

    def test_returns_dataframe(self, mock_client_etf: TaseClient) -> None:
        df = Security("01159235", client=mock_client_etf).etf_history()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_has_standard_columns(self, mock_client_etf: TaseClient) -> None:
        df = Security("01159235", client=mock_client_etf).etf_history()
        for col in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
            assert col in df.columns

    def test_has_etf_columns(self, mock_client_etf: TaseClient) -> None:
        df = Security("01159235", client=mock_client_etf).etf_history()
        assert "Market Cap" in df.columns

    def test_default_ptype(self, mock_client_etf: TaseClient) -> None:
        Security("01159235", client=mock_client_etf).etf_history()
        mock_client_etf.fetch_etf_eod_csv.assert_called_once()
        # Default 2 years → pType 5
        assert mock_client_etf.fetch_etf_eod_csv.call_args[0][1] == 5

    def test_explicit_years(self, mock_client_etf: TaseClient) -> None:
        Security("01159235", client=mock_client_etf).etf_history(years=5)
        assert mock_client_etf.fetch_etf_eod_csv.call_args[0][1] == 7

    def test_days_param(self, mock_client_etf: TaseClient) -> None:
        Security("01159235", client=mock_client_etf).etf_history(days=30)
        assert mock_client_etf.fetch_etf_eod_csv.call_args[0][1] == 1

    def test_start_date_trims(self, mock_client_etf: TaseClient) -> None:
        df = Security("01159235", client=mock_client_etf).etf_history(
            start="2026-03-25"
        )
        assert df.index.min() >= pd.Timestamp("2026-03-25")

    def test_end_date_trims(self, mock_client_etf: TaseClient) -> None:
        df = Security("01159235", client=mock_client_etf).etf_history(
            end="2026-03-26"
        )
        assert df.index.max() <= pd.Timestamp("2026-03-26")

    def test_no_data_raises(self) -> None:
        client = MagicMock(spec=TaseClient)
        client.fetch_etf_eod_csv.return_value = "title\nrange\ncol\n"
        with pytest.raises(SecurityNotFoundError):
            Security("9999999", client=client).etf_history()

    def test_empty_range_raises(self, mock_client_etf: TaseClient) -> None:
        with pytest.raises(SecurityNotFoundError):
            Security("01159235", client=mock_client_etf).etf_history(
                start="2099-01-01", end="2099-12-31"
            )


# ---------------------------------------------------------------------------
# Security.history — mutual fund fallback
# ---------------------------------------------------------------------------


class TestSecurityHistoryFund:
    """Tests for Security.history() falling back to Maya for mutual funds."""

    def test_returns_maya_data(self, mock_client_fund: TaseClient) -> None:
        df = Security("5122627", client=mock_client_fund).history()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "Close" in df.columns

    def test_maya_columns(self, mock_client_fund: TaseClient) -> None:
        df = Security("5122627", client=mock_client_fund).history()
        assert list(df.columns) == ["Close"]

    def test_no_data_anywhere_raises(self) -> None:
        client = MagicMock(spec=TaseClient)
        client.fetch_eod_csv.return_value = "title\nrange\ncol\n"
        client.fetch_maya_fund_history_csv.side_effect = TaseNetworkError("404")
        with pytest.raises(SecurityNotFoundError):
            Security("9999999", client=client).history()

    def test_nothing_found_raises_for_info(self) -> None:
        client = MagicMock(spec=TaseClient)
        client.fetch_security_data.return_value = None  # mutual fund path
        client.fetch_maya_fund_info.side_effect = TaseNetworkError("404")
        with pytest.raises(SecurityNotFoundError):
            Security("9999999", client=client).info()


# ---------------------------------------------------------------------------
# Security.info — exchange-traded
# ---------------------------------------------------------------------------


class TestSecurityInfo:
    """Tests for Security.info() with exchange-traded securities."""

    @staticmethod
    def _sec_data_side_effect(*args, **kwargs):
        """Return Hebrew or English securitydata depending on lang."""
        if kwargs.get("lang") == 0:
            return SAMPLE_SECURITY_DATA_HE
        return SAMPLE_SECURITY_DATA_EN

    @pytest.fixture()
    def info(self) -> dict:
        client = MagicMock(spec=TaseClient)
        client.fetch_security_data.side_effect = self._sec_data_side_effect
        client.fetch_security_majordata.return_value = SAMPLE_MAJORDATA
        return Security("604611", client=client).info()

    def test_includes_name(self, info: dict) -> None:
        assert info["name"] == "LEUMI"

    def test_includes_hebrew_name(self, info: dict) -> None:
        assert info["name_he"] == "\u05dc\u05d0\u05d5\u05de\u05d9"

    def test_name_order(self, info: dict) -> None:
        keys = list(info.keys())
        assert keys[0] == "name"
        assert keys[1] == "name_he"

    def test_long_name(self, info: dict) -> None:
        assert info["long_name"] == "BANK LEUMI LE- ISRAEL B.M."

    def test_company_name(self, info: dict) -> None:
        assert info["company_name"] == "LEUMI BANK"

    def test_symbol(self, info: dict) -> None:
        assert info["symbol"] == "LUMI"

    def test_isin(self, info: dict) -> None:
        assert info["isin"] == "IL0006046119"

    def test_type(self, info: dict) -> None:
        assert info["type"] == "Shares"

    def test_sector(self, info: dict) -> None:
        assert info["sector"] == "Finance-Banks-Banks"

    def test_last_rate(self, info: dict) -> None:
        assert info["last_rate"] == 7011.0

    def test_change_pct(self, info: dict) -> None:
        assert info["change_pct"] == 0.46

    def test_trade_date(self, info: dict) -> None:
        assert info["trade_date"] == "03/04/2026"

    def test_month_yield(self, info: dict) -> None:
        assert info["month_yield"] == 3.7

    def test_annual_yield(self, info: dict) -> None:
        assert info["annual_yield"] == 4.3

    def test_market_value(self, info: dict) -> None:
        assert info["market_value"] == 103664078

    def test_description(self, info: dict) -> None:
        assert "BANKING" in info["description"]

    def test_website(self, info: dict) -> None:
        assert info["website"] == "WWW.LEUMI.CO.IL"

    def test_intraday_rate(self, info: dict) -> None:
        assert info["intraday_rate"] == 7240.0

    def test_intraday_time(self, info: dict) -> None:
        assert info["intraday_time"] == "14:29"

    def test_indices_list(self, info: dict) -> None:
        assert len(info["indices"]) == 1
        assert info["indices"][0]["name"] == "TA-35"
        assert info["indices"][0]["weight"] == 5.97
        assert info["indices"][0]["category"] == "Market Cap. Indices"

    def test_short_sales(self, info: dict) -> None:
        assert info["short_sale_value"] == 9936.18

    def test_statistics(self, info: dict) -> None:
        stats = info["statistics"]
        assert stats["daily_avg_turnover"] == 262852.9
        assert stats["std_dev_yield"] == 3.07

    def test_majordata_uses_real_comp_id(self) -> None:
        """fetch_security_majordata is called with the CompanyId from securitydata."""
        client = MagicMock(spec=TaseClient)
        client.fetch_security_data.side_effect = self._sec_data_side_effect
        client.fetch_security_majordata.return_value = SAMPLE_MAJORDATA
        Security("604611", client=client).info()
        call_kwargs = client.fetch_security_majordata.call_args
        assert call_kwargs.kwargs.get("comp_id") == "604"

    def test_hebrew_name_failure_still_returns_info(self) -> None:
        """If the Hebrew name fetch fails, info() still works without name_he."""
        from tasekit.exceptions import TaseNetworkError

        def side_effect(*args, **kwargs):
            if kwargs.get("lang") == 0:
                raise TaseNetworkError("timeout")
            return SAMPLE_SECURITY_DATA_EN

        client = MagicMock(spec=TaseClient)
        client.fetch_security_data.side_effect = side_effect
        client.fetch_security_majordata.return_value = SAMPLE_MAJORDATA
        info = Security("604611", client=client).info()
        assert "name_he" not in info
        assert info["name"] == "LEUMI"
        assert info["last_rate"] == 7011.0

    def test_no_short_sales(self) -> None:
        data = {**SAMPLE_MAJORDATA, "ShortSales": {"Value": None}}
        client = MagicMock(spec=TaseClient)
        client.fetch_security_data.side_effect = self._sec_data_side_effect
        client.fetch_security_majordata.return_value = data
        info = Security("604611", client=client).info()
        assert "short_sale_value" not in info

    def test_no_indices(self) -> None:
        data = {**SAMPLE_MAJORDATA, "SecurityInIndices": {"Items": [], "TotalRec": 0}}
        client = MagicMock(spec=TaseClient)
        client.fetch_security_data.side_effect = self._sec_data_side_effect
        client.fetch_security_majordata.return_value = data
        info = Security("604611", client=client).info()
        assert "indices" not in info


# ---------------------------------------------------------------------------
# Security.info — mutual fund fallback
# ---------------------------------------------------------------------------


class TestSecurityInfoFund:
    """Tests for Security.info() falling back to Maya for mutual funds."""

    @pytest.fixture()
    def info(self, mock_client_fund: TaseClient) -> dict:
        return Security("5122627", client=mock_client_fund).info()

    def test_name(self, info: dict) -> None:
        assert info["name"] == "MTF מח SP500"

    def test_isin(self, info: dict) -> None:
        assert info["isin"] == "IL0051226277"

    def test_manager(self, info: dict) -> None:
        assert info["manager"] == "מגדל"

    def test_fees(self, info: dict) -> None:
        assert info["management_fee"] == 0.0
        assert info["trustee_fee"] == 0.03

    def test_classification(self, info: dict) -> None:
        assert info["classification"]["major"] == 'מניות בחו"ל'

    def test_yields(self, info: dict) -> None:
        assert info["yields"]["day"] == 2.52
        assert info["yields"]["month"] == -4.74
        assert info["yields"]["std_dev"] == 1.51

    def test_underlying_assets(self, info: dict) -> None:
        assert len(info["underlying_assets"]) == 1
        assert info["underlying_assets"][0]["name"] == "S&P 500 - NTR"

    def test_exposure_profile(self, info: dict) -> None:
        assert "shares" in info["exposure_profile"]

    def test_nothing_found_raises(self) -> None:
        client = MagicMock(spec=TaseClient)
        client.fetch_security_data.return_value = None  # mutual fund path
        client.fetch_maya_fund_info.side_effect = TaseNetworkError("404")
        with pytest.raises(SecurityNotFoundError):
            Security("9999999", client=client).info()
