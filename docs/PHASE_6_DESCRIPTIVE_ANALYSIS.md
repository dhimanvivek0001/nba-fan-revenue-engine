# Phase 6 — Descriptive Analysis

## What this phase builds

A 36-query SQL library against the Phase 5 star schema, organized into 5 files.
Every query runs clean against `data/warehouse/nba_fan_engine.duckdb` — this is
the analytical foundation the 5 ML models in Phase 7 build directly on top of.

| File | Focus | Queries |
|---|---|---|
| `01_fan_segmentation_rfm.sql` | RFM (Recency/Frequency/Monetary) fan segmentation | 8 |
| `02_attendance_trends.sql` | Attendance by day, opponent, month, channel | 8 |
| `03_revenue_analysis.sql` | Revenue by section, tier, tenure, price distribution | 6 |
| `04_concessions_analysis.sql` | Concession sales by stand, item, game, fan linkage | 7 |
| `05_engagement_analysis.sql` | Email engagement, NPS, cross-channel disengagement | 7 |

`01_fan_segmentation_rfm.sql` also creates `main_marts.fan_rfm_segments`, a
reusable view the other 4 files (and Phase 7) query against.

## Headline finding: RFM segmentation, on its own, can't do STH churn's job

Fans were scored into 6 segments (Champions, Loyal Fans, At Risk, Needs
Attention, New/Occasional, Lost/Churned) using standard RFM quartile scoring:

| Segment | Fans | Avg Spend | Avg Games Attended | % of Base |
|---|---|---|---|---|
| Champions | 9,829 | $4,993.71 | 53.4 | 39.3% |
| Lost / Churned | 9,554 | $119.29 | 1.2 | 38.2% |
| New / Occasional | 2,219 | $147.43 | 1.4 | 8.9% |
| Loyal Fans | 1,699 | $376.71 | 3.3 | 6.8% |
| Needs Attention | 1,179 | $254.41 | 2.2 | 4.7% |
| At Risk | 520 | $193.54 | 2.6 | 2.1% |

Cross-referencing this against actual prior-season renewal outcomes surfaced
the key finding: **774 season ticket holders who did NOT renew last season
were still classified as "Champions"** by pure RFM — because their historical
attendance and spend were high right up until they didn't come back. Only 4
non-renewing STHs landed in "Lost/Churned." RFM, built on trailing behavior,
cannot see a renewal decision before it happens.

This is not a flaw in the analysis — it's the reason Phase 7 needs a
purpose-built predictive churn model (not a segmentation) for season ticket
holders specifically. It also validates Phase 1's original stakeholder
finding in hard numbers: the VP of Marketing and Director of Ticket Sales were
right that current methods (which are essentially RFM-equivalent — tenure,
recency, obvious spend drop-off) can't catch this population.

## Other notable results

- **League-wide Net Promoter Score: 5.8** — calculated from the sparse (2.52%
  response rate) NPS data; directionally useful, not fan-level actionable on
  its own, consistent with the Phase 3 finding on survey sparsity.
- **26 season ticket holders have never opened a single email** despite
  receiving 5+ campaigns — a direct, individually-actionable disengagement list.
- **257 fans attend 20+ games but have never opened a marketing email** — a
  segment fully invisible to the current email-based marketing view, visible
  only by joining ticketing and CRM data (exactly the Phase 1 AS-IS gap).

## Running it locally

```powershell
cd C:\projects\nba-fan-revenue-engine
venv\Scripts\activate
python -c "
import duckdb
con = duckdb.connect('data/warehouse/nba_fan_engine.duckdb')
con.execute(open('sql/01_fan_segmentation_rfm.sql').read())
"
```
Or open any `.sql` file in `sql/` and run individual queries against the
DuckDB file with any SQL client (DBeaver, the `duckdb` CLI, or a notebook).

## Next: Phase 7 — Machine Learning Models

5 models, built directly on this phase's segments and query outputs:
1. **Churn prediction** for season ticket holders (the model this phase's
   finding makes necessary)
2. **Dynamic pricing** recommendations by game/section
3. **Customer lifetime value (CLV)** prediction
4. **Concessions demand forecasting** by stand/gameday
5. **Sponsor audience scoring** by fan segment
