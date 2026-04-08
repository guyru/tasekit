"""The :class:`Security` class — main user-facing object."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from tasekit.api import TaseClient, _ptype_for_days, _ptype_for_years, get_default_client
from tasekit.constants import DEFAULT_HISTORY_YEARS
from tasekit.exceptions import SecurityNotFoundError, TaseParsingError
from tasekit.parsers import parse_eod_csv, parse_etf_eod_csv, parse_maya_fund_csv


class Security:
    """Represents a security traded on the Tel Aviv Stock Exchange.

    Create a handle (no network call), then fetch data on demand::

        sec = tasekit.Security("00604611")
        df = sec.history(years=2)

    For mutual funds that are not exchange-traded, the library automatically
    falls back to the Maya API.

    Args:
        security_id: TASE security ID (e.g. ``"00604611"``).
            Both zero-padded and unpadded forms are accepted; the ID is
            normalised to 8 digits internally.
        client: Optional :class:`~tasekit.api.TaseClient` instance.
            If ``None``, the module-level default client is used.
    """

    def __init__(self, security_id: str, *, client: TaseClient | None = None) -> None:
        self._id = self._normalize_id(security_id)
        self._client = client or get_default_client()

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        """The zero-padded 8-digit TASE security ID."""
        return self._id

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def history(
        self,
        *,
        years: int | None = None,
        days: int | None = None,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
    ) -> pd.DataFrame:
        """Fetch historical end-of-day data.

        The method first tries the main TASE EOD endpoint.  If that returns no
        data (e.g. for mutual funds that are not exchange-traded), it
        automatically falls back to the Maya mutual-fund API.

        Args:
            years: How many years of history to fetch (max 5).
                Ignored when *start* or *days* is provided.  Defaults to 2.
            days: How many calendar days of history to fetch.
                Ignored when *start* is provided.  Takes precedence over *years*.
            start: Start date (inclusive).  ``"YYYY-MM-DD"`` string or
                :class:`~datetime.datetime`.
            end: End date (inclusive).  Defaults to today.

        Returns:
            DataFrame with ``DatetimeIndex`` ("Date").

            For exchange-traded securities the columns are:
            ``Open``, ``High``, ``Low``, ``Close``, ``Adj Close``, ``Volume``.

            For mutual funds (Maya fallback) the only column is ``Close``
            (the redemption price).

        Raises:
            SecurityNotFoundError: If the ID returns no trading data.
            TaseNetworkError: On HTTP / connectivity failure.
            TaseParsingError: If the response cannot be parsed.
        """
        # --- Try the main TASE EOD endpoint first --------------------------
        ptype = self._resolve_ptype(years=years, days=days, start=start)
        csv_text = self._client.fetch_eod_csv(self._id, ptype)

        try:
            df = parse_eod_csv(csv_text)
        except TaseParsingError:
            df = pd.DataFrame()

        if not df.empty:
            df = self._trim_dates(df, years=years, days=days, start=start, end=end)
            if not df.empty:
                return df

        # --- Fallback: Maya mutual-fund API --------------------------------
        df = self._fetch_maya_history(years=years, days=days, start=start, end=end)
        if df is not None and not df.empty:
            return df

        raise SecurityNotFoundError(
            f"No trading data found for security {self._id}"
        )

    def etf_history(
        self,
        *,
        years: int | None = None,
        days: int | None = None,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
    ) -> pd.DataFrame:
        """Fetch historical end-of-day data with ETF-specific columns.

        Uses the ``export/etfhistoryeod`` endpoint which returns additional
        columns compared to the generic :meth:`history` method: purchase
        price, redemption price, NAV (unit price), management fee, trustee
        fee, and market cap.

        The parameters and date-selection logic are identical to
        :meth:`history`.

        Args:
            years: How many years of history to fetch (max 5).
                Ignored when *start* or *days* is provided.  Defaults to 2.
            days: How many calendar days of history to fetch.
                Ignored when *start* is provided.  Takes precedence over *years*.
            start: Start date (inclusive).  ``"YYYY-MM-DD"`` string or
                :class:`~datetime.datetime`.
            end: End date (inclusive).  Defaults to today.

        Returns:
            DataFrame with ``DatetimeIndex`` ("Date") and columns
            ``Open``, ``High``, ``Low``, ``Close``, ``Adj Close``,
            ``Volume``, plus any ETF-specific columns that contain data:
            ``Purchase Price``, ``Redemption Price``, ``NAV``,
            ``Management Fee``, ``Trustee Fee``, ``Market Cap``.

        Raises:
            SecurityNotFoundError: If the ID returns no trading data.
            TaseNetworkError: On HTTP / connectivity failure.
            TaseParsingError: If the response cannot be parsed.
        """
        ptype = self._resolve_ptype(years=years, days=days, start=start)
        csv_text = self._client.fetch_etf_eod_csv(self._id, ptype)

        try:
            df = parse_etf_eod_csv(csv_text)
        except TaseParsingError:
            df = pd.DataFrame()

        if not df.empty:
            df = self._trim_dates(df, years=years, days=days, start=start, end=end)
            if not df.empty:
                return df

        raise SecurityNotFoundError(
            f"No ETF trading data found for security {self._id}"
        )

    def info(self) -> dict:
        """Fetch metadata / summary information for this security.

        Uses ``company/securitydata`` as the primary source (ISIN, symbol,
        sector, yields, bond/ETF-specific fields, real company ID) and
        supplements it with ``security/majordata`` for index memberships,
        short sales, and trading statistics.  Falls back to the Maya API
        for mutual funds (where ``securitydata`` returns ``null``).

        Returns:
            dict with available metadata.  Keys depend on the security type.
        """
        from tasekit.exceptions import TaseNetworkError

        unpadded = self._id.lstrip("0") or "0"

        # Primary source: company/securitydata (English).
        # Returns None for mutual funds -> fall back to Maya.
        sec_data = self._client.fetch_security_data(unpadded, lang=1)
        if sec_data is None:
            return self._fetch_maya_info()

        # Hebrew name - best-effort, don't fail if unreachable.
        sec_data_he: dict | None = None
        try:
            sec_data_he = self._client.fetch_security_data(unpadded, lang=0)
        except TaseNetworkError:
            pass

        # Supplement with majordata for indices, short sales, statistics.
        # Pass the real CompanyId so CompanyDetails are populated.
        comp_id = str(sec_data.get("CompanyId") or "")
        major_data = self._client.fetch_security_majordata(
            unpadded, comp_id=comp_id or unpadded
        )

        return self._format_security_data(sec_data, sec_data_he, major_data)

    # ------------------------------------------------------------------
    # Maya helpers
    # ------------------------------------------------------------------

    def _fetch_maya_history(
        self,
        *,
        years: int | None,
        days: int | None,
        start: str | datetime | None,
        end: str | datetime | None,
    ) -> pd.DataFrame | None:
        """Try fetching history from the Maya mutual-fund API.

        Returns ``None`` if the fund is not found on Maya.
        """
        from tasekit.exceptions import TaseNetworkError

        fund_id = self._id.lstrip("0") or "0"
        to_dt = pd.Timestamp(end) if end else pd.Timestamp.now()
        from_dt = self._resolve_from_date(
            to_dt, years=years, days=days, start=start
        )

        to_str = to_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        from_str = from_dt.strftime("%Y-%m-%dT00:00:00.000Z")

        try:
            csv_text = self._client.fetch_maya_fund_history_csv(
                fund_id, from_str, to_str
            )
        except TaseNetworkError:
            return None

        try:
            df = parse_maya_fund_csv(csv_text)
        except TaseParsingError:
            return None

        if df.empty:
            return None

        # Trim to requested window.
        if start is not None:
            df = df[df.index >= pd.Timestamp(start)]
        if end is not None:
            df = df[df.index <= pd.Timestamp(end)]

        return df

    def _fetch_maya_info(self) -> dict:
        """Fetch fund info from Maya, or raise SecurityNotFoundError."""
        from tasekit.exceptions import TaseNetworkError

        fund_id = self._id.lstrip("0") or "0"
        try:
            data = self._client.fetch_maya_fund_info(fund_id)
        except TaseNetworkError as exc:
            raise SecurityNotFoundError(
                f"No info found for security {self._id}"
            ) from exc

        return self._format_maya_info(data)

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_security_data(
        sec_data: dict,
        sec_data_he: dict | None,
        major_data: dict,
    ) -> dict:
        """Build the ``info()`` result from ``securitydata`` + ``majordata``."""
        result: dict = {}

        # --- Names ---
        result["name"] = sec_data.get("Name")
        if sec_data_he:
            name_he = sec_data_he.get("Name")
            if name_he:
                result["name_he"] = name_he

        # For foreign ETFs prefer LongName (e.g. "ISHARES MSCI ACWI UCITS ETF")
        # over SecurityLongName (which is the manager's legal name).
        long_name = sec_data.get("LongName") or sec_data.get("SecurityLongName")
        if long_name:
            result["long_name"] = long_name
        if sec_data.get("CompanyName"):
            result["company_name"] = sec_data["CompanyName"]
        if sec_data.get("Symbol"):
            result["symbol"] = sec_data["Symbol"]
        if sec_data.get("ISIN"):
            result["isin"] = sec_data["ISIN"]
        if sec_data.get("Type"):
            result["type"] = sec_data["Type"]
        if sec_data.get("SecuritySubType"):
            result["sub_type"] = sec_data["SecuritySubType"]
        if sec_data.get("FullBranch"):
            result["sector"] = sec_data["FullBranch"]

        # --- Trading data ---
        result["last_rate"] = sec_data.get("LastRate")
        result["change_pct"] = sec_data.get("Change")
        result["trade_date"] = sec_data.get("TradeDate")
        if sec_data.get("MonthYield") is not None:
            result["month_yield"] = sec_data["MonthYield"]
        if sec_data.get("AnnualYield") is not None:
            result["annual_yield"] = sec_data["AnnualYield"]
        if sec_data.get("MarketValue"):
            result["market_value"] = sec_data["MarketValue"]

        # --- Bond-specific ---
        if sec_data.get("RedemptionDate"):
            result["redemption_date"] = sec_data["RedemptionDate"]
        if sec_data.get("AnnualInterest") is not None:
            result["annual_interest"] = sec_data["AnnualInterest"]
        linkage = sec_data.get("Linkage", "")
        if linkage and linkage.lower() not in ("unlinked", "לא צמוד"):
            result["linkage"] = linkage
        if sec_data.get("DaysUntilRedemption") is not None:
            result["days_until_redemption"] = sec_data["DaysUntilRedemption"]
        if sec_data.get("BaseIndices") is not None:
            result["base_indices"] = sec_data["BaseIndices"]
        if sec_data.get("BaseIndicesDate"):
            result["base_indices_date"] = sec_data["BaseIndicesDate"]

        # --- ETF-specific ---
        if sec_data.get("UAssetName"):
            result["underlying_asset"] = sec_data["UAssetName"]
        if sec_data.get("ForeignMarket"):
            result["foreign_market"] = sec_data["ForeignMarket"]
        if sec_data.get("FundUpdateDate"):
            result["fund_update_date"] = sec_data["FundUpdateDate"]
        if sec_data.get("CreationPrice") is not None:
            result["creation_price"] = sec_data["CreationPrice"]
        if sec_data.get("SellPrice") is not None:
            result["sell_price"] = sec_data["SellPrice"]
        if sec_data.get("UnitPrice") is not None:
            result["nav"] = sec_data["UnitPrice"]

        # --- From majordata: company description & website ---
        comp = major_data.get("CompanyDetails") or {}
        if comp.get("Description"):
            result["description"] = comp["Description"]
        if comp.get("Site"):
            result["website"] = comp["Site"]

        # --- From majordata: live intraday rate ---
        last_rates = major_data.get("LastRates", [])
        if last_rates:
            lr = last_rates[0]
            if lr.get("Rate") is not None:
                result["intraday_rate"] = lr["Rate"]
            if lr.get("DealTime"):
                result["intraday_time"] = lr["DealTime"]
            if lr.get("TradingStageDesc"):
                result["trading_stage"] = lr["TradingStageDesc"]

        # --- From majordata: index memberships ---
        indices_data = major_data.get("SecurityInIndices", {})
        items = (indices_data or {}).get("Items", [])
        if items:
            result["indices"] = [
                {
                    "name": it.get("IndexName"),
                    "weight": it.get("Weight"),
                    "category": it.get("IndexCategoryName"),
                }
                for it in items
            ]

        # --- From majordata: short sales ---
        short = major_data.get("ShortSales", {})
        if short and short.get("Value"):
            result["short_sale_value"] = short["Value"]
            result["short_sale_date"] = short.get("TradeDate")

        # --- From majordata: statistics ---
        stats = major_data.get("Statistics", {})
        if stats:
            result["statistics"] = {
                "period": f"{stats.get('DateFrom')} – {stats.get('DateTo')}",
                "daily_avg_turnover": stats.get("DailyTurnoverInExchange"),
                "6m_avg_turnover": stats.get("Month6AvgTurnover"),
                "std_dev_yield": stats.get("SDYield"),
                "daily_avg_transactions": stats.get("DailyAvgTransactions"),
            }

        return result

    @staticmethod
    def _format_maya_info(data: dict) -> dict:
        """Flatten the Maya fund JSON into a user-friendly dict."""
        result: dict = {
            "fund_id": data.get("fundId"),
            "name": data.get("name"),
            "long_name": data.get("longName"),
            "fund_type": data.get("fundType"),
            "isin": data.get("isin"),
            "deleted": data.get("deleted"),
            "manager": data.get("managerName"),
            "trustee": data.get("trusteeName"),
            "management_fee": data.get("managementFee"),
            "trustee_fee": data.get("trusteeFee"),
            "purchase_price": data.get("purchasePrice"),
            "redemption_price": data.get("redemptionPrice"),
            "rates_as_of": data.get("ratesAsOf"),
            "aum_nis_millions": data.get("assetValueNISMillions"),
            "tax_status": data.get("taxStatusName"),
        }

        cls = data.get("classification", {})
        if cls:
            result["classification"] = {
                "major": cls.get("major"),
                "main": cls.get("main"),
                "secondary": cls.get("secondary"),
            }

        yields = data.get("yields", {})
        if yields:
            result["yields"] = {
                "day": yields.get("dayYield"),
                "month": yields.get("monthYield"),
                "year": yields.get("yearYield"),
                "12_months": yields.get("last12MonthYield"),
                "std_dev": yields.get("standardDeviation"),
            }

        assets = data.get("underlyingAssets", [])
        if assets:
            result["underlying_assets"] = [
                {"name": a.get("name"), "weight": a.get("weight")} for a in assets
            ]

        exp = data.get("exposureProfile", {})
        if exp:
            result["exposure_profile"] = {
                "shares": exp.get("sharesDesc"),
                "fx": exp.get("fxDesc"),
            }

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_id(security_id: str) -> str:
        """Zero-pad a numeric security ID to 8 digits."""
        if not security_id.isdigit():
            raise ValueError(
                f"Invalid TASE security ID: {security_id!r} (must be numeric)"
            )
        return security_id.zfill(8)

    @staticmethod
    def _resolve_ptype(
        *,
        years: int | None,
        days: int | None,
        start: str | datetime | None,
    ) -> int:
        """Choose the right ``pType`` based on the caller's arguments."""
        if start is not None:
            start_dt = pd.Timestamp(start)
            delta_days = (pd.Timestamp.now() - start_dt).days
            return _ptype_for_days(max(1, delta_days))

        if days is not None:
            return _ptype_for_days(max(1, days))

        if years is None:
            years = DEFAULT_HISTORY_YEARS
        return _ptype_for_years(years)

    @staticmethod
    def _resolve_from_date(
        to_dt: pd.Timestamp,
        *,
        years: int | None,
        days: int | None,
        start: str | datetime | None,
    ) -> pd.Timestamp:
        """Calculate the start date for a Maya history request."""
        if start is not None:
            return pd.Timestamp(start)
        if days is not None:
            return to_dt - timedelta(days=days)
        y = years if years is not None else DEFAULT_HISTORY_YEARS
        return to_dt - timedelta(days=y * 365)

    @staticmethod
    def _trim_dates(
        df: pd.DataFrame,
        *,
        years: int | None,
        days: int | None,
        start: str | datetime | None,
        end: str | datetime | None,
    ) -> pd.DataFrame:
        """Trim *df* to the requested date window."""
        if start is not None:
            df = df[df.index >= pd.Timestamp(start)]
        elif days is not None and days > 0 and not df.empty:
            cutoff = df.index.max() - timedelta(days=days)
            df = df[df.index >= cutoff]
        elif years is not None and years > 0 and not df.empty:
            cutoff = df.index.max() - timedelta(days=years * 365)
            df = df[df.index >= cutoff]

        if end is not None:
            df = df[df.index <= pd.Timestamp(end)]

        return df
