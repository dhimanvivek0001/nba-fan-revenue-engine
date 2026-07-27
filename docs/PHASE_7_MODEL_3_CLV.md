# Phase 7 — Model 3: Customer Lifetime Value (CLV)

## Approach

CLV combines two things rather than being modeled from scratch:

1. **Predicted annual spend** — a Ridge regression using tenure, attendance
   rate, email engagement, and membership tier.
2. **Model 1's churn probability** — reused directly (not re-derived), so an
   account's CLV moves consistently with its churn risk rather than the two
   models disagreeing with each other.

**CLV formula:** `predicted_annual_spend / churn_probability`, capped at a
12-year horizon. This is the standard non-contractual CLV formula — the
expected sum of an infinite geometric series of future annual value, where
each year's probability of "still being a customer" shrinks by the churn
rate. A account with 10% annual churn is expected to stick around for ~10
years of value; one with 50% churn, about 2 years. The 12-year cap prevents
near-zero-churn accounts from being valued as effectively infinite.

## Results

| Metric | Value |
|---|---|
| Annual spend model — 5-fold CV R² | **0.912** |
| MAE | $220 |
| Total portfolio CLV (8,500 STH accounts) | **$543,015,377** |
| Average CLV per account | $63,884 |

**Why R² is this high, honestly stated:** attendance rate is not a subtle
predictor of spend here — it's mechanically close to one, because in this
dataset a fan's season spend accumulates directly from the price paid at each
game they attend. High attendance rate and high spend are two views of almost
the same underlying number, not an independent relationship the model
"discovered." This mirrors the honesty note in Model 1's churn AUC: the
strength of the result partly reflects how the underlying data was
constructed, not purely modeling skill — worth saying plainly rather than
presenting it as a bigger insight than it is.

## A genuine data limitation, caught by this model

CLV by membership tier came out nearly flat:

| Tier | Avg CLV | Accounts |
|---|---|---|
| Platinum | $65,007 | 674 |
| Gold | $64,618 | 1,895 |
| Silver | $64,045 | 2,978 |
| Bronze | $62,995 | 2,953 |

In a real franchise, Platinum accounts should be worth meaningfully more than
Bronze — tier is supposed to track spend and seat quality. The near-identical
averages here reveal that `membership_tier` was assigned independently of
actual behavior back in Phase 3's data generation (a random categorical, not
derived from price or spend). This is a documented synthetic-data limitation,
not a modeling error — flagged here rather than left for someone else to
discover, the same way Phase 3's random churn label was caught and fixed
before Model 1 was built. A production fix would tie tier assignment to
historical spend at data-generation time; noted as a backlog item rather than
re-generating the dataset a second time mid-phase.

## Outputs

- `models/clv/clv_scores.csv` — every STH account: predicted annual spend,
  churn probability (from Model 1), implied lifetime years, final CLV
- `models/clv/clv_model_metrics.json` — R², MAE, portfolio totals

## Running it locally

```powershell
cd C:\projects\nba-fan-revenue-engine
venv\Scripts\activate
python models\clv\train_clv_model.py
```
Requires `models/churn/churn_scores.csv` to already exist (Model 1's output).

## Next: Model 4 — Concessions Demand Forecasting

Forecasting F&B demand by stand and gameday, building on the Phase 6
concessions analysis (72% of transactions lack fan linkage, so this model
works at the game/stand level rather than the fan level).
