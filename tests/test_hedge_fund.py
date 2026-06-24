"""Tests for tasekit.hedge_fund."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tasekit.api import TaseClient
from tasekit.constants import MAYA_HEDGE_MAX_PAGE_SIZE
from tasekit.exceptions import SecurityNotFoundError
from tasekit.hedge_fund import HedgeFund


def _fund_row(fund_id: int) -> dict:
    return {"fundId": fund_id, "name": f"Fund {fund_id}", "classification": {}}


def _client_with(
    *, metadata=None, detail=None, snapshot=None, history_pages=None, list_pages=None
) -> MagicMock:
    client = MagicMock(spec=TaseClient)
    if metadata is not None:
        client.fetch_hedge_fund_metadata.return_value = metadata
    if detail is not None:
        client.fetch_hedge_fund_detail.return_value = detail
    if history_pages is not None:
        client.fetch_hedge_fund_history.side_effect = history_pages
    elif snapshot is not None:
        client.fetch_hedge_fund_history.return_value = snapshot
    if list_pages is not None:
        client.fetch_hedge_fund_list.side_effect = list_pages
    return client


class TestNormalizeId:
    def test_strips_leading_zeros(self) -> None:
        assert HedgeFund("01194141", client=MagicMock()).id == "1194141"

    def test_rejects_non_numeric(self) -> None:
        with pytest.raises(ValueError):
            HedgeFund("abc", client=MagicMock())


class TestList:
    def test_single_short_page(self, hedge_list_page: list) -> None:
        client = _client_with(list_pages=[hedge_list_page])
        df = HedgeFund.list(client=client)
        assert df.index.name == "Fund ID"
        assert len(df) == 3
        # A short first page stops pagination after one call.
        assert client.fetch_hedge_fund_list.call_count == 1

    def test_paginates_until_short_page(self) -> None:
        full = [_fund_row(1000000 + i) for i in range(MAYA_HEDGE_MAX_PAGE_SIZE)]
        tail = [_fund_row(2000000 + i) for i in range(5)]
        client = _client_with(list_pages=[full, tail])
        df = HedgeFund.list(client=client)
        assert len(df) == MAYA_HEDGE_MAX_PAGE_SIZE + 5
        assert client.fetch_hedge_fund_list.call_count == 2

    def test_empty_raises(self) -> None:
        client = _client_with(list_pages=[[]])
        with pytest.raises(SecurityNotFoundError):
            HedgeFund.list(client=client)


class TestSeriesAndAnchor:
    def test_series_sorted_oldest_first(self, hedge_metadata: dict) -> None:
        fund = HedgeFund("1194141", client=_client_with(metadata=hedge_metadata))
        series = fund.series()
        ids = [int(s["security_id"]) for s in series]
        assert ids == sorted(ids)
        assert len(ids) == len(hedge_metadata["securities"])

    def test_anchor_is_lowest_id(self, hedge_metadata: dict) -> None:
        fund = HedgeFund("1194141", client=_client_with(metadata=hedge_metadata))
        assert fund.anchor_id() == "1194869"

    def test_series_cached(self, hedge_metadata: dict) -> None:
        client = _client_with(metadata=hedge_metadata)
        fund = HedgeFund("1194141", client=client)
        fund.series()
        fund.series()
        assert client.fetch_hedge_fund_metadata.call_count == 1

    def test_anchor_raises_when_empty(self) -> None:
        fund = HedgeFund("1194141", client=_client_with(metadata={"securities": []}))
        with pytest.raises(SecurityNotFoundError):
            fund.anchor_id()


class TestInfo:
    def test_flattens_detail(self, hedge_detail: dict) -> None:
        fund = HedgeFund("1194141", client=_client_with(detail=hedge_detail))
        info = fund.info()
        assert info["fund_id"] == 1194141
        assert info["success_fee"] == 20.0
        assert info["management_fee"] == 1.5
        assert "current_series" in info
        assert info["redemption"]["days"] == 10
        # current_series carries each live series' net/gross.
        assert info["current_series"][0]["gross"] == 360.41


class TestRedemptionSnapshot:
    def test_snapshot_indexed_by_security(self, hedge_snapshot: list) -> None:
        fund = HedgeFund("1194141", client=_client_with(snapshot=hedge_snapshot))
        df = fund.redemption_snapshot()
        assert df.index.name == "Security ID"
        assert len(df) == 6
        assert {"Gross", "Net"}.issubset(df.columns)


class TestHistory:
    def test_defaults_to_anchor(self, hedge_metadata, hedge_anchor_history) -> None:
        client = _client_with(
            metadata=hedge_metadata,
            history_pages=[hedge_anchor_history[:30], hedge_anchor_history[30:]],
        )
        fund = HedgeFund("1194141", client=client)
        df = fund.history()

        # First history call used the anchor ID.
        first_call = client.fetch_hedge_fund_history.call_args_list[0]
        assert first_call.kwargs["security_id"] == "1194869"
        assert list(df.columns) == ["Gross", "Net", "Adj Close"]
        assert len(df) == 41

    def test_pagination_stops_on_short_page(
        self, hedge_metadata, hedge_anchor_history
    ) -> None:
        client = _client_with(
            metadata=hedge_metadata,
            history_pages=[hedge_anchor_history[:30], hedge_anchor_history[30:]],
        )
        fund = HedgeFund("1194141", client=client)
        fund.history()
        # 41 rows -> page1 (30, full) then page2 (11, short) -> stop. 2 calls.
        assert client.fetch_hedge_fund_history.call_count == 2

    def test_pagination_uses_max_page_size(
        self, hedge_metadata, hedge_anchor_history
    ) -> None:
        client = _client_with(
            metadata=hedge_metadata,
            history_pages=[hedge_anchor_history[:30], hedge_anchor_history[30:]],
        )
        HedgeFund("1194141", client=client).history()
        assert (
            client.fetch_hedge_fund_history.call_args_list[0].kwargs["page_size"]
            == MAYA_HEDGE_MAX_PAGE_SIZE
        )

    def test_explicit_series_id(self, hedge_snapshot) -> None:
        client = _client_with(history_pages=[hedge_snapshot])
        fund = HedgeFund("1194141", client=client)
        fund.history(security_id="1233857")
        assert (
            client.fetch_hedge_fund_history.call_args_list[0].kwargs["security_id"]
            == "1233857"
        )
        # anchor (metadata) not needed when series is explicit.
        client.fetch_hedge_fund_metadata.assert_not_called()

    def test_empty_history_raises(self, hedge_metadata) -> None:
        client = _client_with(metadata=hedge_metadata, history_pages=[[]])
        fund = HedgeFund("1194141", client=client)
        with pytest.raises(SecurityNotFoundError):
            fund.history()


class TestPerformance:
    def test_net_performance_recent_equals_actual(
        self, hedge_metadata, hedge_anchor_history
    ) -> None:
        client = _client_with(
            metadata=hedge_metadata,
            history_pages=[hedge_anchor_history[:30], hedge_anchor_history[30:]],
        )
        fund = HedgeFund("1194141", client=client)
        perf = fund.performance(net=True)
        assert list(perf.columns) == ["Performance"]
        # Last net-of-fees value == last raw net (346.15).
        assert perf["Performance"].iloc[-1] == pytest.approx(346.15)
        # ~+195% total return since inception.
        ratio = perf["Performance"].iloc[-1] / perf["Performance"].iloc[0]
        assert ratio == pytest.approx(2.952, abs=1e-3)

    def test_gross_performance(self, hedge_metadata, hedge_anchor_history) -> None:
        client = _client_with(
            metadata=hedge_metadata,
            history_pages=[hedge_anchor_history[:30], hedge_anchor_history[30:]],
        )
        fund = HedgeFund("1194141", client=client)
        perf = fund.performance(net=False)
        ratio = perf["Performance"].iloc[-1] / perf["Performance"].iloc[0]
        assert ratio == pytest.approx(3.6041, abs=1e-3)

    def test_anchor_history_cached_across_net_and_gross(
        self, hedge_metadata, hedge_anchor_history
    ) -> None:
        # Two pages consumed once; a second fetch would exhaust the side_effect.
        client = _client_with(
            metadata=hedge_metadata,
            history_pages=[hedge_anchor_history[:30], hedge_anchor_history[30:]],
        )
        fund = HedgeFund("1194141", client=client)
        net = fund.performance(net=True)
        gross = fund.performance(net=False)
        # Both derived from a single full-life fetch (2 pages, no re-fetch).
        assert client.fetch_hedge_fund_history.call_count == 2
        assert net["Performance"].iloc[-1] == pytest.approx(346.15)
        assert gross["Performance"].iloc[-1] == pytest.approx(360.41)
