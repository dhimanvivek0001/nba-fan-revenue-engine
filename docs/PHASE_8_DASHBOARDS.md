# Phase 8 — Power BI Dashboards: Build Guide

## Why CSV extracts instead of a live DuckDB connection

Power BI Desktop has no native DuckDB connector. The reliable path: export
clean, pre-joined extracts from the star schema and Phase 7 model outputs as
CSVs, then import via Power BI's Folder connector. This is a common,
legitimate pattern for BI tools connecting to warehouses without a native
driver — the same extracts could later be swapped for a live ODBC connection
without changing the dashboard logic.

## Setup — do this once

1. Open **Power BI Desktop**
2. **Get Data** → **Folder** → browse to `C:\projects\nba-fan-revenue-engine\dashboards\`
3. Select all 6 CSVs → **Transform Data** (opens Power Query)
4. In Power Query, for each table: confirm the first row is used as headers, and set correct data types (dates as Date, currency fields as Decimal Number, percentages as Decimal Number)
5. **Close & Apply**
6. Create 4 pages (tabs at the bottom): rename them `CEO`, `Ticket Sales`, `Pricing`, `Sponsorship`

---

## Dashboard 1: CEO (FR-10)

**Data:** `ceo_game_trend.csv`, `ceo_nps_summary.csv`

**KPI cards (top row, 4 cards):**
| Card | Measure |
|---|---|
| Total Season Revenue | `SUM(ceo_game_trend[total_revenue])` |
| Total Attendance | `SUM(ceo_game_trend[final_attendance])` |
| At-Risk Revenue | Manually add a card with value **$1,830,000** (from `models/churn/churn_model_metrics.json`) — or better, add a measure referencing that file's value as a constant, since it doesn't live in these CSVs |
| Avg NPS Score | `ceo_nps_summary[avg_nps_score]` |

**Main visual:** Line chart — X axis `game_date`, Y axis `cumulative_revenue` (shows season revenue trending up game by game)

**Secondary visual:** Column chart — X axis `day_of_week`, Y axis `AVERAGE(final_attendance)` (attendance by day of week — ties back to the Phase 6 finding)

**Bottom visual:** Table — `opponent`, `game_date`, `total_revenue`, sorted descending (top revenue games)

---

## Dashboard 2: Ticket Sales (FR-11)

**Data:** `ticket_sales_outreach_priority.csv`

**KPI cards:**
| Card | Measure |
|---|---|
| Accounts Flagged At-Risk | `COUNTROWS(FILTER(ticket_sales_outreach_priority, [churn_risk_score] >= 60))` |
| Total At-Risk Revenue | `CALCULATE(SUM([total_spend]), [churn_risk_score] >= 60)` (note: `total_spend` isn't in this extract — use `predicted_annual_spend` instead, which is) |

**Main visual:** Table, sorted by `outreach_priority_score` descending — columns: `full_name`, `membership_tier`, `section`, `churn_risk_score`, `clv`, `reason_codes`. This is the literal call list a Director of Ticket Sales rep would work from top to bottom.

**Secondary visual:** Scatter plot — X axis `churn_risk_score`, Y axis `clv`, to visually separate "high value + high risk" (top-right quadrant — call these first) from everything else.

**Slicer:** `membership_tier`, so a rep can filter to just their assigned tier.

---

## Dashboard 3: Pricing (FR-12)

**Data:** `pricing_recommendations.csv`, `pricing_backtest.csv`

**KPI cards:**
| Card | Measure |
|---|---|
| Revenue Left on the Table | **$657,935** (from `models/pricing/pricing_model_metrics.json` — add as a manual card or a DAX constant measure) |
| Games Recommended for Premium Pricing | `CALCULATE(COUNTROWS(pricing_backtest), [recommended_price_adjustment_pct] > 5)` |

**Main visual:** Bar chart — X axis `game_id` (or `opponent`), Y axis `recommended_price_adjustment_pct`, colored by sign (green for premium, red for discount)

**Secondary visual:** Line/column combo chart — `game_date` on X, `actual_avg_price` (line) vs `recommended_avg_price` (column) from `pricing_backtest.csv`, showing the gap visually per game

**Table:** `pricing_recommendations.csv` filtered/sliced by `section`, showing `base_price`, `recommended_price_adjustment_pct`, `recommended_price` per game

---

## Dashboard 4: Sponsorship (FR-13)

**Data:** `sponsorship_audience_scores.csv`, `sponsorship_season_summary.csv`

**KPI cards:**
| Card | Measure |
|---|---|
| Total Unique Fans | `sponsorship_season_summary[total_unique_fans]` |
| Season Ticket Accounts | `sponsorship_season_summary[sth_accounts]` |
| Total Season Attendance | `sponsorship_season_summary[total_season_attendance]` |
| Last Refreshed | `sponsorship_season_summary[last_refreshed]` — this is the FR-13 requirement that numbers show a live timestamp instead of being a stale PDF |

**Main visual:** Clustered bar chart — `fan_segment` on Y axis, three measures side by side: `premium_luxury_fit`, `mass_market_beverage_fit`, `digital_fintech_fit`

**Table:** the full `sponsorship_audience_scores.csv`, sorted by `fan_count` descending — this is the literal table to screenshot into a sponsorship one-pager

---

## Refreshing the dashboards after any pipeline re-run

Whenever the underlying models or data are re-run (e.g. after regenerating
synthetic data or retraining a model), re-run the extract script and refresh
in Power BI:

```powershell
cd C:\projects\nba-fan-revenue-engine
venv\Scripts\activate
python dashboards\build_dashboard_extracts.py
```
Then in Power BI Desktop: **Home** → **Refresh**.

## Next: Phase 9 — Real-Time Matchday Layer

Kafka + Streamlit — near-real-time concession/gate-scan event streaming and a
live matchday operations dashboard, supplementing this batch-refreshed
Power BI layer on gamedays.
