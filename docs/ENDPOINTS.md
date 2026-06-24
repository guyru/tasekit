# tasekit — TASE API Endpoint Catalog

Discovered by extracting routes from the `market.tase.co.il` Angular bundle
and verified by live probing (last updated 2026-04-07).

**Base URL:** `https://api.tase.co.il/api/`

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Accessible with plain `requests` (no browser cookies needed) |
| 🚫 | WAF-blocked — returns 403. Requires Incapsula JS challenge cookies. |

### Required Headers (all api.tase.co.il endpoints)

```
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) ...
Origin: https://market.tase.co.il
Referer: https://market.tase.co.il/
Accept-Language: en-US          ← controls CSV export language
Content-Type: application/json;charset=UTF-8   ← POST only
```

Without `Origin`/`Referer`, even accessible endpoints return 403.

---

## 1. CSV Export Endpoints (POST)

Standard payload format:

```json
{
  "FilterData": {
    "pType": "4",        // time range (0=1d, 1=1mo, 2=3mo, 3=6mo, 4=1y, 5=2y, 6=3y, 7=5y)
    "TotalRec": 1,
    "pageNum": 1,
    "oId": "00604611",   // security or index ID
    "lang": "0"          // no effect on CSV — use Accept-Language header instead
  },
  "isAdd": false,
  "callerName": "..."
}
```

**CSV Language:** The `Accept-Language` header controls CSV output language —
`en-US` gives English headers/values; `he-IL` gives Hebrew. The `lang`
parameter has no effect on CSV exports.

### 1.1 Accessible ✅

| Endpoint | Description | oId type |
|----------|-------------|----------|
| `export/securityhistoryeod` | Historical EOD OHLC for a security (stock, bond, ETF). 18+ columns including Date, Adj Close, Close, Open, High, Low, Volume. | Security ID |
| `export/etfhistoryeod` | Historical EOD for an ETF. Same base columns plus: Purchase Price, Redemption Price, Unit Price (NAV), Management Fee, Trustee Fee, Market Cap, Turnover. | Security ID |
| `export/securityhistoryindaydata` | Intraday tick data for current trading day. Columns: Time, Last Price, Change%, Volume, Cumulative Turnover, Trade Type. | Security ID |
| `export/indexhistoryeod` | Historical EOD for an index. Columns: Date, Base Rate, Close Rate, Total Market Cap. | Index ID |
| `export/indexmarketdata` | Current snapshot of all securities in an index. Columns: Name, Symbol, ID, Last Price, Change%, Volume, Open, High, Low, YTD return. | Index ID |
| `export/securityInIndicesDataGet` | Indices containing a security, with weight and weight factor. | Security ID |
| `export/getindiceslobby` | All indices overview — name, category, code, last rate, change%. | (ignored) |
| `export/listedcapital` | All listed securities — name, symbol, ID, free float, listed capital. Full market. | (ignored) |
| `export/otctransactions` | OTC (off-exchange) transactions — Name, Symbol, ID, ISIN, Type, Date, Price, Value, Quantity. | (ignored) |
| `export/putvscallevents` | Derivatives trading calendar — settlement days, exercise/expiration dates. | (ignored) |
| `export/indicescomponentsequityupdate` | Equity index composition changes — additions/removals, weight factors, dates. | (ignored) |
| `export/indicescomponentstelbondsupdate` | Bond index composition changes. | (ignored) |
| `export/indicesupdatesschedule` | Upcoming index rebalance dates by category. | (ignored) |
| `export/listofsharesforindices` | Securities eligible for indices. | (ignored) |
| `export/weightfactor` | Upcoming weight factor changes. | (ignored) |
| `export/analysisreports` | Analyst reports — publication date, covered company, target price, recommendation. | (ignored) |

### 1.2 WAF-Blocked 🚫

| Endpoint | Description |
|----------|-------------|
| `export/securityyieldsrates` | Bond yields and rates for a security |
| `export/securityadditionalqueries` | Additional security data queries |
| `export/dailyreviewmain` | Daily market review — main summary |
| `export/dailyreviewmostactive` | Daily review — most active securities |
| `export/dailyreviewderivativesmarket` | Daily review — derivatives market |
| `export/dailyreviewforeignexchangeexport` | Daily review — foreign exchange |
| `export/bondsturnoverandmarketcap` | Bond turnover and market cap summary |
| `export/sharesturnoverandmarketcap` | Share turnover and market cap summary |
| `export/summarybysectors` | Market summary by sector |
| `export/summarybytypes` | Market summary by security type |
| `export/membersranking` | Exchange member (broker) rankings |
| `export/monthlyreviewsecurities` | Monthly review — securities |
| `export/monthlyreviewderivatives` | Monthly review — derivatives |
| `export/monthlyreviewdeleted` | Monthly review — delisted securities |
| `export/indexcomponents` | Index components CSV (use JSON `index/components` POST instead ✅) |
| `export/indexcomponentsmostactivedata` | Index components — most active |
| `export/indicesuniversecomponentsupdate` | Index universe components update |
| `export/expectedchangesians` | Expected IANS changes |
| `export/rights` | Rights offerings |
| `exportchart/chartdata` | Chart data export |
| `exportchart/putvscalldata` | Put vs Call chart data |
| `download/corpactions` | Corporate actions — dividends, splits, etc. **High value.** |

---

## 2. JSON Endpoints — GET

Parameters are query string. All return `application/json`.

### 2.1 Accessible ✅

| Endpoint | Description | Parameters |
|----------|-------------|------------|
| `company/securitydata` | **Rich security metadata**: ISIN, symbol, sector, type, yields, market value, bond fields (redemption date, interest, linkage, days to maturity), ETF fields (NAV, creation/sell price, fund update date, underlying asset). Returns JSON `null` for mutual funds (definitive fund detection). | `securityId`, `lang` |
| `company/securitieslist` | **All securities for a company** — every stock, bond, and ETF issued by a given company. Fields: `Id`, `Name`, `ShareType`, `TypeInSite`, `SecuritySubType`. | `companyId`, `lang` |
| `company/fetfslist` | **ETFs managed by a fund company** — empty array for non-fund companies. | `companyId`, `lang` |
| `company/tradedata` | Basic trading data by company ID. Same structure as `securitydata` but most metadata fields are null. Less useful than `securitydata`. | `companyId`, `lang` |
| `security/majordata` | **Rich security overview**: last 5 days' data, last 5 trades, index memberships+weights, short sale data, trading statistics (avg turnover, std dev). Pass the real `compId` (from `company/securitydata`) to unlock `CompanyDetails` (description, website). | `secId`, `compId`, `lang` |
| `security/securitiesclassifications` | **Security type taxonomy** — 7 categories (Shares, Bonds, ETFs, etc.) with `ShareType` sub-codes and names. | `lang` |
| `index/majordata` | Rich index overview: most active components, last 5 days' data, sector weights, short sale summary. | `indexId`, `lang` |
| `index/details` | Index metadata: name, base/open/high/low rates, month+annual yield, market value, trading status. | `indexId`, `lang` |
| `index/getindiceslistfornavigatorcombo` | All indices organised by category (~140 indices). Each entry: IndexId, Name, IndexType. | `lang` |
| `index/getindayindices` | All indices real-time snapshot — current rates, changes, gainers/decliners. | `lang` |
| `marketdata/mostactive` | Most active securities — top movers by various criteria. | `lang` |
| `marketdata/overallturnovers` | Aggregate turnover figures. | `lang` |
| `content/siteconfig` | UI configuration and feature flags. | — |
| `content/siteparameters` | Key index IDs and feature toggles. | — |
| `content/translations` | All UI label translations (Hebrew↔English). ~218 KB. | — |
| `commissions/loadcommissions` | Trading commission rates. | — |
| `derivatives/defaulttradedate` | Default trade date for derivatives. | — |
| `company/delistedsecurities` | Delisted securities for a company. | `companyId` |

### 2.2 WAF-Blocked 🚫

| Endpoint | Description | Priority |
|----------|-------------|----------|
| `search/market` | Security/company search by name → ID resolution | **High** |
| `company/alldetails` | Full company details (name, sector, description, logo, website) | Low (covered by `majordata` CompanyDetails) |
| `company/financereports` | Company financial reports | Medium |
| `company/manager/reports` | Manager reports for ETFs | Low |
| `security/reports` | Reports/filings for a security | Medium |
| `index/lastdaysdata` | Index last days data | Low |
| `index/mostactive` | Index most active components | Low |
| `index/branchesweights` | Index sector/branch weights | Low |
| `index/yieldsandrates` | Index yields and rates | Medium |
| `index/componentsdeftradedate` | Components default trade date | Low |
| `index/componentsmostactive` | Index most active components (POST) | Low |
| `index/otctransactions` | Index OTC transactions (POST) | Low |
| `marketdata/lastexchange` | Last exchange/FX rates | Medium |
| `marketdata/dailyreviewmain` | Daily market review main | Low |
| `marketdata/dailyreviewmostactive` | Daily review most active | Low |
| `corporateaction/filter` | Corporate actions filter/search | **High** |
| `report/filter` | Report search | Medium |
| `report/lastbreakingannouncement` | Latest breaking announcement | Low |
| `derivatives/derivativesnavdata` | Derivatives navigation data | Low |

---

## 3. JSON Endpoints — POST

Accept JSON body with `FilterData`.

### 3.1 Accessible ✅

| Endpoint | Description |
|----------|-------------|
| `index/components` | Index components list |
| `index/historyeod` | Index EOD history (JSON format) |
| `index/historyhighlow` | Index high/low history |
| `index/historyinday` | Index intraday history |
| `index/etn` | ETN data for index |
| `index/expectedchangesians` | Expected IANS changes |
| `index/expectedchangessecurities` | Expected securities changes |
| `index/listedcapital` | Index listed capital |
| `derivatives/all` | All derivatives data |
| `derivatives/newopened` | Newly opened derivatives |
| `derivatives/spotdata` | Spot data for derivatives |
| `marketdata/dailyreviewforeignexchange` | FX daily review (POST only; GET is WAF-blocked) |
| `marketdata/statistics` | Market statistics |

---

## 4. Maya API (`maya.tase.co.il`)

**Base URL:** `https://maya.tase.co.il/api/v1/`

No WAF — all tested endpoints accessible. Different `Origin`/`Referer` headers required.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `funds/mutual/{fundId}` | GET | Full mutual fund details — name, type, ISIN, manager, fees, yields, classification, exposure profile, underlying assets. |
| `funds/mutual/{fundId}/history/file` | POST | Mutual fund NAV history CSV. Body: `{pageSize, pageNumber, period, fromDate, toDate}`. Supports arbitrary date ranges. |
| `funds/hedge` | POST | Full mutual **hedge** fund **listing** (backs the `/he/funds/hedge-funds` page). Body `{pageSize, pageNumber}` → list of fund summaries (`fundId`, `name`, `managerName`, `trusteeName`, fees, `assetValue`, `taxStatusName`, `classification`). No total-count envelope; `pageSize` must be 1–30; paginate until a short/empty page. |
| `funds/metadata/hedge` | GET | Hedge-fund **listing filters**: `fundsManagers`, `fundsTrustees`, `fundTypes` (key/value option lists). |
| `funds/hedge/{fundId}` | GET | Mutual **hedge** fund details — fees (`successFee`, `managementFee`), redemption schedule, and `securityRedemptions[]` (currently redeemable monthly series with `nav`/`gav`). |
| `funds/metadata/{fundId}/history-hedge-fund` | GET | Hedge-fund history-page metadata: default `fromDate`/`toDate` and `securities: [{key=securityId, value="name MM/YY"}]` — every monthly series. Lowest `key` = oldest anchor series. |
| `funds/hedge/{fundId}/history` | POST | Hedge-fund price history (JSON). Body `{pageSize, pageNumber}` → current redemption **snapshot** (all live series, latest date). Add `securityId`, `fromDate`, `toDate` → that series' monthly **time series** of `{tradeDate, purchasePrice (gross/GAV), sellPrice (net/NAV)}`. `pageSize` must be 1–30; paginate for longer histories. |
| `funds/hedge/{fundId}/history/file` | POST | Hedge fund NAV history CSV (legacy/untested via this client). |
| `funds/etf/{fundId}/history/file` | POST | ETF fund history — untested with real ETF ID. |

#### Hedge-fund mechanics (see `docs/HEDGE_FUNDS_PLAN.md` §1)

A new `securityId` is minted each month. Within a calendar-year fee period the
net price (`sellPrice`) drifts below the gross (`purchasePrice`) as management +
success fees accrue. At year-end, fees crystallize: holdings convert into the
**oldest** series, net resets up to gross, and unit count scales by `net/gross`.
The oldest series therefore has a continuous full-life history and is the
performance anchor; its raw net series has an upward reset jump each January
that `add_hedge_fund_adj_close()` removes to build a true net-of-fees return.

---

## 5. Technical Notes

### 5.1 ID Formats

| Context | Format | Example |
|---------|--------|---------|
| CSV export `oId` | Zero-padded 8 digits | `"00604611"` |
| `company/securitydata` `securityId` | Unpadded | `"604611"` |
| `security/majordata` `secId` / `compId` | Unpadded | `"604611"` / `"604"` |
| Index endpoints | Short numeric | `"142"` |
| Maya fund endpoints | 7-digit | `"5122627"` |

### 5.2 Mutual Fund Detection

There is no reliable ID prefix to identify mutual funds. The TASE ID space
is shared between exchange-traded securities and mutual funds with overlapping
numeric ranges. The definitive programmatic check is `company/securitydata`
returning JSON `null`.

### 5.3 TableDef Parameter

Some CSV export endpoints accept an optional `TableDef` object to request
specific columns with custom headers:

```json
"TableDef": {
  "title": "IndicesMarketData",
  "columns": [
    {"title": "Name", "fieldName": "Name"},
    {"title": "Category", "fieldName": "CategoryName"}
  ]
}
```

Confirmed on `export/getindiceslobby`; may work on other export endpoints.

### 5.4 WAF Bypass Strategy

The Imperva/Incapsula WAF requires JavaScript challenge completion (`reese84`
and `___utmvc` cookies). TLS fingerprint impersonation (`curl_cffi`) does NOT
work — tested 2026-04-07.

Viable approach: **Playwright cookie extraction** — headless browser visits
`market.tase.co.il`, solves the JS challenge, extracts cookies, then passes
them to `requests`. Cookies remain valid for hours to days.
