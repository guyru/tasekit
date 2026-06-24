"""Tests for the tasekit CLI."""

from __future__ import annotations

import subprocess
import sys


class TestCliHelp:
    """Smoke tests for CLI argument parsing."""

    def test_version(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tasekit.cli", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "tasekit" in result.stdout

    def test_no_args_shows_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tasekit.cli"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "commands" in result.stdout or "history" in result.stdout

    def test_history_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tasekit.cli", "history", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "ID" in result.stdout
        assert "--days" in result.stdout
        assert "index" in result.stdout.lower()

    def test_info_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tasekit.cli", "info", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "ID" in result.stdout
        assert "--format" in result.stdout


class TestHedgeCliParsing:
    """Hedge-fund CLI flags appear in help."""

    def test_history_hedge_flag_in_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tasekit.cli", "history", "--help"],
            capture_output=True, text=True,
        )
        assert "--hedge" in result.stdout
        assert "--series" in result.stdout
        assert "--gross" in result.stdout

    def test_info_hedge_flag_in_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tasekit.cli", "info", "--help"],
            capture_output=True, text=True,
        )
        assert "--hedge" in result.stdout

    def test_list_hedge_flag_in_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tasekit.cli", "list", "--help"],
            capture_output=True, text=True,
        )
        assert "--hedge" in result.stdout


class TestHedgeCliRouting:
    """In-process routing tests (patch HedgeFund, no network)."""

    def test_history_routes_to_hedge_fund(self, monkeypatch) -> None:
        import pandas as pd
        import tasekit
        from tasekit import cli

        captured = {}

        class FakeHedge:
            def __init__(self, fund_id):
                captured["id"] = fund_id
                self.id = fund_id

            def history(self, **kwargs):
                captured["history_kwargs"] = kwargs
                return pd.DataFrame(
                    {"Gross": [1.0], "Net": [0.9], "Adj Close": [0.9]},
                    index=pd.DatetimeIndex(["2026-05-28"], name="Date"),
                )

        monkeypatch.setattr(tasekit, "HedgeFund", FakeHedge)
        cli.main(["history", "1194141", "--hedge", "--series", "1233857"])

        assert captured["id"] == "1194141"
        assert captured["history_kwargs"]["security_id"] == "1233857"

    def test_info_routes_to_hedge_fund(self, monkeypatch) -> None:
        import tasekit
        from tasekit import cli

        captured = {}

        class FakeHedge:
            def __init__(self, fund_id):
                captured["id"] = fund_id

            def info(self):
                return {"fund_id": 1194141, "name": "x"}

        monkeypatch.setattr(tasekit, "HedgeFund", FakeHedge)
        cli.main(["info", "1194141", "--hedge"])
        assert captured["id"] == "1194141"

    def test_list_routes_to_hedge_fund(self, monkeypatch, capsys) -> None:
        import pandas as pd
        import tasekit
        from tasekit import cli

        called = {}

        class FakeHedge:
            @classmethod
            def list(cls):
                called["list"] = True
                return pd.DataFrame(
                    {"Name": ["Harel"], "Manager": ["HAREL"]},
                    index=pd.Index(["1194141"], name="Fund ID"),
                )

        monkeypatch.setattr(tasekit, "HedgeFund", FakeHedge)
        cli.main(["list", "--hedge"])

        assert called["list"] is True
        out = capsys.readouterr().out
        assert "1194141" in out
        assert "Harel" in out

    def test_list_without_type_errors(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tasekit.cli", "list"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "--hedge" in result.stderr
