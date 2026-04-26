# ah-market-data

A/H market data provider skill using Hexin iFinD MCP servers.

## What it does

Fetches read-only Chinese mainland and Hong Kong market data through configured MCP servers:

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

Works on agents that support MCP tools and have the Hexin iFinD MCP servers configured.

## Setup

Configure these MCP servers in the agent runtime:

- `hexin-ifind-ds-stock-mcp`
- `hexin-ifind-ds-fund-mcp`
- `hexin-ifind-ds-edb-mcp`
- `hexin-ifind-ds-news-mcp`

Keep authorization headers in the agent MCP configuration or secret store. Do not commit tokens to this repository.

## Reference files

- `references/mcp-routing.md` - server routing and task mapping
- `references/response-guidelines.md` - output conventions, units, and safety language
