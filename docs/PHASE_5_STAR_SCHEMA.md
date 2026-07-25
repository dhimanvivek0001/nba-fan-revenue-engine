# Phase 5 — Star Schema Data Modeling (Gold Layer)

## What this phase builds

The Gold-layer star schema on top of Phase 4's Silver models — the tables
Phases 6–9 (SQL analysis, ML models, dashboards, real-time ops) query directly.
Nothing downstream should ever query a `bronze_*` or `stg_*` table again.

## Schema

**Dimensions**
| Table | Grain | Rows |
|---|---|---|
| `dim_fan` | one row per resolved fan, enriched with STH attributes | 25,000 |
| `dim_game` | one row per game | 82 |
| `dim_date` | one row per calendar day, 2017–2026 | 3,652 |

**Facts**
| Table | Grain | Rows | Fan-resolved |
|---|---|---|---|
| `fact_ticket_sales` | one row per ticket transaction | 549,896 | 100% (via Phase 4 identity map) |
| `fact_concessions` | one row per concession transaction | 781,785 | 28.0% (matches the Phase 3 DQ finding exactly — this ceiling is real, not a modeling gap) |
| `fact_engagement` | one row per email sent | 370,143 | 96.3% |
| `fact_nps` | one row per survey response | 32,499 | 70.1% |

`fact_ticket_sales` excludes the 1,662 orphan-game-reference rows quarantined
in Phase 4 — they can't join to a real `game_id` and would break every
downstream aggregation if included silently.

## A second identity-resolution bug, caught by testing

Building `fact_engagement` and `fact_nps` surfaced a new edge case beyond the
one Phase 4 solved: at 25,000-fan scale, **4 pairs of fans coincidentally share
an identical generated email address**. A plain join on email fanned out
127 engagement rows (each email-sent event appeared twice, once per matching
fan) — caught immediately by the `unique_engagement_id` dbt test failing.

Fix: the same deterministic-tiebreak pattern used in Phase 4's Ticketmaster
resolution — pick one canonical fan per email, lowest `fan_id` wins — applied
in both `fact_engagement` and `fact_nps`. All 34 dbt tests pass after the fix.

This is a small but real example of why testing every grain assumption matters:
a "one row per email sent" fact table silently became "one or two rows" the
moment a join key wasn't provably unique, and nothing about the row counts
alone would have flagged it without the test.

## Running it locally

```powershell
cd C:\projects\nba-fan-revenue-engine\dbt_project
$env:DBT_PROFILES_DIR = "."
dbt run
dbt test
```
16 models build (8 staging views + 1 intermediate + 3 dimensions + 4 facts +
this doc's schema tests), 34 tests, all passing.

## Next: Phase 6 — Descriptive Analysis

A 30+ query SQL library against this star schema: RFM fan segmentation,
attendance trends, revenue-per-section, concession velocity by stand — the
analysis Phases 7–9 build on top of.
