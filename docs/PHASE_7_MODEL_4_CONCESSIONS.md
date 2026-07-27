# Phase 7 — Model 4: Concessions Demand Forecasting

## Grain: game × stand, not fan-level

Phase 3/5 established that 72.0% of concession transactions carry no fan
linkage at all. Fan-level forecasting isn't possible with this data — and
isn't actually what a gameday operations team needs anyway. This model
forecasts transaction volume per stand, per game — the grain that drives
staffing decisions.

## Validation approach

Evaluated with **GroupKFold by `game_id`** rather than a random row split.
A random split would let rows from the same game land in both train and test,
which would make the held-out error meaningless for the real question this
model answers: *"can we forecast a game we haven't seen yet?"* Every fold
holds out entire games, never partial ones.

## Result

| Metric | Value | BRD Target (FR-08) |
|---|---|---|
| MAPE (held-out games) | **8.1%** | ≤ 20% |

Comfortably exceeds the target. **Why, honestly stated:** `final_attendance`
alone accounts for 83.3% of feature importance — attendance is the dominant,
almost mechanical driver of how many concession transactions occur (more
people in the building, more transactions), so this is a case where the
"forecast" is largely a well-calibrated multiplier on attendance rather than
a subtle pattern-discovery exercise. `stand_id` correctly contributes almost
nothing to the model, which is the right answer: stands were assigned to
transactions uniformly at random in the source data (no stand is genuinely
more popular than another), and a well-behaved model should learn exactly
that — not invent a fake stand-specific pattern to overfit on. A real
franchise's actual concession data would very likely show genuine
stand-to-stand variation (a stand near the home section sells more team gear
and hot dogs, one near a family section sells more soda) — this model would
pick that up the moment real data reflected it.

## Outputs

- `models/concessions/concessions_forecast.csv` — every game × stand
  combination: actual vs. predicted transaction count, absolute % error
- `models/concessions/staffing_priority_by_game.csv` — stands ranked by
  predicted volume within each game, ready to hand to gameday ops for
  staffing allocation
- `models/concessions/concessions_model_metrics.json` — MAPE, feature
  importances

## Running it locally

```powershell
cd C:\projects\nba-fan-revenue-engine
venv\Scripts\activate
python models\concessions\train_concessions_model.py
```

## Next: Model 5 — Sponsor Audience Scoring

Scoring fan segments (from Phase 6's RFM view) for sponsor-relevant audience
fit — the last of the 5 ML models, feeding directly into the Phase 8
sponsorship dashboard.
