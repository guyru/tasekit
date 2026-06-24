"""Parsers for TASE API responses (CSV and JSON)."""

from __future__ import annotations

import io

import pandas as pd

from tasekit.constants import (
    COL_ADJ_CLOSE,
    COL_CLOSE,
    COL_DATE,
    COL_HIGH,
    COL_LOW,
    COL_MANAGEMENT_FEE,
    COL_MARKET_CAP,
    COL_OPEN,
    COL_PURCHASE_PRICE,
    COL_REDEMPTION_PRICE,
    COL_TRUSTEE_FEE,
    COL_UNIT_PRICE,
    COL_VOLUME_TRADE,
    COL_VOLUME_UNITS,
)
from tasekit.exceptions import TaseParsingError


# Prefix in the first CSV row before the security name (English).
_EOD_TITLE_PREFIX_EN = "Historical Data - End of Day "
# Prefix in Hebrew (fallback).
_EOD_TITLE_PREFIX_HE = "נתונים היסטוריים - סוף יום "


def extract_security_name(csv_text: str) -> str | None:
    """Extract the security name from the first (title) row of a TASE EOD CSV.

    Works with both English and Hebrew CSV responses.

    Returns:
        The security name, or ``None`` if it cannot be extracted.
    """
    first_line = csv_text.split("\n", maxsplit=1)[0]
    # Strip trailing commas, whitespace, and carriage returns.
    first_line = first_line.strip(", \t\r")
    for prefix in (_EOD_TITLE_PREFIX_EN, _EOD_TITLE_PREFIX_HE):
        if first_line.startswith(prefix):
            name = first_line[len(prefix):]
            return name if name else None
    return None


def parse_eod_csv(csv_text: str) -> pd.DataFrame:
    """Parse a TASE historical-EOD CSV into a standardized OHLC DataFrame.

    The TASE CSV has two metadata rows (title, date range) followed by a header
    row with Hebrew column names and then the data rows.

    Returns:
        DataFrame with a ``DatetimeIndex`` named ``"Date"`` (ascending) and
        columns ``Open``, ``High``, ``Low``, ``Close``, ``Adj Close``, ``Volume``.

    Raises:
        TaseParsingError: If the CSV cannot be parsed or has missing columns.
    """
    try:
        df = pd.read_csv(io.StringIO(csv_text), skiprows=2)
    except Exception as exc:
        raise TaseParsingError(f"Failed to read CSV data: {exc}") from exc

    if df.empty:
        raise TaseParsingError("CSV contained no data rows")

    col_map = _build_column_map(df.columns.tolist())

    result = pd.DataFrame()
    result["Date"] = pd.to_datetime(df[col_map["Date"]], format="%d/%m/%Y")
    result["Open"] = pd.to_numeric(df[col_map["Open"]], errors="coerce")
    result["High"] = pd.to_numeric(df[col_map["High"]], errors="coerce")
    result["Low"] = pd.to_numeric(df[col_map["Low"]], errors="coerce")
    result["Close"] = pd.to_numeric(df[col_map["Close"]], errors="coerce")
    result["Adj Close"] = pd.to_numeric(df[col_map["Adj Close"]], errors="coerce")
    result["Volume"] = pd.to_numeric(df[col_map["Volume"]], errors="coerce")

    # Filter out non-trading days.
    result = result.dropna(subset=["High", "Low"])
    result = result[result["Open"] > 0]

    # Sort ascending by date and set the index.
    result = result.sort_values("Date").reset_index(drop=True)
    result = result.set_index("Date")

    return result


def parse_etf_eod_csv(csv_text: str) -> pd.DataFrame:
    """Parse a TASE ETF historical-EOD CSV into a DataFrame.

    The ETF CSV has the same two-metadata-row structure as the regular EOD
    CSV, but includes extra columns specific to ETFs: purchase price,
    redemption price, unit price (NAV), management fee, and trustee fee.

    Returns:
        DataFrame with a ``DatetimeIndex`` named ``"Date"`` (ascending) and
        columns ``Open``, ``High``, ``Low``, ``Close``, ``Adj Close``,
        ``Volume``, plus optional ETF-specific columns:
        ``Purchase Price``, ``Redemption Price``, ``NAV``,
        ``Management Fee``, ``Trustee Fee``, ``Market Cap``.

        ETF-specific columns that are entirely empty are omitted.

    Raises:
        TaseParsingError: If the CSV cannot be parsed or has missing columns.
    """
    try:
        df = pd.read_csv(io.StringIO(csv_text), skiprows=2)
    except Exception as exc:
        raise TaseParsingError(f"Failed to read ETF CSV data: {exc}") from exc

    if df.empty:
        raise TaseParsingError("ETF CSV contained no data rows")

    col_map = _build_etf_column_map(df.columns.tolist())

    result = pd.DataFrame()
    result["Date"] = pd.to_datetime(df[col_map["Date"]], format="%d/%m/%Y")
    result["Open"] = pd.to_numeric(df[col_map["Open"]], errors="coerce")
    result["High"] = pd.to_numeric(df[col_map["High"]], errors="coerce")
    result["Low"] = pd.to_numeric(df[col_map["Low"]], errors="coerce")
    result["Close"] = pd.to_numeric(df[col_map["Close"]], errors="coerce")
    result["Adj Close"] = pd.to_numeric(df[col_map["Adj Close"]], errors="coerce")
    result["Volume"] = pd.to_numeric(df[col_map["Volume"]], errors="coerce")

    # ETF-specific optional columns — include only if they have data.
    _etf_extras = [
        ("Purchase Price", "Purchase Price"),
        ("Redemption Price", "Redemption Price"),
        ("NAV", "NAV"),
        ("Management Fee", "Management Fee"),
        ("Trustee Fee", "Trustee Fee"),
        ("Market Cap", "Market Cap"),
    ]
    for result_col, map_key in _etf_extras:
        if map_key in col_map:
            series = pd.to_numeric(df[col_map[map_key]], errors="coerce")
            if series.notna().any():
                result[result_col] = series

    # Filter out non-trading days.
    result = result.dropna(subset=["High", "Low"])
    result = result[result["Open"] > 0]

    # Sort ascending by date and set the index.
    result = result.sort_values("Date").reset_index(drop=True)
    result = result.set_index("Date")

    return result


def parse_maya_fund_csv(csv_text: str) -> pd.DataFrame:
    """Parse a Maya mutual-fund history CSV into a DataFrame.

    The Maya CSV has a single header row with Hebrew columns::

        מס' קרן, תאריך, מחיר קניה, מחיר פדיון, דמי ניהול (%), ...

    Returns:
        DataFrame with ``DatetimeIndex`` ("Date") and column ``Close``
        (the redemption price / מחיר פדיון).

    Raises:
        TaseParsingError: If the CSV cannot be parsed.
    """
    try:
        df = pd.read_csv(io.StringIO(csv_text))
    except Exception as exc:
        raise TaseParsingError(f"Failed to read Maya CSV data: {exc}") from exc

    if df.empty:
        raise TaseParsingError("Maya CSV contained no data rows")

    cols = df.columns.tolist()
    # Expected columns: fund number, date, purchase price, redemption price, ...
    if len(cols) < 4:
        raise TaseParsingError(
            f"Maya CSV has too few columns ({len(cols)}): {cols}"
        )

    result = pd.DataFrame()
    result["Date"] = pd.to_datetime(df[cols[1]], format="%d.%m.%Y")
    result["Close"] = pd.to_numeric(df[cols[3]], errors="coerce")  # redemption price

    result = result.dropna(subset=["Close"])
    result = result.sort_values("Date").reset_index(drop=True)
    result = result.set_index("Date")

    return result


def parse_hedge_fund_history(rows: list[dict]) -> pd.DataFrame:
    """Parse mutual hedge-fund history rows (JSON) into a DataFrame.

    Each row is ``{fundId, tradeDate, purchasePrice, sellPrice}`` as returned
    by ``funds/hedge/{id}/history``.

    Returns:
        DataFrame with a ``DatetimeIndex`` ("Date", ascending) and columns
        ``Gross`` (purchase price / שער יחידה ברוטו) and ``Net`` (redemption
        price / שער יחידה נטו).

    Raises:
        TaseParsingError: If *rows* is empty or cannot be parsed.
    """
    if not rows:
        raise TaseParsingError("Hedge-fund history contained no rows")

    try:
        df = pd.DataFrame(rows)
        result = pd.DataFrame()
        result["Date"] = pd.to_datetime(df["tradeDate"])
        result["Gross"] = pd.to_numeric(df["purchasePrice"], errors="coerce")
        result["Net"] = pd.to_numeric(df["sellPrice"], errors="coerce")
    except (KeyError, ValueError) as exc:
        raise TaseParsingError(f"Failed to parse hedge-fund history: {exc}") from exc

    result = result.dropna(subset=["Net"])
    result = result.sort_values("Date").reset_index(drop=True)
    result = result.set_index("Date")

    if result.empty:
        raise TaseParsingError("Hedge-fund history contained no valid rows")

    return result


def parse_hedge_fund_list(rows: list[dict]) -> pd.DataFrame:
    """Parse the mutual hedge-fund listing (JSON) into a DataFrame.

    Each row is a fund summary as returned by ``funds/hedge`` (the listing that
    backs the Maya hedge-funds page).

    Returns:
        DataFrame indexed by ``Fund ID`` (string) with columns ``Name``,
        ``Manager``, ``Trustee``, ``Management Fee``, ``Success Fee``,
        ``Trustee Fee``, ``AUM`` (assets under management, NIS millions),
        ``Tax Status`` and ``Classification``.  Sorted ascending by fund ID.

    Raises:
        TaseParsingError: If *rows* is empty or cannot be parsed.
    """
    if not rows:
        raise TaseParsingError("Hedge-fund list contained no rows")

    try:
        records = [
            {
                "Fund ID": str(r["fundId"]),
                "Name": r.get("name"),
                "Manager": r.get("managerName"),
                "Trustee": r.get("trusteeName"),
                "Management Fee": r.get("managementFee"),
                "Success Fee": r.get("successFee"),
                "Trustee Fee": r.get("trusteeFee"),
                "AUM": r.get("assetValue"),
                "Tax Status": r.get("taxStatusName"),
                "Classification": (r.get("classification") or {}).get("major"),
            }
            for r in rows
        ]
    except (KeyError, TypeError) as exc:
        raise TaseParsingError(f"Failed to parse hedge-fund list: {exc}") from exc

    result = pd.DataFrame.from_records(records)
    result = result.sort_values("Fund ID", key=lambda s: s.astype(int))
    return result.set_index("Fund ID")


def add_hedge_fund_adj_close(df: pd.DataFrame, *, tol: float = 1e-4) -> pd.DataFrame:
    """Add a continuous ``Adj Close`` column to a hedge-fund history frame.

    A new monthly series is minted for the fund each month; within a fee
    period the net (redemption) price drifts below the gross price as
    management and success fees accrue.  At each year-end crystallization the
    fees are realised: holdings convert into the oldest series, the per-unit
    net price *resets up* to the gross, and the unit count is scaled by
    ``net/gross`` to preserve value.

    The raw ``Net`` series therefore contains an upward jump at every reset
    that is not a real return.  This builds a forward total-return index that
    replaces each reset step's ratio with 1 (value is preserved across the
    conversion), then rescales it so the most recent ``Adj Close`` equals the
    most recent raw ``Net`` (yfinance "recent = actual" convention).

    A crystallization is identified by three conditions: the step crosses a
    calendar-year boundary, net was previously accruing fees (net < gross),
    and net has jumped up to meet gross.  Requiring a year crossing avoids a
    false positive when a success-fee fund's gross falls below its high-water
    mark mid-year — the success fee zeroes out so net rises to meet gross, but
    no unit conversion happens and the (genuine, often negative) return must
    not be discarded.

    Args:
        df: Output of :func:`parse_hedge_fund_history` (needs ``Gross`` and
            ``Net``, ascending by date).
        tol: Relative tolerance for detecting ``net == gross``.

    Returns:
        A copy of *df* with an added ``Adj Close`` column.  When the frame has
        a single row, ``Adj Close`` equals ``Net``.
    """
    result = df.copy()
    net = result["Net"].to_numpy(dtype=float)
    gross = result["Gross"].to_numpy(dtype=float)
    dates = result.index
    n = len(net)

    if n == 0:
        result["Adj Close"] = pd.Series(dtype=float)
        return result

    tr = [1.0] * n
    for i in range(1, n):
        crosses_year = dates[i - 1].year < dates[i].year
        net_was_below = net[i - 1] < gross[i - 1] * (1 - tol)
        net_meets_gross = net[i] >= gross[i] * (1 - tol)
        is_reset = crosses_year and net_was_below and net_meets_gross
        ratio = 1.0 if is_reset else (net[i] / net[i - 1] if net[i - 1] else 1.0)
        tr[i] = tr[i - 1] * ratio

    scale = net[-1] / tr[-1] if tr[-1] else 1.0
    result["Adj Close"] = [v * scale for v in tr]
    return result


def parse_index_eod_csv(csv_text: str) -> pd.DataFrame:
    """Parse a TASE index historical-EOD CSV into a DataFrame.

    The index CSV has two metadata rows followed by a header row::

        תאריך, מדד בסיס, מדד נעילה, שווי שוק כולל (אלפי ש''ח)

    Returns:
        DataFrame with ``DatetimeIndex`` ("Date") and columns
        ``Open`` (base), ``Close`` (closing rate), ``Market Cap``.

    Raises:
        TaseParsingError: If the CSV cannot be parsed.
    """
    try:
        df = pd.read_csv(io.StringIO(csv_text), skiprows=2)
    except Exception as exc:
        raise TaseParsingError(f"Failed to read index CSV data: {exc}") from exc

    if df.empty:
        raise TaseParsingError("Index CSV contained no data rows")

    cols = df.columns.tolist()
    if len(cols) < 3:
        raise TaseParsingError(
            f"Index CSV has too few columns ({len(cols)}): {cols}"
        )

    result = pd.DataFrame()
    result["Date"] = pd.to_datetime(df[cols[0]], format="%d/%m/%Y")
    result["Open"] = pd.to_numeric(df[cols[1]], errors="coerce")     # base rate
    result["Close"] = pd.to_numeric(df[cols[2]], errors="coerce")    # closing rate
    if len(cols) >= 4:
        result["Market Cap"] = pd.to_numeric(df[cols[3]], errors="coerce")

    result = result.dropna(subset=["Close"])
    result = result.sort_values("Date").reset_index(drop=True)
    result = result.set_index("Date")

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


# Hebrew column name prefixes (fallback for Accept-Language: he-IL responses).
_HE_DATE = "\u05ea\u05d0\u05e8\u05d9\u05da"
_HE_ADJ_CLOSE = "\u05e9\u05e2\u05e8 \u05e0\u05e2\u05d9\u05dc\u05d4 \u05de\u05ea\u05d5\u05d0\u05dd"
_HE_CLOSE = "\u05e9\u05e2\u05e8 \u05e0\u05e2\u05d9\u05dc\u05d4"
_HE_OPEN = "\u05e9\u05e2\u05e8 \u05e4\u05ea\u05d9\u05d7\u05d4"
_HE_HIGH = "\u05e9\u05e2\u05e8 \u05d2\u05d1\u05d5\u05d4"
_HE_LOW = "\u05e9\u05e2\u05e8 \u05e0\u05de\u05d5\u05da"
_HE_VOL_UNITS = "\u05de\u05d7\u05d6\u05d5\u05e8 \u05d1\u05d9\u05d7\u05d9\u05d3\u05d5\u05ea"
_HE_VOL_TRADE = "\u05de\u05d7\u05d6\u05d5\u05e8 \u05d4\u05de\u05e1\u05d7\u05e8"


def _build_column_map(columns: list[str]) -> dict[str, str]:
    """Map CSV column headers to canonical names.

    Works with both English (``Accept-Language: en-US``) and Hebrew headers.

    Raises:
        TaseParsingError: If a required column cannot be found.
    """
    mapping: dict[str, str] = {}
    close_candidates: list[str] = []

    for col in columns:
        stripped = col.strip()
        if stripped.startswith(COL_DATE) or stripped.startswith(_HE_DATE):
            mapping["Date"] = col
        elif stripped.startswith(COL_ADJ_CLOSE) or stripped.startswith(_HE_ADJ_CLOSE):
            mapping["Adj Close"] = col
        elif stripped.startswith(COL_OPEN) or stripped.startswith(_HE_OPEN):
            mapping["Open"] = col
        elif stripped.startswith(COL_HIGH) or stripped.startswith(_HE_HIGH):
            mapping["High"] = col
        elif stripped.startswith(COL_LOW) or stripped.startswith(_HE_LOW):
            mapping["Low"] = col
        elif (
            stripped.startswith(COL_VOLUME_UNITS)
            or stripped.startswith(COL_VOLUME_TRADE)
            or stripped.startswith(_HE_VOL_UNITS)
            or stripped.startswith(_HE_VOL_TRADE)
        ):
            mapping.setdefault("Volume", col)
        elif stripped.startswith(COL_CLOSE) or stripped.startswith(_HE_CLOSE):
            close_candidates.append(col)

    # The unadjusted close column starts with COL_CLOSE / _HE_CLOSE but also
    # contains "(0.01 ILS)" / "(\u05d1\u05d0\u05d2\u05d5\u05e8\u05d5\u05ea)".  Pick the one that isn't Adj Close.
    if "Close" not in mapping and close_candidates:
        for candidate in close_candidates:
            if candidate != mapping.get("Adj Close"):
                mapping["Close"] = candidate
                break
        if "Close" not in mapping:
            mapping["Close"] = close_candidates[0]

    required = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
    missing = [k for k in required if k not in mapping]
    if missing:
        raise TaseParsingError(
            f"Missing required columns: {', '.join(missing)}. "
            f"Available columns: {columns}"
        )
    return mapping


def _build_etf_column_map(columns: list[str]) -> dict[str, str]:
    """Map ETF CSV column headers to canonical names.

    Extends :func:`_build_column_map` with ETF-specific optional columns.

    Raises:
        TaseParsingError: If a required column cannot be found.
    """
    # Start with the base OHLCV mapping.
    mapping = _build_column_map(columns)

    # Add ETF-specific optional columns.
    for col in columns:
        stripped = col.strip()
        if stripped.startswith(COL_PURCHASE_PRICE):
            mapping["Purchase Price"] = col
        elif stripped.startswith(COL_REDEMPTION_PRICE):
            mapping["Redemption Price"] = col
        elif stripped.startswith(COL_UNIT_PRICE):
            mapping["NAV"] = col
        elif stripped.startswith(COL_MANAGEMENT_FEE):
            mapping["Management Fee"] = col
        elif stripped.startswith(COL_TRUSTEE_FEE):
            mapping["Trustee Fee"] = col
        elif stripped.startswith(COL_MARKET_CAP):
            mapping["Market Cap"] = col

    return mapping
