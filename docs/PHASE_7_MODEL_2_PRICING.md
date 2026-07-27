# Phase 7 — Model 2: Dynamic Pricing

## Data-grain limitation, stated upfront

The BRD (FR-06) asks for per-game, **per-section** price recommendations.
The Ticketmaster source system, however, only ever captured a seating section
for season ticket accounts (their fixed season seat) — single-game ticket
transactions carry no section field at all. So "per-section" here means: a
game-level demand multiplier applied on top of each section's historical base
price (derived from actual STH ticket sales in that section). It is not an
independently-modeled per-transaction section effect, because the source data
doesn't support that level of granularity. Documented plainly rather than
quietly assumed away.

## The demand model — an honest negative result, and why it still works

**First attempt:** target-encoding games by opponent (a natural first feature)
produced a demand model with **negative R²** on a held-out test set. Root
cause: this single synthetic season has a median of only 2.5 games per
opponent, and several opponents appear just once — target-encoding was
mostly leaking each game's own attendance back into its "feature" rather than
learning any real draw effect.

**Fix:** opponent was dropped as a model feature entirely. The model now uses
only day-of-week, weekend flag, and month — the only signals repeated often
enough in one 82-game season to model honestly. Evaluated with 5-fold
cross-validation instead of a single fragile train/test split (82 rows is too
few for a stable holdout estimate).

**Result: 5-fold CV R² is still weak (-0.06), MAE 0.077 attendance-rate
points.** This is expected, not a bug: the synthetic attendance data has a
large random variance term relative to the real (but modest) weekend effect,
so precise point-prediction of exact attendance is genuinely hard with only
one season of history. A real production version of this model would need
multiple seasons to separate schedule effects from game-to-game noise.

**But the recommendation direction is validated anyway.** The practical
question for a pricing tool isn't "predict exact attendance" — it's "correctly
rank which games deserve a premium." Backtesting the recommended price
adjustment against actual attendance confirms this works:

| | Actual attendance rate | Recommended price adjustment |
|---|---|---|
| Weekday games | 84.7% | −6.7% |
| Weekend games | 90.5% | +7.7% |

Correlation between recommended adjustment and actual attendance rate:
**0.447** — meaningfully positive. The model correctly identifies premium vs.
discount nights even though it can't predict the exact attendance number for
any single game.

## Section base pricing

35 sections had a reliable sample (≥20 STH ticket sales) to compute a base
price from, ranging roughly $88–$95 depending on section. Recommended price
per game/section = `base_price × (1 + recommended_adjustment_pct)`.

## Business impact (FR-07 backtest)

Estimated **$657,675** in revenue left on the table this season — the sum,
across high-demand games, of the gap between what demand justified charging
and what was actually charged, weighted by attendance. This is the dollar
case for adopting dynamic pricing.

## Outputs

- `models/pricing/pricing_recommendations.csv` — 2,870 game × section price
  recommendations
- `models/pricing/pricing_backtest.csv` — per-game actual vs. recommended
  pricing and attendance
- `models/pricing/pricing_model_metrics.json` — CV R², MAE, backtest
  correlation, revenue-left-on-table estimate

## Running it locally

```powershell
cd C:\projects\nba-fan-revenue-engine
venv\Scripts\activate
python models\pricing\train_pricing_model.py
```

## Next: Model 3 — Customer Lifetime Value (CLV)

Predicting cumulative fan value using tenure, spend trajectory, and
attendance patterns — building on the same fan_rfm_segments view Model 1 used.
