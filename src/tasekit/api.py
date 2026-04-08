"""Low-level HTTP client for the TASE API."""

from __future__ import annotations

import requests

from tasekit.constants import (
    BASE_URL,
    DEFAULT_HEADERS,
    MAYA_BASE_URL,
    MAYA_HEADERS,
    PTYPE_DAYS_THRESHOLDS,
    PTYPE_MAP,
    MAX_HISTORY_YEARS,
)
from tasekit.exceptions import TaseNetworkError


def _ptype_for_years(years: int) -> int:
    """Return the smallest pType value that covers *years* years of history."""
    if years <= 0:
        return 0
    if years >= MAX_HISTORY_YEARS:
        return 7
    return PTYPE_MAP.get(years, 7)


def _ptype_for_days(days: int) -> int:
    """Return the smallest pType value that covers *days* days of history."""
    for max_days, ptype in PTYPE_DAYS_THRESHOLDS:
        if days <= max_days:
            return ptype
    return 7  # maximum


class TaseClient:
    """Thin wrapper around :mod:`requests` for talking to ``api.tase.co.il``
    and ``maya.tase.co.il``.

    A single :class:`requests.Session` is reused for connection pooling.
    """

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()
        # Only set the User-Agent on the session; Origin/Referer vary by API domain.
        self._session.headers["User-Agent"] = DEFAULT_HEADERS["User-Agent"]

    # ------------------------------------------------------------------
    # CSV export helpers (api.tase.co.il)
    # ------------------------------------------------------------------

    def fetch_eod_csv(
        self, security_id: str, ptype: int, *, accept_language: str | None = None
    ) -> str:
        """Fetch historical end-of-day CSV for a security.

        Args:
            security_id: Zero-padded 8-digit TASE security ID.
            ptype: TASE ``pType`` value (0–7).
            accept_language: Override the ``Accept-Language`` header
                (e.g. ``"he-IL"`` for Hebrew).  Defaults to the
                session default (``"en-US"``).

        Returns:
            Raw CSV text (UTF-8, BOM stripped).

        Raises:
            TaseNetworkError: On any HTTP / connectivity failure.
        """
        url = f"{BASE_URL}/export/securityhistoryeod"
        payload = {
            "FilterData": {
                "pType": str(ptype),
                "TotalRec": 1,
                "pageNum": 1,
                "oId": security_id,
                "lang": "0",
            },
            "isAdd": False,
            "callerName": "security-history-eod",
        }
        extra: dict[str, str] | None = None
        if accept_language is not None:
            extra = {**DEFAULT_HEADERS, "Accept-Language": accept_language}
        return self._post_csv(url, payload, extra_headers=extra)

    def fetch_etf_eod_csv(self, security_id: str, ptype: int) -> str:
        """Fetch historical end-of-day CSV for an ETF.

        Uses the ``export/etfhistoryeod`` endpoint which returns extra
        ETF-specific columns (purchase price, redemption price, NAV,
        management fee, trustee fee) compared to the generic
        ``securityhistoryeod`` endpoint.

        Args:
            security_id: Zero-padded 8-digit TASE security ID.
            ptype: TASE ``pType`` value (0–7).

        Returns:
            Raw CSV text (UTF-8, BOM stripped).

        Raises:
            TaseNetworkError: On any HTTP / connectivity failure.
        """
        url = f"{BASE_URL}/export/etfhistoryeod"
        payload = {
            "FilterData": {
                "pType": str(ptype),
                "TotalRec": 1,
                "pageNum": 1,
                "oId": security_id,
                "lang": "0",
            },
            "isAdd": False,
            "callerName": "etf-history-eod",
        }
        return self._post_csv(url, payload)

    # ------------------------------------------------------------------
    # JSON helpers (api.tase.co.il)
    # ------------------------------------------------------------------

    def fetch_security_data(self, security_id: str, lang: int = 1) -> dict | None:
        """Fetch the ``company/securitydata`` JSON for a security.

        Returns rich metadata: ISIN, symbol, sector, yields, type,
        bond-specific fields (redemption date, interest, linkage),
        ETF-specific fields (creation/sell/unit price, underlying asset),
        and the real ``CompanyId`` needed for a correct ``majordata`` call.

        Args:
            security_id: Unpadded numeric security ID.
            lang: 0 = Hebrew, 1 = English.

        Returns:
            Parsed JSON dict, or ``None`` when the API returns ``null``
            (e.g. for mutual funds that are not exchange-traded).

        Raises:
            TaseNetworkError: On any HTTP / connectivity failure.
        """
        url = f"{BASE_URL}/company/securitydata?securityId={security_id}&lang={lang}"
        raw = self._get_json_nullable(url, headers=DEFAULT_HEADERS)
        return raw  # None when the API returns JSON null

    def fetch_security_majordata(
        self, security_id: str, lang: int = 1, comp_id: str | None = None
    ) -> dict:
        """Fetch the ``security/majordata`` JSON for a security.

        Args:
            security_id: Unpadded numeric security ID.
            lang: 0 = Hebrew, 1 = English.
            comp_id: Company ID for the ``compId`` parameter.  When
                provided this unlocks ``CompanyDetails`` (description,
                website, etc.).  Falls back to *security_id* when omitted.

        Returns:
            Parsed JSON dict.
        """
        cid = comp_id or security_id
        url = (
            f"{BASE_URL}/security/majordata"
            f"?secId={security_id}&compId={cid}&lang={lang}"
        )
        return self._get_json(url, headers=DEFAULT_HEADERS)

    def fetch_index_details(self, index_id: str, lang: int = 1) -> dict:
        """Fetch the ``index/details`` JSON for an index.

        Args:
            index_id: TASE index ID (e.g. ``"142"`` for TA-35).
            lang: 0 = Hebrew, 1 = English.

        Returns:
            Parsed JSON dict with name, rates, yields, market value, etc.
        """
        url = f"{BASE_URL}/index/details?indexId={index_id}&lang={lang}"
        return self._get_json(url, headers=DEFAULT_HEADERS)

    # ------------------------------------------------------------------
    # Index CSV export helpers
    # ------------------------------------------------------------------

    def fetch_index_eod_csv(self, index_id: str, ptype: int) -> str:
        """Fetch historical end-of-day CSV for an index.

        Args:
            index_id: TASE index ID (e.g. ``"142"``).
            ptype: TASE ``pType`` value (0\u20137).

        Returns:
            Raw CSV text.
        """
        url = f"{BASE_URL}/export/indexhistoryeod"
        payload = {
            "FilterData": {
                "pType": str(ptype),
                "TotalRec": 1,
                "pageNum": 1,
                "oId": index_id,
                "lang": "0",
            },
            "isAdd": False,
            "callerName": "index-history-eod",
        }
        return self._post_csv(url, payload)

    # ------------------------------------------------------------------
    # Maya API helpers (maya.tase.co.il)
    # ------------------------------------------------------------------

    def fetch_maya_fund_info(self, fund_id: str) -> dict:
        """Fetch mutual-fund details from the Maya API.

        Args:
            fund_id: Numeric fund ID (e.g. ``"5122627"``).

        Returns:
            Parsed JSON dict with fund metadata, yields, classification, etc.
        """
        url = f"{MAYA_BASE_URL}/funds/mutual/{fund_id}"
        return self._get_json(url, headers=MAYA_HEADERS)

    def fetch_maya_fund_history_csv(
        self, fund_id: str, from_date: str, to_date: str
    ) -> str:
        """Fetch mutual-fund NAV history CSV from the Maya API.

        Args:
            fund_id: Numeric fund ID.
            from_date: ISO date string ``"YYYY-MM-DDT00:00:00.000Z"``.
            to_date: ISO date string.

        Returns:
            Raw CSV text.
        """
        url = f"{MAYA_BASE_URL}/funds/mutual/{fund_id}/history/file"
        payload = {
            "pageSize": 20,
            "pageNumber": 1,
            "period": 4,
            "fromDate": from_date,
            "toDate": to_date,
        }
        return self._post_csv(url, payload, extra_headers=MAYA_HEADERS)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post_csv(
        self,
        url: str,
        payload: dict,
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> str:
        """POST *payload* as JSON expecting a CSV response."""
        headers: dict[str, str] = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "text/csv",
        }
        if extra_headers:
            headers.update(extra_headers)
        else:
            headers.update(DEFAULT_HEADERS)
        try:
            resp = self._session.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise TaseNetworkError(str(exc)) from exc
        return resp.content.decode("utf-8-sig")

    def _get_json(self, url: str, headers: dict[str, str]) -> dict:
        """GET *url* expecting a JSON object response."""
        req_headers = {
            "Accept": "application/json",
            **headers,
        }
        try:
            resp = self._session.get(url, headers=req_headers)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise TaseNetworkError(str(exc)) from exc
        try:
            return resp.json()
        except ValueError as exc:
            raise TaseNetworkError(f"Invalid JSON response: {exc}") from exc

    def _get_json_nullable(self, url: str, headers: dict[str, str]) -> dict | None:
        """GET *url* expecting a JSON object or JSON null response.

        Returns ``None`` when the server responds with a literal JSON
        ``null`` body (as ``company/securitydata`` does for mutual funds).
        """
        req_headers = {
            "Accept": "application/json",
            **headers,
        }
        try:
            resp = self._session.get(url, headers=req_headers)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise TaseNetworkError(str(exc)) from exc
        try:
            result = resp.json()
        except ValueError as exc:
            raise TaseNetworkError(f"Invalid JSON response: {exc}") from exc
        # The API returns literal JSON null for non-exchange-traded securities.
        return result if isinstance(result, dict) else None

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()


# ------------------------------------------------------------------
# Module-level default client (lazy singleton)
# ------------------------------------------------------------------

_default_client: TaseClient | None = None


def get_default_client() -> TaseClient:
    """Return (and lazily create) the module-level default :class:`TaseClient`."""
    global _default_client  # noqa: PLW0603
    if _default_client is None:
        _default_client = TaseClient()
    return _default_client
