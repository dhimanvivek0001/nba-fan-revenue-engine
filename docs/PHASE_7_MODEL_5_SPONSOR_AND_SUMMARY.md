# Phase 7 — Model 5: Sponsor Audience Scoring

## Why a weighted-scoring model, not a black-box classifier

A sponsorship team pitching a prospective sponsor needs to explain exactly
*why* an audience scored the way it did — "this segment scores 100 on premium
fit because of their spend and attendance levels" is a sentence a salesperson
can say in a meeting. A black-box model's output is not. This model is a
transparent, percentile-based weighted blend, not a trained classifier.

## Data limitation, stated upfront

This synthetic dataset has no age, income, or household data, and fan
city/state were generated with no real geographic clustering (pure random US
addresses, unrelated to any actual arena location). So a genuine "local
audience reach" or demographic-fit archetype isn't supportable here — building
one would mean presenting fabricated signal as real. Only **3 archetypes**
are scored, each grounded in something that actually exists and varies
meaningfully across fan segments: spend, attendance-driven reach, and digital
engagement. A real franchise with actual fan addresses and demographic append
data could extend this same framework with a geographic/demographic
archetype.

## The 3 archetypes

| Archetype | Formula | Sponsor example |
|---|---|---|
| Premium / Luxury Fit | 60% spend score + 40% attendance score | Financial services, luxury auto, premium spirits |
| Mass-Market / Beverage Fit | 50% reach (fan count) + 50% attendance score | QSR, beer, mass-market CPG |
| Digital / Fintech Fit | 50% email engagement + 50% mobile purchase share | Fintech apps, betting/DFS platforms, digital-first brands |

Each underlying metric is percentile-ranked 0–100 across the 6 fan segments
before blending, so scores are always relative to this fan base's own range.

## Results

| Segment | Fans | Avg Spend | Premium/Luxury | Mass-Market | Digital/Fintech |
|---|---|---|---|---|---|
| Champions | 9,829 | $4,993.71 | **100.0** | **100.0** | 66.6 |
| Loyal Fans | 1,699 | $376.71 | 83.3 | 66.6 | 66.6 |
| Needs Attention | 1,179 | $254.41 | 60.0 | 41.6 | 50.0 |
| At Risk | 520 | $193.54 | 56.7 | 41.7 | 41.6 |
| New / Occasional | 2,219 | $147.43 | 33.3 | 50.0 | **83.4** |
| Lost / Churned | 9,554 | $119.29 | 16.7 | 50.0 | 41.7 |

**Champions** are the clear top pitch for a premium sponsor — but
**New/Occasional** fans score highest on digital/fintech fit despite low
spend, since they skew toward mobile-app purchasing and represent a
genuinely different sponsor conversation (an app-download or DFS/betting
platform partner cares about digital reach among newer fans, not season-long
spend).

## Outputs

- `models/sponsor/sponsor_audience_scores.csv` — the sponsorship-deck-ready
  table above
- `models/sponsor/sponsor_model_metrics.json` — archetype list and the
  data-limitation note

## Running it locally

```powershell
cd C:\projects\nba-fan-revenue-engine
venv\Scripts\activate
python models\sponsor\train_sponsor_scoring.py
```

---

# Phase 7 Complete — All 5 ML Models

| # | Model | Headline result |
|---|---|---|
| 1 | Churn Prediction | AUC 0.977 (local), ~$1.83M at-risk revenue with reason codes |
| 2 | Dynamic Pricing | Backtest correlation 0.447 validated, ~$658K revenue left on the table |
| 3 | CLV | $543M total portfolio CLV, churn-weighted |
| 4 | Concessions Forecasting | MAPE 8.1–8.5%, well under the 20% target |
| 5 | Sponsor Audience Scoring | 3 archetypes, sponsorship-deck-ready table |

Every model in this phase found and honestly documented at least one real
limitation along the way — a random label, a leaky feature, a mechanical
correlation, a missing data field — rather than presenting a clean result
that wasn't earned. That trail of honest fixes is arguably the most
interview-worthy part of Phase 7.

## Next: Phase 8 — Power BI Dashboards

4 dashboards (CEO, Ticket Sales, Pricing, Sponsorship), built directly on
these 5 models' outputs and the Phase 5 star schema.
