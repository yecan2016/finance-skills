# iFinD HTTP API Reference

This reference describes the direct HTTP interface discovered from the local iFinD configuration.
It bypasses agent-side MCP registration and calls iFinD's hosted JSON-RPC endpoints directly.
The hosted service still speaks MCP-over-HTTP, so the client must initialize a session before
calling tools.

## Configuration Summary

Base URL:

```text
https://api-mcp.51ifind.com:8643/ds-mcp-servers
```

Headers:

```text
Content-Type: application/json
Accept: application/json, text/event-stream
Authorization: <iFinD token>
Mcp-Session-Id: <session id returned by initialize, after initialization>
```

Resolve the authorization token in this order:

1. `IFIND_AUTH_TOKEN` environment variable.
2. `IFIND_API_TOKEN` environment variable.
3. `IFIND_MCP_CONFIG_PATH` JSON file containing `{"auth_token": "..."}`.
4. `mcp_config.json` in the current working directory or any parent directory, including the repository root.

Never print, persist, or commit the token.

## Endpoint Map

| Server type | URL suffix | Use for |
|---|---|---|
| `stock` | `/hexin-ifind-ds-stock-mcp` | A-share stocks, indices, sectors, quotes, K-lines, financials, valuation, shareholders, events, ESG |
| `fund` | `/hexin-ifind-ds-fund-mcp` | Chinese funds and ETFs, NAV/performance, holdings, holders, fund companies |
| `edb` | `/hexin-ifind-ds-edb-mcp` | Macro, industry economics, rates, activity, commodity time series |
| `news` | `/hexin-ifind-ds-news-mcp` | Market news, listed-company announcements, hot events |

## JSON-RPC Flow

1. Initialize the server session:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-03-26",
    "capabilities": {},
    "clientInfo": { "name": "ifind-http-client", "version": "1.0.0" }
  }
}
```

2. Capture the `Mcp-Session-Id` response header.
3. Send the initialized notification with that session header:

```json
{ "jsonrpc": "2.0", "method": "notifications/initialized" }
```

4. List tools or call tools with the same session header:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_stock_financials",
    "arguments": { "query": "贵州茅台 2025-12-31 ROE 净利润率" }
  }
}
```

## Direct Client

From the skill directory:

```bash
python scripts/ifind_http_client.py list stock
python scripts/ifind_http_client.py --text call stock get_stock_summary --query "贵州茅台 财务状况"
python scripts/ifind_http_client.py --text call news search_notice --query "贵州茅台 2025年度报告 经营情况" --time-start 2026-01-01 --time-end 2026-04-26 --size 5
```

The client prefers `requests` when installed and disables environment proxy inheritance
(`Session.trust_env = False`) to avoid proxy timeouts on the iFinD endpoint. If
`requests` is unavailable, it falls back to Python's built-in `urllib`. It defaults
to the same TLS behavior as the local iFinD bridge; set `IFIND_VERIFY_TLS=1` or
pass `--verify-tls` when certificate verification works in the runtime.

Use `--text` for analysis workflows. iFinD often returns a JSON-RPC envelope whose
`result.content[].text` field contains a JSON string with `data.text` markdown inside it;
`--text` unwraps that common shape.

Transient connection failures such as TLS EOF, timeout, connection reset, and HTTP
5xx are retried with exponential backoff. Set `IFIND_MAX_RETRIES` or pass
`--max-retries` to tune retry count.

### Structured CLI Arguments

For tools with structured schemas, prefer shortcuts over hand-written JSON:

```bash
python scripts/ifind_http_client.py --text call news search_notice \
  --query "贵州茅台 2026年第一季度报告" \
  --time-start 2026-04-01 \
  --time-end 2026-04-26 \
  --size 5

python scripts/ifind_http_client.py --text call news search_trending_news \
  --keyword "白酒" \
  --time-scope "24小时" \
  --sensitive "全部" \
  --industry-name "食品饮料" \
  --size 5

python scripts/ifind_http_client.py --text call news search_notice \
  --query "贵州茅台 分红方案" \
  --arg time_start=2026-01-01 \
  --arg time_end=2026-04-26 \
  --arg size=5
```

## Tool Catalog

### Stock Tools (`server_type="stock"`)

| Tool | Purpose | Arguments |
|---|---|---|
| `get_stock_summary` | Quick A-share stock summary: company basics, latest financial summary, recent trend, valuation, industry and business profile. Not for precise metric/time filters. | `{"query": "证券实体 + 查询内容"}` |
| `search_stocks` | Natural-language A-share stock screening by indicators, industry, concept, business, or constraints. | `{"query": "选股条件"}` |
| `get_stock_performance` | Daily historical market data, derived technical indicators, price/volume metrics, margin trading, and other daily trading indicators. | `{"query": "证券实体 + 指标 + 日期/区间"}` |
| `get_stock_info` | Basic security and listed-company profile data: code/name, listing/issuance, index membership, registration, industry, main business. | `{"query": "证券实体 + 基础资料指标"}` |
| `get_stock_shareholders` | Share capital structure, float, restricted shares, top shareholders, institution holdings, shareholder counts and ratios. | `{"query": "证券实体 + 股本/股东指标 + 日期"}` |
| `get_stock_financials` | Financial statements, profitability, growth, leverage, solvency, risk, valuation metrics and percentiles. Report-period dates are expected. | `{"query": "证券实体 + 财务/估值指标 + 报告期"}` |
| `get_risk_indicators` | Quantitative price-series risk metrics such as alpha, beta, volatility, Sharpe ratio, VaR. | `{"query": "证券实体 + 时间范围 + 风险指标"}` |
| `get_stock_events` | Public listed-company events: IPO, refinancing, M&A, management changes, shareholder changes, incentives, warnings, inquiries, lawsuits. | `{"query": "证券实体 + 事件类型/指标"}` |
| `get_esg_data` | A-share listed-company ESG ratings and reports. | `{"query": "证券实体 + ESG指标"}` |

### Fund Tools (`server_type="fund"`)

| Tool | Purpose | Arguments |
|---|---|---|
| `search_funds` | Match fuzzy fund names or fund-selection requirements to similar funds. | `{"query": "基金名称或选基需求"}` |
| `get_fund_profile` | Fund basics: name, code, type, fees, issuer, launch date, issue shares. | `{"query": "基金实体 + 基本资料指标"}` |
| `get_fund_market_performance` | Fund quote, NAV/performance, premium/discount, ranking, flows, margin data, technical patterns, risk/performance metrics. | `{"query": "基金实体 + 指标 + 日期/区间"}` |
| `get_fund_ownership` | Fund shares, subscriptions/redemptions, holder counts and holder structure. Report-period dates are expected. | `{"query": "基金实体 + 份额/持有人指标 + 报告期"}` |
| `get_fund_portfolio` | Asset allocation, industry distribution, top holdings, and portfolio details. Report-period dates are expected. | `{"query": "基金实体 + 投资组合指标 + 报告期"}` |
| `get_fund_financials` | Fund report-period financials, profit metrics, dividends and distribution plans. | `{"query": "基金实体 + 财务/分红指标 + 报告期"}` |
| `get_fund_company_info` | Fund-company information: profile, managers, AUM, fund count, portfolios, financials and performance metrics. | `{"query": "基金实体/基金公司 + 公司维度指标 + 日期"}` |

### EDB Tools (`server_type="edb"`)

| Tool | Purpose | Arguments |
|---|---|---|
| `search_edb` | Search macro or industry indicators when the exact indicator name is unclear. | `{"query": "行业/产品/地区/指标需求"}` |
| `get_edb_data` | Query macro, regional, industry, commodity, production, trade, price, inventory, or activity series. | `{"query": "指标名称 + 地区/频率/统计口径 + 时间范围"}` |

### News Tools (`server_type="news"`)

| Tool | Purpose | Arguments |
|---|---|---|
| `search_notice` | Semantic search over A-share, fund, Hong Kong, and US stock announcements. Returns relevant announcement snippets. | `{"query": "...", "time_start": "yyyy-MM-dd", "time_end": "yyyy-MM-dd", "size": 5}` |
| `search_news` | Search iFinD financial news snippets by company, industry, topic, and time range. | `{"query": "...", "time_start": "yyyy-MM-dd", "time_end": "yyyy-MM-dd", "size": 5}` |
| `search_trending_news` | Search hot event-driven news by recency, sentiment, industry, and keyword. | `{"size": 5, "time_scope": "6小时|24小时|近一周", "sensitive": "正面|负面|中性|全部", "industry_name": "行业名", "keyword": "关键词"}` |

`search_notice` and `search_news` require `query`, `time_start`, `time_end`, and `size`.
`search_trending_news` only requires `size`; all other filters are optional, and overly strict
filters can return no results.

## Query Construction Rules

- Prefer one clear entity plus a small set of indicators per request.
- For stock and fund metrics, include the report period (`YYYY-MM-DD`) or trading-date range.
- Keep broad screeners narrow enough for context limits.
- For macro/industry data, use `search_edb` first when the exact indicator name is unknown.
- For announcement/news requests, include the company or topic, document/news type, date range, and desired snippet count.
- Preserve the provider's timestamps, report periods, units, and raw field names when normalizing output.
