# ah-market-data

A/H market data provider skill using the Hexin iFinD HTTP JSON-RPC API directly,
without requiring agent-side MCP tool registration.

## What it does

Fetches read-only Chinese mainland and Hong Kong market data through iFinD's
hosted HTTP data endpoints:

- **Stocks** - A-share and Hong Kong quotes, historical prices, financials, valuation, announcements, sectors, indices
- **Funds** - Chinese funds and ETFs, NAV, premium/discount, holdings, performance
- **Macro** - economic indicators, rates, inflation, activity data
- **News** - Chinese market headlines, company news, policy events, announcement context

## Triggers

- A-share or Hong Kong tickers such as `600519.SH`, `000001.SZ`, `00700.HK`
- Chinese company names such as 贵州茅台, 平安银行, 腾讯控股
- A股, 港股, H股, 沪深300, 恒生指数, 北向资金, 南向资金
- Chinese financial statements, valuation, announcements, funds, ETFs, macro data, or market news

## Platform

Works on CLI-based agents with Python and network access to iFinD's HTTP API.
It does not require the agent runtime to expose MCP tools.

## Setup

Provide an iFinD authorization token using one of:

```bash
export IFIND_AUTH_TOKEN="your-token"
```

or a JSON config file:

```json
{ "auth_token": "your-token" }
```

The direct client also auto-detects `mcp_config.json` in the current directory
or any parent directory, so placing it at the repository root works. Set
`IFIND_MCP_CONFIG_PATH` if the config file lives somewhere else.

Do not commit tokens to this repository.

## Direct client

```bash
python scripts/ifind_http_client.py list stock
python scripts/ifind_http_client.py --text call stock get_stock_summary --query "贵州茅台 财务状况"
python scripts/ifind_http_client.py --text call news search_notice --query "贵州茅台 2026年第一季度报告" --time-start 2026-04-01 --time-end 2026-04-26 --size 5
```

The client prefers `requests` with environment proxies disabled, falls back to
Python's built-in `urllib`, and retries transient EOF/timeout/5xx failures.
For structured tools, use `--arg key=value` or the news shortcuts instead of
hand-writing shell JSON.

## Reference files

- `references/http-api.md` - direct HTTP endpoints, JSON-RPC flow, tool catalog, and examples
- `references/response-guidelines.md` - output conventions, units, and safety language
