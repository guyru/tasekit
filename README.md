# tasekit

Fetch financial data from the Tel Aviv Stock Exchange (TASE).

Inspired by [yfinance](https://github.com/ranaroussi/yfinance), **tasekit** provides
a simple Python API and CLI for downloading historical market data from
[market.tase.co.il](https://market.tase.co.il).

Supports stocks, ETFs, bonds, mutual funds, and market indices.

## Installation

```bash
pip install git+https://github.com/guyru/tasekit.git
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install git+https://github.com/guyru/tasekit.git
```

For development:

```bash
git clone https://github.com/guyru/tasekit.git
cd tasekit
uv venv .venv
uv pip install -e ".[dev]"
```

## Quick Start

### Python API

```python
import tasekit

# Historical OHLC data — stocks, ETFs, bonds
sec = tasekit.Security("00604611")   # Bank Leumi
df = sec.history()                   # default: 2 years
df = sec.history(years=5)
df = sec.history(days=30)
df = sec.history(start="2024-01-01", end="2024-12-31")

# ETF history with extra columns (NAV, purchase/redemption price, fees)
etf = tasekit.Security("01144724")
df = etf.etf_history(years=1)

# Mutual funds — automatically uses the Maya API
fund = tasekit.Security("5122627")
df = fund.history(years=1)

# Bonds work the same way
bond = tasekit.Security("01193580")
df = bond.history(days=90)

# Convenience function
df = tasekit.download("00604611", years=2)

# Security metadata
info = sec.info()
# Returns: name, name_he, long_name, company_name, symbol, isin,
#          type, sub_type, sector, last_rate, change_pct, trade_date,
#          month_yield, annual_yield, market_value, description, website,
#          intraday_rate, intraday_time, trading_stage,
#          indices (with weights), short_sale_value, statistics
#          + bond fields: redemption_date, annual_interest, linkage, ...
#          + ETF fields:  nav, creation_price, sell_price, fund_update_date

# Mutual hedge funds (קרן גידור בנאמנות) — Maya, explicit class
funds = tasekit.HedgeFund.list()  # every hedge fund on TASE (DataFrame)
hf = tasekit.HedgeFund("1194141")
perf = hf.performance()          # net-of-fees total-return series (Performance)
perf = hf.performance(net=False) # gross (fee-free) series
df = hf.history()                # anchor series: Gross, Net, Adj Close
snap = hf.redemption_snapshot()  # current live monthly series + net/gross
info = hf.info()                 # fees, redemption schedule, current series

# Market indices
idx = tasekit.Index("142")   # TA-35
df = idx.history(years=3)
info = idx.info()
```

**Return types:**

| Method | Columns |
|--------|---------|
| `Security.history()` — stocks, ETFs, bonds | `Open`, `High`, `Low`, `Close`, `Adj Close`, `Volume` |
| `Security.etf_history()` | Above + `Market Cap`, and when available: `Purchase Price`, `Redemption Price`, `NAV`, `Management Fee`, `Trustee Fee` |
| `Security.history()` — mutual funds | `Close` (redemption price) |
| `HedgeFund.list()` | `Name`, `Manager`, `Trustee`, `Management Fee`, `Success Fee`, `Trustee Fee`, `AUM`, `Tax Status`, `Classification` (indexed by `Fund ID`) |
| `HedgeFund.history()` | `Gross` (שער ברוטו), `Net` (שער נטו), `Adj Close` (continuous net-of-fees) |
| `HedgeFund.performance()` | `Performance` (net-of-fees total return; `net=False` for gross) |
| `Index.history()` | `Open` (base rate), `Close` (closing rate), `Market Cap` |

### CLI

```bash
# Security history (table, CSV, or JSON output)
tasekit history 00604611
tasekit history 00604611 --days 30
tasekit history 00604611 --start 2024-01-01 --end 2024-12-31
tasekit history 00604611 -o leumi.csv
tasekit history 00604611 -f json

# ETF-specific history (extra columns)
tasekit history 01144724 --etf
tasekit history 01144724 --etf --days 30 -o etf.csv

# List every mutual hedge fund traded on TASE
tasekit list --hedge
tasekit list --hedge -o hedge_funds.csv

# Mutual hedge fund (net-of-fees Adj Close on the oldest series)
tasekit history 1194141 --hedge
tasekit history 1194141 --hedge --gross           # gross series
tasekit history 1194141 --hedge --series 1233857  # a specific monthly series
tasekit info 1194141 --hedge

# Index history (auto-detected by short ID ≤ 3 digits)
tasekit history 142 --years 3

# Security metadata
tasekit info 00604611
tasekit info 5122627 -f json
tasekit info 01193580        # bond — shows redemption date, interest, linkage
tasekit info 01159235        # ETF — shows NAV, underlying asset, foreign market
tasekit info 142             # index
```

## Finding IDs

- **Security IDs** are 6–8 digit numeric identifiers.
  Find them on [market.tase.co.il](https://market.tase.co.il) — the ID appears
  in the URL when viewing a security's page.
  Both zero-padded (`00604611`) and unpadded (`604611`) forms are accepted.
- **Mutual fund IDs** are 7-digit numbers (e.g. `5122627`).
  The library automatically detects mutual funds and uses the Maya API.
- **Mutual hedge fund IDs** are 7-digit numbers (e.g. `1194141`). Hedge funds
  are not exchange-traded and are indistinguishable from ordinary funds via the
  main API, so access them explicitly with `tasekit.HedgeFund(...)` or the
  `--hedge` CLI flag.
- **Index IDs**: `142` = TA-35, `137` = TA-125, `143` = TA-90, `140` = TA-SME60.
  IDs with 1–3 digits are automatically treated as index IDs by the CLI.

## License

MIT
