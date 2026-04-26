# A/H Market Data MCP Routing

Use this reference when deciding which Hexin iFinD MCP server should answer a Chinese mainland or Hong Kong market-data request.

## Server Map

| MCP server | Use for |
|---|---|
| `hexin-ifind-ds-stock-mcp` | Stocks, indices, sectors, concept boards, quotes, K-lines, financials, valuation, announcements |
| `hexin-ifind-ds-fund-mcp` | Mutual funds, ETFs, NAV, holdings, performance, managers, fees |
| `hexin-ifind-ds-edb-mcp` | Macro indicators, economic database series, rates, inflation, industrial activity |
| `hexin-ifind-ds-news-mcp` | Market news, company news, policy headlines, event narratives |

## Routing Patterns

| User asks for | Route |
|---|---|
| "贵州茅台今天怎么样" | stock quote + recent price history |
| "600519.SH 财报" | stock financial statements |
| "腾讯控股估值" | stock valuation and fundamentals |
| "沪深300 最近一年走势" | stock/index historical K-line |
| "某 ETF 折溢价" | fund NAV + market price |
| "基金持仓" | fund holdings |
| "中国 CPI / 社融 / M2" | EDB macro series |
| "今天 A 股新闻" | news headlines, optionally grouped by sector |
| "这家公司有什么公告" | stock announcements first, news second |

## Tool Selection Rules

1. Discover the actual MCP tool names exposed in the current runtime.
2. Prefer schema-based tools over prompt-like tools.
3. For ambiguous names, run search/lookup first, then fetch data by canonical symbol.
4. Use exchange-qualified symbols in downstream calls when available.
5. Keep calls narrow: do not fetch full histories when a quote snapshot answers the question.
6. Preserve provider timestamps and reporting periods.

## Fallback Rules

If an MCP tool is missing:
- try the adjacent iFinD MCP server only if the data type overlaps
- otherwise tell the user exactly which server capability is unavailable

If authentication fails:
- do not print headers or tokens
- ask the user to refresh the MCP authorization in their agent configuration

If the provider returns no data:
- confirm the symbol/exchange
- try a name/code lookup
- report "no provider data returned" rather than inferring a financial conclusion

## Downstream Skill Handoff

When another analysis skill needs A/H data, provide a compact normalized payload:

```text
source: Hexin iFinD MCP
symbol:
exchange:
name:
as_of:
currency:
fields:
missing_fields:
notes:
```

This lets analytical skills avoid depending on raw provider field names.
