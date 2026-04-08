"""Command-line interface for tasekit."""

from __future__ import annotations

import argparse
import json
import sys

from tasekit._version import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tasekit",
        description="Fetch data from the Tel Aviv Stock Exchange (TASE).",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )

    sub = parser.add_subparsers(dest="command", title="commands")

    # -- history sub-command ------------------------------------------------
    hist = sub.add_parser(
        "history",
        help="Fetch historical EOD data for a security or index.",
    )
    hist.add_argument(
        "id", metavar="ID",
        help=(
            "TASE security ID (e.g. 00604611) or index ID (e.g. 142). "
            "IDs with 1-3 digits are treated as indices; 6+ digits as securities."
        ),
    )
    hist.add_argument(
        "-y", "--years",
        type=int, default=None,
        help="Years of history (default: 2, max: 5). Ignored when --start is given.",
    )
    hist.add_argument(
        "-d", "--days",
        type=int, default=None,
        help="Days of history. Takes precedence over --years.",
    )
    hist.add_argument(
        "-s", "--start",
        default=None, metavar="DATE",
        help="Start date (YYYY-MM-DD).",
    )
    hist.add_argument(
        "-e", "--end",
        default=None, metavar="DATE",
        help="End date (YYYY-MM-DD). Defaults to today.",
    )
    hist.add_argument(
        "--etf",
        action="store_true",
        default=False,
        help="Use the ETF-specific endpoint (extra columns: purchase/redemption price, NAV, fees).",
    )
    hist.add_argument(
        "-o", "--output",
        default=None, metavar="FILE",
        help="Save output to a CSV file.",
    )
    hist.add_argument(
        "-f", "--format",
        default="table", choices=["table", "csv", "json"],
        help="Output format (default: table).",
    )

    # -- info sub-command ---------------------------------------------------
    info = sub.add_parser(
        "info",
        help="Show metadata / summary for a security or index.",
    )
    info.add_argument(
        "id", metavar="ID",
        help=(
            "TASE security ID (e.g. 00604611) or index ID (e.g. 142). "
            "IDs with 1-3 digits are treated as indices; 6+ digits as securities."
        ),
    )
    info.add_argument(
        "-f", "--format",
        default="text", choices=["text", "json"],
        help="Output format (default: text).",
    )

    return parser


# ---------------------------------------------------------------------------
# ID classification
# ---------------------------------------------------------------------------

def _is_index_id(id_str: str) -> bool:
    """Return True if *id_str* looks like a TASE index ID (1–3 digits)."""
    return id_str.isdigit() and len(id_str) <= 3


# ---------------------------------------------------------------------------
# Sub-command implementations
# ---------------------------------------------------------------------------

def _output_dataframe(
    df, *, label: str, fmt: str, output: str | None,
) -> None:
    """Common output logic for DataFrames."""
    if output:
        df.to_csv(output)
        print(f"Saved {len(df)} rows to {output}", file=sys.stderr)
        return

    if fmt == "csv":
        print(df.to_csv())
    elif fmt == "json":
        print(df.to_json(orient="index", date_format="iso", indent=2))
    else:
        print(
            f"{label} — {len(df)} trading days "
            f"({df.index.min().date()} to {df.index.max().date()})"
        )
        print(df.to_string())


def _output_info(data: dict, fmt: str) -> None:
    """Common output logic for info dicts."""
    if fmt == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    else:
        _print_info_text(data)


def _cmd_history(args: argparse.Namespace) -> None:
    from tasekit.exceptions import TaseError

    try:
        if _is_index_id(args.id):
            from tasekit import Index
            obj = Index(args.id)
            label = f"Index {obj.id}"
        else:
            from tasekit import Security
            obj = Security(args.id)
            label = f"Security {obj.id}"

        if getattr(args, 'etf', False) and not _is_index_id(args.id):
            df = obj.etf_history(
                years=args.years, days=args.days, start=args.start, end=args.end
            )
        else:
            df = obj.history(
                years=args.years, days=args.days, start=args.start, end=args.end
            )
    except (TaseError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    _output_dataframe(df, label=label, fmt=args.format, output=args.output)


def _cmd_info(args: argparse.Namespace) -> None:
    from tasekit.exceptions import TaseError

    try:
        if _is_index_id(args.id):
            from tasekit import Index
            data = Index(args.id).info()
        else:
            from tasekit import Security
            data = Security(args.id).info()
    except (TaseError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    _output_info(data, args.format)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_info_text(data: dict, indent: int = 0) -> None:
    """Pretty-print an info dict to stdout."""
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            _print_info_text(value, indent + 1)
        elif isinstance(value, list):
            print(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    parts = [f"{k}={v}" for k, v in item.items()]
                    print(f"{prefix}  - {', '.join(parts)}")
                else:
                    print(f"{prefix}  - {item}")
        else:
            print(f"{prefix}{key}: {value}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``tasekit`` CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "history":
        _cmd_history(args)
    elif args.command == "info":
        _cmd_info(args)


if __name__ == "__main__":
    main()
