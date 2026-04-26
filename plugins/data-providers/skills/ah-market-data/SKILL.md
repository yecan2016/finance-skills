---
name: ah-market-data
description: >
  Fetch A-share and Hong Kong stock, fund, macroeconomic, and market news data
  through Hexin iFinD MCP servers. Use this skill whenever the user asks about
  A/H stocks, Chinese mainland equities, Hong Kong equities, A-share tickers
  such as 600519.SH or 000001.SZ, Hong Kong tickers such as 00700.HK,
  Chinese funds or ETFs, CSI/HSI indices, sector or concept market data,
  Chinese macro indicators, company announcements, financial statements,
  valuation metrics, price/volume history, northbound or southbound related
  market research, or Chinese financial news. This skill is read-only and must
  never place trades, submit orders, or modify brokerage/account state.
---

# A/H Market Data

Use the Hexin iFinD MCP data-source servers as the preferred provider for A-share and Hong Kong market research.

This skill is a provider layer: it fetches and normalizes Chinese/HK market data for downstream analysis skills such as SEPA, liquidity, earnings, estimate, ETF/fund, macro, and news workflows.

## Step 1: Check MCP Availability

Use the configured MCP servers instead of hardcoded API tokens or raw HTTP calls. Never print, persist, or commit authorization headers.

Expected server names:

| Server | Primary use |
|---|---|
| `hexin-ifind-ds-stock-mcp` | A/H stock quotes, OHLCV, fundamentals, announcements, valuation, sectors, indices |
| `hexin-ifind-ds-fund-mcp` | Funds, ETFs, holdings, NAV, performance, fund managers |
| `hexin-ifind-ds-edb-mcp` | Economic database, macro indicators, rates, inflation, activity data |
| `hexin-ifind-ds-news-mcp` | Chinese market news, company news, policy headlines, event context |

If these MCP servers or their tools are unavailable:
1. Tell the user the iFinD MCP connection is not available in the current runtime.
2. Ask them to configure the MCP servers in their agent settings.
3. If the task is urgent, continue only with user-provided data or another explicitly available data source.

Read `references/mcp-routing.md` when you need to choose the right MCP server/tool for a request.

## Step 2: Identify Security And Market

Normalize the user's input before calling tools.

| User input | Interpret as | Notes |
|---|---|---|
| `600519`, `600519.SH`, `贵州茅台` | A-share stock | Prefer exchange-qualified code in output |
| `000001`, `000001.SZ`, `平安银行` | A-share stock | Disambiguate stock vs index/fund when needed |
| `00700`, `0700.HK`, `腾讯控股` | Hong Kong stock | Normalize to `.HK` style when possible |
| `沪深300`, `CSI 300`, `000300.SH` | China index | Use index-capable stock/market tool |
| `恒生指数`, `HSI` | Hong Kong index | Use index-capable stock/market tool |
| Fund code / ETF code | Fund or ETF | Route to fund MCP first |
| Macro indicator | Economic data | Route to EDB MCP |
| News / policy / announcement | News data | Route to news MCP, then stock MCP if company-specific |

Ask a concise clarification only when the same code/name maps to multiple plausible instruments and the requested metric depends on the distinction.

## Step 3: Route The Request

Match the user request to the lightest data call that answers it.

| Request type | Preferred MCP | Typical fields to fetch |
|---|---|---|
| Current quote / quote snapshot | stock | last price, change %, volume, turnover, market cap, timestamp |
| Historical K-line / price trend | stock | open, high, low, close, volume, turnover, adjustment mode |
| Financial statements | stock | income statement, balance sheet, cash flow, reporting period |
| Valuation and factors | stock | PE, PB, PS, dividend yield, ROE, margins, growth |
| Announcements / filings | stock or news | announcement title, date, category, URL/content summary |
| Sector / concept / peers | stock | industry, concept boards, constituent list, peer metrics |
| Fund or ETF data | fund | NAV, premium/discount, holdings, performance, manager, fees |
| Macro data | edb | indicator value, frequency, region, release date, history |
| Market news | news | headline, source, publish time, tickers/entities, summary |

For broad questions like "分析一下贵州茅台":
1. Fetch quote and recent price history.
2. Fetch valuation and key financial metrics.
3. Fetch latest announcements/news.
4. Add sector/peer context when available.

For cross-market comparisons like "A股和港股的腾讯相关标的":
1. Normalize each listed security.
2. Fetch the same metric set for each instrument.
3. State currency, exchange, timestamp, and data-source differences.

## Step 4: Execute Through MCP Tools

Use the actual tool names exposed by the MCP server in the current runtime. Tool names may differ by client, so discover them from the MCP tool list/resource metadata instead of inventing function names.

When calling tools:
- prefer structured parameters over free-text prompts if the MCP server exposes schemas
- include exchange-qualified tickers when known
- request only the fields and date range needed
- keep calls read-only
- do not store credentials in files or responses
- preserve source timestamps and reporting periods

If a tool returns Chinese field names, keep the raw meaning but translate only what helps the user's requested output. Do not lose the original period, unit, currency, or exchange.

## Step 5: Normalize Output

Use these normalized field concepts when passing data into other analysis:

| Concept | Normalized name |
|---|---|
| Security code | `symbol` |
| Exchange | `exchange` |
| Security name | `name` |
| Last price | `last_price` |
| Change percent | `change_pct` |
| Volume | `volume` |
| Turnover amount | `turnover` |
| Market capitalization | `market_cap` |
| Report period | `report_period` |
| Data timestamp | `as_of` |
| Currency | `currency` |
| Data source | `source` |

For A/H data, always make units explicit:
- CNY vs HKD vs USD
- shares vs lots vs contracts
- percent vs decimal
- reporting period vs trading date
- adjusted vs unadjusted prices

Read `references/response-guidelines.md` for answer patterns, fallback wording, and downstream-analysis handoff.

## Step 6: Respond To The User

Lead with the answer, then show the data table or evidence behind it.

Always include:
- the data source: Hexin iFinD MCP
- the market/exchange
- the data timestamp or reporting period
- any missing fields or provider limitations

Never present the result as investment advice. Do not place trades, recommend order execution, or imply brokerage action.

## Reference Files

- `references/mcp-routing.md` - MCP server routing, common tasks, and fallback rules
- `references/response-guidelines.md` - A/H market output conventions and safety language
