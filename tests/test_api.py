"""Tests for tasekit.api."""

from __future__ import annotations

import pytest
import responses

from tasekit.api import TaseClient, _ptype_for_years, _ptype_for_days
from tasekit.constants import BASE_URL, MAYA_BASE_URL
from tasekit.exceptions import TaseNetworkError


class TestPtypeForYears:
    """Tests for :func:`_ptype_for_years`."""

    @pytest.mark.parametrize(
        "years, expected",
        [
            (0, 0),
            (1, 4),
            (2, 5),
            (3, 6),
            (4, 7),
            (5, 7),
            (10, 7),
            (-1, 0),
        ],
    )
    def test_mapping(self, years: int, expected: int) -> None:
        assert _ptype_for_years(years) == expected


class TestPtypeForDays:
    """Tests for :func:`_ptype_for_days`."""

    @pytest.mark.parametrize(
        "days, expected",
        [
            (1, 0),
            (7, 1),
            (30, 1),
            (31, 2),
            (90, 2),
            (91, 3),
            (180, 3),
            (365, 4),
            (366, 5),
            (730, 5),
            (1095, 6),
            (1826, 7),
            (9999, 7),
        ],
    )
    def test_mapping(self, days: int, expected: int) -> None:
        assert _ptype_for_days(days) == expected


class TestTaseClient:
    """Tests for :class:`TaseClient`."""

    @responses.activate
    def test_fetch_eod_csv_success(self, sample_eod_csv: str) -> None:
        url = f"{BASE_URL}/export/securityhistoryeod"
        responses.add(responses.POST, url, body=sample_eod_csv, status=200)

        client = TaseClient()
        result = client.fetch_eod_csv("00604611", ptype=1)

        assert "Date" in result
        assert len(responses.calls) == 1

        # Verify correct headers were sent.
        req = responses.calls[0].request
        assert req.headers["Accept"] == "text/csv"
        assert "market.tase.co.il" in req.headers["Origin"]

    @responses.activate
    def test_fetch_eod_csv_sends_correct_payload(self) -> None:
        url = f"{BASE_URL}/export/securityhistoryeod"
        responses.add(responses.POST, url, body="a,b\n1,2", status=200)

        client = TaseClient()
        client.fetch_eod_csv("00604611", ptype=5)

        import json

        body = json.loads(responses.calls[0].request.body)
        assert body["FilterData"]["oId"] == "00604611"
        assert body["FilterData"]["pType"] == "5"

    @responses.activate
    def test_fetch_eod_csv_http_error(self) -> None:
        url = f"{BASE_URL}/export/securityhistoryeod"
        responses.add(responses.POST, url, status=500)

        client = TaseClient()
        with pytest.raises(TaseNetworkError):
            client.fetch_eod_csv("00604611", ptype=1)

    @responses.activate
    def test_fetch_eod_csv_waf_block(self) -> None:
        url = f"{BASE_URL}/export/securityhistoryeod"
        responses.add(
            responses.POST,
            url,
            body="<html>Request Rejected</html>",
            status=403,
        )

        client = TaseClient()
        with pytest.raises(TaseNetworkError):
            client.fetch_eod_csv("00604611", ptype=1)

    @responses.activate
    def test_fetch_etf_eod_csv_success(self, sample_etf_eod_csv: str) -> None:
        url = f"{BASE_URL}/export/etfhistoryeod"
        responses.add(responses.POST, url, body=sample_etf_eod_csv, status=200)

        client = TaseClient()
        result = client.fetch_etf_eod_csv("01159235", ptype=1)

        assert "Date" in result
        assert "Purchase Price" in result
        assert len(responses.calls) == 1

        req = responses.calls[0].request
        assert req.headers["Accept"] == "text/csv"
        assert "market.tase.co.il" in req.headers["Origin"]

    @responses.activate
    def test_fetch_etf_eod_csv_sends_correct_payload(self) -> None:
        url = f"{BASE_URL}/export/etfhistoryeod"
        responses.add(responses.POST, url, body="a,b\n1,2", status=200)

        client = TaseClient()
        client.fetch_etf_eod_csv("01159235", ptype=4)

        import json

        body = json.loads(responses.calls[0].request.body)
        assert body["FilterData"]["oId"] == "01159235"
        assert body["FilterData"]["pType"] == "4"

    @responses.activate
    def test_fetch_etf_eod_csv_http_error(self) -> None:
        url = f"{BASE_URL}/export/etfhistoryeod"
        responses.add(responses.POST, url, status=500)

        client = TaseClient()
        with pytest.raises(TaseNetworkError):
            client.fetch_etf_eod_csv("01159235", ptype=1)

    @responses.activate
    def test_fetch_security_data_success(self) -> None:
        url_pattern = f"{BASE_URL}/company/securitydata"
        responses.add(
            responses.GET,
            url_pattern,
            json={"Name": "LEUMI", "ISIN": "IL0006046119", "CompanyId": 604},
            status=200,
        )

        client = TaseClient()
        result = client.fetch_security_data("604611", lang=1)

        assert result["Name"] == "LEUMI"
        assert result["ISIN"] == "IL0006046119"
        req = responses.calls[0].request
        assert "securityId=604611" in req.url
        assert "lang=1" in req.url

    @responses.activate
    def test_fetch_security_data_null_response(self) -> None:
        """Returns None when API responds with JSON null (mutual funds)."""
        url_pattern = f"{BASE_URL}/company/securitydata"
        responses.add(responses.GET, url_pattern, body="null", status=200,
                      content_type="application/json")

        client = TaseClient()
        result = client.fetch_security_data("5122627", lang=1)
        assert result is None

    @responses.activate
    def test_fetch_security_data_lang_param(self) -> None:
        url_pattern = f"{BASE_URL}/company/securitydata"
        responses.add(responses.GET, url_pattern,
                      json={"Name": "\u05dc\u05d0\u05d5\u05de\u05d9"}, status=200)

        client = TaseClient()
        client.fetch_security_data("604611", lang=0)
        assert "lang=0" in responses.calls[0].request.url

    @responses.activate
    def test_fetch_security_majordata_with_comp_id(self) -> None:
        url_pattern = f"{BASE_URL}/security/majordata"
        responses.add(
            responses.GET, url_pattern,
            json={"LastDaysData": [], "CompanyDetails": {"Name": "LEUMI BANK"}},
            status=200,
        )

        client = TaseClient()
        client.fetch_security_majordata("604611", comp_id="604")
        url = responses.calls[0].request.url
        assert "secId=604611" in url
        assert "compId=604" in url

    @responses.activate
    def test_fetch_security_majordata_defaults_comp_id_to_sec_id(self) -> None:
        url_pattern = f"{BASE_URL}/security/majordata"
        responses.add(responses.GET, url_pattern, json={}, status=200)

        client = TaseClient()
        client.fetch_security_majordata("604611")
        url = responses.calls[0].request.url
        assert "compId=604611" in url

    @responses.activate
    def test_fetch_security_majordata(self) -> None:
        url_pattern = f"{BASE_URL}/security/majordata"
        responses.add(
            responses.GET,
            url_pattern,
            json={"LastDaysData": [{"LastRate": 7000}], "LastRates": []},
            status=200,
        )

        client = TaseClient()
        result = client.fetch_security_majordata("604611")

        assert result["LastDaysData"][0]["LastRate"] == 7000
        assert "secId=604611" in responses.calls[0].request.url

    @responses.activate
    def test_fetch_maya_fund_info(self) -> None:
        url = f"{MAYA_BASE_URL}/funds/mutual/5122627"
        responses.add(
            responses.GET,
            url,
            json={"fundId": 5122627, "name": "Test Fund"},
            status=200,
        )

        client = TaseClient()
        result = client.fetch_maya_fund_info("5122627")

        assert result["name"] == "Test Fund"
        # Verify Maya headers (not market.tase.co.il).
        req = responses.calls[0].request
        assert "maya.tase.co.il" in req.headers["Origin"]

    @responses.activate
    def test_fetch_maya_fund_history_csv(self) -> None:
        url = f"{MAYA_BASE_URL}/funds/mutual/5122627/history/file"
        body = (
            "\ufeffמס' קרן,תאריך,מחיר קניה,מחיר פדיון\n"
            "05122627,01.01.2026,100.00,100.50\n"
        )
        responses.add(responses.POST, url, body=body, status=200)

        client = TaseClient()
        result = client.fetch_maya_fund_history_csv(
            "5122627",
            "2025-01-01T00:00:00.000Z",
            "2026-04-06T00:00:00.000Z",
        )
        assert "מחיר פדיון" in result

    @responses.activate
    def test_fetch_index_details(self) -> None:
        url_pattern = f"{BASE_URL}/index/details"
        responses.add(
            responses.GET,
            url_pattern,
            json={"Name": "TA-35", "LastRate": 4248.43},
            status=200,
        )

        client = TaseClient()
        result = client.fetch_index_details("142")

        assert result["Name"] == "TA-35"
        assert "indexId=142" in responses.calls[0].request.url

    @responses.activate
    def test_fetch_index_eod_csv(self) -> None:
        url = f"{BASE_URL}/export/indexhistoryeod"
        body = "title\nrange\nDate,Base,Close,MCap\n01/01/2026,100,101,999\n"
        responses.add(responses.POST, url, body=body, status=200)

        client = TaseClient()
        result = client.fetch_index_eod_csv("142", ptype=4)

        assert "Date" in result

        import json
        req_body = json.loads(responses.calls[0].request.body)
        assert req_body["FilterData"]["oId"] == "142"
        assert req_body["FilterData"]["pType"] == "4"


class TestHedgeFundEndpoints:
    """Tests for the Maya hedge-fund methods of :class:`TaseClient`."""

    @responses.activate
    def test_fetch_hedge_fund_list(self) -> None:
        url = f"{MAYA_BASE_URL}/funds/hedge"
        responses.add(
            responses.POST, url,
            json=[{"fundId": 1194141, "name": "Harel Mul Str Mut He Fnd"}],
            status=200,
        )

        client = TaseClient()
        result = client.fetch_hedge_fund_list(page_number=2)

        assert result[0]["fundId"] == 1194141
        import json
        body = json.loads(responses.calls[0].request.body)
        assert body == {"pageSize": 30, "pageNumber": 2}
        assert "maya.tase.co.il" in responses.calls[0].request.headers["Origin"]

    @responses.activate
    def test_fetch_hedge_fund_list_error_envelope(self) -> None:
        url = f"{MAYA_BASE_URL}/funds/hedge"
        responses.add(
            responses.POST, url,
            json={"errors": {"PageSize": "must be between 1 and 30"}},
            status=200,
        )

        client = TaseClient()
        with pytest.raises(TaseNetworkError):
            client.fetch_hedge_fund_list(page_size=100)

    @responses.activate
    def test_fetch_hedge_fund_detail(self) -> None:
        url = f"{MAYA_BASE_URL}/funds/hedge/1194141"
        responses.add(
            responses.GET, url,
            json={"fundId": 1194141, "successFee": 20.0}, status=200,
        )

        client = TaseClient()
        result = client.fetch_hedge_fund_detail("1194141")

        assert result["fundId"] == 1194141
        req = responses.calls[0].request
        assert "maya.tase.co.il" in req.headers["Origin"]

    @responses.activate
    def test_fetch_hedge_fund_metadata(self) -> None:
        url = f"{MAYA_BASE_URL}/funds/metadata/1194141/history-hedge-fund"
        responses.add(
            responses.GET, url,
            json={"securities": [{"key": 1194869, "value": "x 03/23"}]},
            status=200,
        )

        client = TaseClient()
        result = client.fetch_hedge_fund_metadata("1194141")

        assert result["securities"][0]["key"] == 1194869

    @responses.activate
    def test_fetch_hedge_fund_history_snapshot(self) -> None:
        url = f"{MAYA_BASE_URL}/funds/hedge/1194141/history"
        responses.add(
            responses.POST, url,
            json=[{"fundId": "01242023", "tradeDate": "2026-05-28T00:00:00",
                   "purchasePrice": 360.41, "sellPrice": 360.41}],
            status=200,
        )

        client = TaseClient()
        result = client.fetch_hedge_fund_history("1194141")

        assert len(result) == 1
        import json
        body = json.loads(responses.calls[0].request.body)
        assert body == {"pageSize": 30, "pageNumber": 1}

    @responses.activate
    def test_fetch_hedge_fund_history_series(self) -> None:
        url = f"{MAYA_BASE_URL}/funds/hedge/1194141/history"
        responses.add(responses.POST, url, json=[], status=200)

        client = TaseClient()
        client.fetch_hedge_fund_history(
            "1194141",
            security_id="1194869",
            from_date="2023-01-01T00:00:00.000Z",
            to_date="2026-06-30T00:00:00.000Z",
            page_number=2,
        )

        import json
        body = json.loads(responses.calls[0].request.body)
        assert body["securityId"] == 1194869  # coerced to int
        assert body["fromDate"] == "2023-01-01T00:00:00.000Z"
        assert body["pageNumber"] == 2

    @responses.activate
    def test_fetch_hedge_fund_history_error_envelope(self) -> None:
        url = f"{MAYA_BASE_URL}/funds/hedge/1194141/history"
        responses.add(
            responses.POST, url,
            json={"errors": {"PageSize": "must be between 1 and 30"}},
            status=200,
        )

        client = TaseClient()
        with pytest.raises(TaseNetworkError):
            client.fetch_hedge_fund_history("1194141", page_size=100)
