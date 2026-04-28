---
name: ah-market-data
description: >
  Fetch A-share and Hong Kong stock, fund, macroeconomic, and market news data
  through the Hexin iFinD HTTP JSON-RPC API, without relying on agent-side MCP
  tool registration. Use this skill whenever the user asks about A/H stocks,
  Chinese mainland equities, Hong Kong equities, A-share tickers such as
  600519.SH or 000001.SZ, Hong Kong tickers such as 00700.HK, Chinese funds or
  ETFs, CSI/HSI indices, sector or concept market data, Chinese macro
  indicators, company announcements, financial statements, valuation metrics,
  price/volume history, northbound or southbound related market research, or
  Chinese financial news. This skill is read-only and must never place trades,
  submit orders, or modify brokerage/account state.
---

# A/H Market Data

Use Hexin iFinD's hosted HTTP JSON-RPC data endpoints as the preferred provider
for A-share and Hong Kong market research. This skill bypasses the agent's MCP
tool layer and calls the iFinD endpoints directly through `scripts/ifind_http_client.py`.

The remote iFinD service still uses MCP-over-HTTP JSON-RPC internally
(`initialize`, `tools/list`, `tools/call`). Treat it as a direct API client flow:
resolve an authorization token, initialize a session, then call the needed tool.

## Step 1: Detect Direct API Credentials

Resolve the iFinD authorization token without printing it. The direct client checks in order:

1. `mcp_config.json` in the skill directory (same directory as this SKILL.md)
2. `IFIND_AUTH_TOKEN`
3. `IFIND_API_TOKEN`
4. `IFIND_MCP_CONFIG_PATH` pointing to JSON with `auth_token`
5. `mcp_config.json` in the current working directory or any parent directory, including the repository root

```
!`python -c "import os,pathlib; skill_dir=pathlib.Path(__file__).parent if '__file__' in dir() else pathlib.Path.cwd(); env_paths=[pathlib.Path(os.environ['IFIND_MCP_CONFIG_PATH'])] if os.environ.get('IFIND_MCP_CONFIG_PATH') else []; cwd=pathlib.Path.cwd(); paths=[skill_dir/'mcp_config.json']+env_paths+[cwd/'mcp_config.json', *[p/'mcp_config.json' for p in cwd.parents]]; found=next((str(p) for p in paths if p.exists()), ''); print('IFIND_AUTH_TOKEN_SET' if (os.environ.get('IFIND_AUTH_TOKEN') or os.environ.get('IFIND_API_TOKEN')) else ('IFIND_CONFIG_FOUND:'+found if found else 'IFIND_AUTH_MISSING'))" 2>/dev/null || echo "PYTHON_UNAVAILABLE"`
```

Decision tree:

1. If a token or config file is found, proceed with direct HTTP calls.
2. If Python is unavailable, use the JSON-RPC request shapes in `references/http-api.md`
   with any available HTTP client.
3. If credentials are missing, ask the user to set `IFIND_AUTH_TOKEN` or provide an
   `mcp_config.json` path. Do not ask them to configure agent MCP servers.

Read `references/http-api.md` before making calls; it contains endpoint URLs,
the JSON-RPC session flow, and the tool catalog discovered from `tools/list`.

## Step 2: Identify Security And Market

Normalize the user's input before calling tools.

| User input                        | Interpret as    | Notes                                                       |
| --------------------------------- | --------------- | ----------------------------------------------------------- |
| `600519`, `600519.SH`, `贵州茅台` | A-share stock   | Prefer exchange-qualified code in output                    |
| `000001`, `000001.SZ`, `平安银行` | A-share stock   | Disambiguate stock vs index/fund when needed                |
| `00700`, `0700.HK`, `腾讯控股`    | Hong Kong stock | Normalize to `.HK` style when possible                      |
| `沪深300`, `CSI 300`, `000300.SH` | China index     | Use stock/index-capable queries                             |
| `恒生指数`, `HSI`                 | Hong Kong index | Use stock/index-capable queries                             |
| Fund code / ETF code              | Fund or ETF     | Route to fund server first                                  |
| Macro indicator                   | Economic data   | Route to EDB server                                         |
| News / policy / announcement      | News data       | Route to news server, then stock server if company-specific |

Ask a concise clarification only when the same code/name maps to multiple plausible
instruments and the requested metric depends on the distinction.

## Step 3: Route The Request

Match the user request to the lightest direct API call that answers it.

| Request type                    | Server/tool                                                | Typical fields to request                                     |
| ------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------- |
| Current quote / quote snapshot  | `stock/get_stock_summary` or `stock/get_stock_performance` | last price, change %, volume, turnover, market cap, timestamp |
| Historical K-line / price trend | `stock/get_stock_performance`                              | open, high, low, close, volume, turnover, adjustment mode     |
| Company profile / listing info  | `stock/get_stock_info`                                     | code, name, exchange, industry, listing date, main business   |
| Financial statements            | `stock/get_stock_financials`                               | income statement, balance sheet, cash flow, reporting period  |
| Valuation and factors           | `stock/get_stock_financials`                               | PE, PB, PS, dividend yield, ROE, margins, growth              |
| Shareholders / float            | `stock/get_stock_shareholders`                             | float, top holders, institution holdings, shareholder count   |
| Events / corporate actions      | `stock/get_stock_events`                                   | event title, date, category, key values                       |
| Announcements / filings         | `news/search_notice`                                       | announcement title, date, category, relevant snippets         |
| Sector / concept / peers        | `stock/search_stocks` or `stock/get_stock_info`            | industry, concept boards, constituent or peer list            |
| Fund or ETF data                | fund tools                                                 | NAV, premium/discount, holdings, performance, manager, fees   |
| Macro data                      | `edb/search_edb`, then `edb/get_edb_data`                  | indicator value, frequency, region, release date, history     |
| Market news                     | `news/search_news` or `news/search_trending_news`          | headline/snippet, source, publish time, topic/entity          |

For broad questions like "分析一下贵州茅台":

1. Fetch company/profile and quote or recent price context.
2. Fetch valuation and key financial metrics.
3. Fetch latest announcements/news.
4. Add sector/peer context when available.

For cross-market comparisons:

1. Normalize each listed security.
2. Fetch the same metric set for each instrument.
3. State currency, exchange, timestamp, and provider limitations.

## Step 4: Execute Through The Direct HTTP Client

Use the bundled client from the skill directory:

```bash
python scripts/ifind_http_client.py list stock
python scripts/ifind_http_client.py --text call stock get_stock_summary --query "贵州茅台 财务状况"
python scripts/ifind_http_client.py --text call stock get_stock_financials --query "贵州茅台 2025-12-31 ROE 净利润率"
python scripts/ifind_http_client.py --text call news search_notice --query "贵州茅台 2025年度报告 经营情况" --time-start 2026-01-01 --time-end 2026-04-26 --size 5
```

When calling tools:

- use structured arguments where the tool exposes them (`search_notice`, `search_news`,
  `search_trending_news`). Prefer CLI shortcuts such as `--time-start`, `--time-end`,
  `--size`, `--keyword`, and repeated `--arg key=value` over hand-written shell JSON.
- otherwise use a clear `query` string with entity, metric, and date/range
- include exchange-qualified tickers when known
- request only the fields and date range needed
- keep calls read-only
- do not store credentials in files or responses
- preserve source timestamps and reporting periods
- the client prefers `requests` with environment proxies disabled, falls back to
  `urllib`, and retries transient EOF/timeout/5xx errors; set `IFIND_MAX_RETRIES`
  or pass `--max-retries` to tune retry count

If a call fails, report whether the failure was missing credentials, network/API
connectivity, a JSON-RPC error, or no provider data returned.

## Step 5: Normalize Output

Use these normalized field concepts when passing data into other analysis:

| Concept               | Normalized name |
| --------------------- | --------------- |
| Security code         | `symbol`        |
| Exchange              | `exchange`      |
| Security name         | `name`          |
| Last price            | `last_price`    |
| Change percent        | `change_pct`    |
| Volume                | `volume`        |
| Turnover amount       | `turnover`      |
| Market capitalization | `market_cap`    |
| Report period         | `report_period` |
| Data timestamp        | `as_of`         |
| Currency              | `currency`      |
| Data source           | `source`        |

For A/H data, always make units explicit:

- CNY vs HKD vs USD
- shares vs lots vs contracts
- percent vs decimal
- reporting period vs trading date
- adjusted vs unadjusted prices

Read `references/response-guidelines.md` for answer patterns, fallback wording,
and downstream-analysis handoff.

## Step 6: Respond To The User

Lead with the answer, then show the data table or evidence behind it.

Always include:

- the data source: Hexin iFinD HTTP API
- the market/exchange
- the data timestamp or reporting period
- any missing fields or provider limitations

Never present the result as investment advice. Do not place trades, recommend order
execution, or imply brokerage action.

## Reference Files

- `references/http-api.md` - direct HTTP endpoints, JSON-RPC flow, tool catalog, and examples
- `references/response-guidelines.md` - A/H market output conventions and safety language
