# tasekit — Agent Instructions

## Project Overview

**tasekit** is a Python library and CLI for fetching financial data from the
Tel Aviv Stock Exchange (TASE) via web scraping of `api.tase.co.il` and
`maya.tase.co.il`. Inspired by [yfinance](https://github.com/ranaroussi/yfinance).

Repository: https://github.com/guyru/tasekit

## Project Structure

```
tasekit/
├── README.md               # user-facing quick-start
├── AGENTS.md               # this file
├── docs/
│   ├── DESIGN.md           # architecture reference (current state)
│   ├── ENDPOINTS.md        # complete API endpoint catalog
│   └── TODO.md             # roadmap and known issues
├── src/tasekit/            # library source (src layout)
│   ├── __init__.py         # public API: Security, HedgeFund, Index, download()
│   ├── _version.py         # single source of version
│   ├── api.py              # low-level HTTP client (TaseClient)
│   ├── cli.py              # CLI entry point (argparse, unified history/info)
│   ├── constants.py        # URLs, headers, pType maps, column name prefixes
│   ├── exceptions.py       # TaseError hierarchy
│   ├── hedge_fund.py       # HedgeFund class (mutual hedge funds, Maya)
│   ├── index.py            # Index class (market indices)
│   ├── parsers.py          # CSV/JSON response parsers
│   └── security.py         # Security class (stocks, ETFs, bonds, mutual funds)
└── tests/
    ├── conftest.py         # shared fixtures
    ├── test_api.py
    ├── test_cli.py
    ├── test_hedge_fund.py
    ├── test_index.py
    ├── test_parsers.py
    ├── test_security.py
    └── data/               # sample fixtures from real API responses (CSV + hedge_*.json)
```

## Key Design Decisions

- **src/ layout** — prevents accidental imports from the source tree.
- **Two API domains**: `api.tase.co.il` (main market data, Imperva WAF on ~half
  the endpoints) and `maya.tase.co.il` (mutual funds, no WAF).
- **`company/securitydata`** is the primary source for `Security.info()`. It
  returns JSON `null` for mutual funds — the definitive mutual fund detection
  mechanism. No ID prefix heuristic is reliable.
- **`security/majordata`** supplements `info()` with index memberships, short
  sales, statistics. Pass the real `CompanyId` (from `securitydata`) to unlock
  `CompanyDetails` (description, website).
- **`Accept-Language: en-US`** — controls CSV export language. English headers,
  English values, English security names.
- **Automatic fallback**: `Security.history()` and `Security.info()` try the
  main TASE API first, then fall back to Maya for mutual funds.
- **Unified CLI**: `tasekit history` and `tasekit info` auto-detect index
  (1–3 digit ID) vs security (6+ digit ID). `--etf` flag uses the ETF-specific
  endpoint; `--hedge` routes to `HedgeFund`.
- **Mutual hedge funds** (`HedgeFund`, Maya only): a new `securityId` is minted
  monthly; fees accrue intra-year (net < gross) then crystallize at year-end by
  converting holdings into the **oldest** series. The oldest series is the
  continuous performance anchor; `add_hedge_fund_adj_close()` removes the
  January reset jumps to build a net-of-fees total-return series. Not
  auto-detectable from the main API, so it requires the explicit class/flag.
  See `docs/HEDGE_FUNDS_PLAN.md`.
- **Pandas DataFrames** are the native return type from `history()`.
- **Security IDs** are normalised to zero-padded 8-digit strings internally.
- **Index IDs** are short numeric strings (e.g. `"142"` for TA-35).

## Development

```bash
uv venv .venv
uv pip install -e ".[dev]"
.venv/bin/python -m pytest tests/ -v     # run tests (205 tests)
.venv/bin/ruff check src/ tests/         # lint
uv run tasekit history 00604611          # smoke test (stock)
uv run tasekit history 142 -d 30         # smoke test (index)
uv run tasekit info 00604611             # smoke test (rich metadata)
uv run tasekit info 5122627              # smoke test (mutual fund)
uv run tasekit history 01144724 --etf    # smoke test (ETF with fund prices)
uv run tasekit history 1194141 --hedge   # smoke test (hedge fund, net Adj Close)
uv run tasekit info 1194141 --hedge      # smoke test (hedge fund metadata)
uv run tasekit list --hedge              # smoke test (all hedge funds)
```

Testing uses `responses` to mock HTTP calls. Every API method in `TaseClient`
has a corresponding mocked test in `test_api.py`. The `tests/data/` directory
contains real captured API responses (English) used as fixtures.

## Architecture

### Data Flow

```
User → Security.history()
         ├─ TaseClient.fetch_eod_csv()        → api.tase.co.il (Accept-Language: en-US)
         │    → parsers.parse_eod_csv()       → DataFrame (Open/High/Low/Close/Adj Close/Volume)
         └─ (fallback) TaseClient.fetch_maya_fund_history_csv() → maya.tase.co.il
              → parsers.parse_maya_fund_csv() → DataFrame (Close only)

User → Security.etf_history()
         └─ TaseClient.fetch_etf_eod_csv()    → api.tase.co.il
              → parsers.parse_etf_eod_csv()   → DataFrame (OHLCV + optional ETF cols)

User → Security.info()
         ├─ TaseClient.fetch_security_data(lang=1)  → company/securitydata (English)
         │    Returns None → mutual fund → Maya fallback
         ├─ TaseClient.fetch_security_data(lang=0)  → company/securitydata (Hebrew name)
         └─ TaseClient.fetch_security_majordata(comp_id=real_id)
              → security/majordata (indices, short sales, stats, description)

User → Index.history()
         └─ TaseClient.fetch_index_eod_csv()  → export/indexhistoryeod

User → Index.info()
         └─ TaseClient.fetch_index_details()  → index/details

User → HedgeFund.list()  (classmethod)
         └─ TaseClient.fetch_hedge_fund_list(paginated) → funds/hedge (POST, en-US)
              → parsers.parse_hedge_fund_list() → DataFrame (indexed by Fund ID)

User → HedgeFund.performance() / .history()
         ├─ TaseClient.fetch_hedge_fund_metadata()  → funds/metadata/{id}/history-hedge-fund (series list, anchor)
         └─ TaseClient.fetch_hedge_fund_history(securityId=anchor, paginated) → funds/hedge/{id}/history
              → parsers.parse_hedge_fund_history() → add_hedge_fund_adj_close() → DataFrame (Gross/Net/Adj Close)

User → HedgeFund.info()
         └─ TaseClient.fetch_hedge_fund_detail() → funds/hedge/{id}
```

### API Constraints

- The TASE EOD endpoint only supports predefined time windows via `pType`
  (1d, 1mo, 3mo, 6mo, 1y, 2y, 3y, 5y) — not arbitrary date ranges. The
  library picks the smallest window that covers the request and trims.
- The Maya API supports arbitrary `fromDate`/`toDate` ranges.
- About half the `api.tase.co.il` endpoints are blocked by Imperva WAF.
  See `docs/ENDPOINTS.md` for the full catalog.
- Mutual funds: `company/securitydata` returns JSON `null`. There is no
  reliable ID prefix to identify them — numeric ranges overlap with
  exchange-traded securities.

### Important Files to Read First

1. `docs/TODO.md` — roadmap, known issues, next steps
2. `docs/ENDPOINTS.md` — complete API endpoint catalog with accessibility status
3. `docs/DESIGN.md` — architecture reference
4. `src/tasekit/security.py` — main user-facing class
5. `src/tasekit/api.py` — all HTTP interaction
6. `src/tasekit/constants.py` — URLs, headers, column name mappings

## Conventions

- Python ≥ 3.11; use `X | Y` union syntax, not `Optional[X]`.
- Use `ruff` for linting and formatting (line length 99).
- Tests use `pytest` with `responses` for HTTP mocking and
  `unittest.mock.MagicMock` for `TaseClient` injection.
- Every new API endpoint added to `TaseClient` must have a corresponding
  mocked test in `test_api.py`.
- Public API changes must be reflected in `__init__.py`, `README.md`, and
  the CLI.
- Test fixtures use English CSV data (matching the `Accept-Language: en-US`
  default).

## Adding a New Data Source / Endpoint

1. Add the HTTP method to `TaseClient` in `api.py`.
2. Add a parser function in `parsers.py` if the response format is new.
3. Wire it into `Security`, `Index`, or a new class.
4. Add mocked tests in `test_api.py`, parser tests in `test_parsers.py`,
   and integration tests in the appropriate `test_*.py`.
5. Document the endpoint in `docs/ENDPOINTS.md`.
6. Expose in CLI (`cli.py`) if user-facing.
7. Update `README.md`.
