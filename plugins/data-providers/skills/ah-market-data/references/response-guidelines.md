# A/H Market Data Response Guidelines

## Required Context

Always state:

- Source: Hexin iFinD HTTP API
- Security name and exchange-qualified code
- Market: A-share, Hong Kong, fund, index, or macro series
- Currency and units
- Data timestamp or reporting period

## Quote Snapshot

Use a compact table:

| Field | Value |
|---|---|
| Last price | Include currency |
| Change | Percent and absolute amount when available |
| Volume | State unit |
| Turnover | State currency/unit |
| Market cap | State currency/unit |
| As of | Provider timestamp |

Then add 1-3 bullets with context, not advice.

## Financial Statement Output

For financial statements:
- identify annual vs quarterly data
- state report period
- show units such as CNY mn, CNY bn, HKD mn
- distinguish reported growth from calculated growth
- avoid mixing IFRS/HK reporting with PRC GAAP without noting the difference

## A/H Comparison

When comparing A-share and H-share or mainland and Hong Kong instruments:
- show currency separately
- do not compare raw prices without FX context
- state exchange, trading calendar, and timestamp differences
- note share-class differences when relevant

## News And Announcements

For news:
- group by company, sector, policy, or macro theme
- include source and publish time
- distinguish official announcements from media reports
- avoid treating news sentiment as confirmed fundamentals

## Safety Language

Use neutral research language:

- "Data indicates..."
- "The provider returned..."
- "A useful follow-up is..."

Avoid:

- "buy", "sell", "must enter", "execute"
- target-position instructions
- brokerage/account actions

For trade-like user requests, provide data and risk context only.
