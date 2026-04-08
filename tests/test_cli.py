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
