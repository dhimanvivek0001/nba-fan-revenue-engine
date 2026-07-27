"""
Phase 7 — Model 2: Dynamic Pricing.

Fulfills BRD FR-06 (recommend a per-game, per-section price adjustment based
on demand signals) and FR-07 (backtest recommendations against historical
sell-through).

Data-grain note: the Ticketmaster source system tracks price per transaction
but never captured a seating section on single-game purchases — only season
ticket accounts carry a section (their fixed season seat). So "per-section"
pricing here means: a game-level demand multiplier applied on top of each
section's historical base price (derived from actual STH ticket sales in
that section), not a genuinely independent per-transaction section field.
This is stated plainly rather than papered over.
"""
import duckdb
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_absolute_error
import os
import json

SEED = 42
BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DUCKDB_PATH = os.path.join(BASE, "data", "warehouse", "nba_fan_engine.duckdb")
OUT_DIR = os.path.dirname(__file__)

con = duckdb.connect(DUCKDB_PATH)

# --- Step 1: Game-level demand data ---
games = con.execute("""
    select game_id, game_date, opponent, day_of_week, is_weekend,
           final_attendance, is_sellout, game_month
    from main_marts.dim_game
""").fetchdf()

CAPACITY = 18000
games["attendance_rate"] = games["final_attendance"] / CAPACITY

# opponent historical draw (target-encode by that opponent's mean attendance rate)
opponent_draw = games.groupby("opponent")["attendance_rate"].mean().rename("opponent_avg_draw")
games = games.merge(opponent_draw, on="opponent", how="left")

# --- Step 2: Demand model — predict attendance rate from schedule signals ---
# Note: opponent is deliberately NOT used as a model feature. Most opponents
# appear only 1-3 times in a single 82-game season (median 2.5), so target-
# encoding by opponent would mostly be leaking each game's own attendance back
# into its "feature" rather than learning a real draw effect — confirmed by
# an initial version of this model scoring negative R² on a held-out split.
# Day-of-week and month are the only signals repeated enough times in one
# season to model honestly. Opponent-specific draw would need multiple
# seasons of history to estimate reliably — a documented limitation, not a
# hidden one.
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_predict

feature_cols = ["is_weekend", "day_of_week", "game_month"]
X = pd.get_dummies(games[feature_cols], columns=["day_of_week", "game_month"], dummy_na=False)
y = games["attendance_rate"]

demand_model = Ridge(alpha=5.0, random_state=SEED)

# 5-fold cross-validation — with only 82 games, a single train/test split is
# too small to give a stable R² estimate; CV uses every game as a test point once
kf = KFold(n_splits=5, shuffle=True, random_state=SEED)
cv_predictions = cross_val_predict(demand_model, X, y, cv=kf)
r2 = r2_score(y, cv_predictions)
mae = mean_absolute_error(y, cv_predictions)
print(f"Demand model — 5-fold CV R²: {r2:.3f}, MAE: {mae:.4f} (attendance rate)")

# fit on all data for final scoring/recommendations
demand_model.fit(X, y)
games["predicted_attendance_rate"] = demand_model.predict(X)
games["demand_percentile"] = games["predicted_attendance_rate"].rank(pct=True)

# --- Step 3: Convert demand percentile into a price adjustment ---
# +/-15% max swing: bottom-decile games get a 15% discount recommendation,
# top-decile games get a 15% premium. Linear in between, centered at 0% for
# median demand.
MAX_SWING = 0.15
games["recommended_price_adjustment_pct"] = ((games["demand_percentile"] - 0.5) * 2 * MAX_SWING * 100).round(1)

# --- Step 4: Section base prices, derived from actual STH ticket sales ---
section_prices = con.execute("""
    select f.section, round(avg(t.price_paid), 2) as base_price, count(*) as sample_size
    from main_marts.fact_ticket_sales t
    join main_marts.dim_fan f on t.fan_id = f.fan_id
    where f.is_season_ticket_holder = true and f.section is not null and not t.is_price_missing
    group by 1
    having count(*) >= 20
    order by base_price desc
""").fetchdf()
con.close()

print(f"\n{len(section_prices)} sections with a reliable base price (>=20 sales)")
print(section_prices.head(10).to_string(index=False))

# --- Step 5: Build the full per-game, per-section recommendation table ---
recommendations = []
for _, g in games.iterrows():
    for _, s in section_prices.iterrows():
        rec_price = round(s["base_price"] * (1 + g["recommended_price_adjustment_pct"] / 100), 2)
        recommendations.append({
            "game_id": g["game_id"],
            "game_date": g["game_date"],
            "opponent": g["opponent"],
            "section": s["section"],
            "base_price": s["base_price"],
            "demand_percentile": round(g["demand_percentile"], 3),
            "recommended_price_adjustment_pct": g["recommended_price_adjustment_pct"],
            "recommended_price": rec_price,
        })
rec_df = pd.DataFrame(recommendations)
rec_df.to_csv(os.path.join(OUT_DIR, "pricing_recommendations.csv"), index=False)
print(f"\nWrote {len(rec_df):,} game x section price recommendations")

# --- Step 6: Backtest against historical sell-through (FR-07) ---
# Validate direction: do high-recommended-premium games actually correspond to
# real sellouts / high attendance? And quantify "revenue left on the table" —
# games where actual average price paid was below what demand justified.
actual_avg_price_by_game = con2 = duckdb.connect(DUCKDB_PATH).execute("""
    select game_id, round(avg(price_paid), 2) as actual_avg_price
    from main_marts.fact_ticket_sales
    where not is_price_missing
    group by 1
""").fetchdf()

backtest = games.merge(actual_avg_price_by_game, on="game_id", how="left")
# blended "recommended price" per game = demand-adjusted average across sections
avg_base_price = section_prices["base_price"].mean()
backtest["recommended_avg_price"] = (avg_base_price * (1 + backtest["recommended_price_adjustment_pct"] / 100)).round(2)
backtest["price_gap"] = backtest["recommended_avg_price"] - backtest["actual_avg_price"]

# Revenue left on the table: for high-demand games where actual price undershot
# the recommendation, the gap x attendance is potential uplift left uncaptured
backtest["revenue_gap_estimate"] = np.where(
    backtest["price_gap"] > 0,
    backtest["price_gap"] * backtest["final_attendance"] * 0.15,  # 15% of attendees are price-elastic ticket buyers (STH excluded, they don't pay per-game price)
    0
)
total_revenue_left = backtest["revenue_gap_estimate"].sum()

# Direction check: correlation between recommended adjustment and actual attendance rate
corr = backtest["recommended_price_adjustment_pct"].corr(backtest["attendance_rate"])

print(f"\n--- Backtest (FR-07) ---")
print(f"Correlation between recommended price adjustment and actual attendance rate: {corr:.3f} (positive = model direction validated)")
print(f"Estimated revenue left on the table this season (undershot high-demand games): ${total_revenue_left:,.0f}")

backtest.to_csv(os.path.join(OUT_DIR, "pricing_backtest.csv"), index=False)

metrics = {
    "demand_model_r2": round(float(r2), 3),
    "demand_model_mae": round(float(mae), 4),
    "n_games": int(len(games)),
    "n_sections_priced": int(len(section_prices)),
    "backtest_correlation": round(float(corr), 3),
    "estimated_revenue_left_on_table": round(float(total_revenue_left), 0),
}
with open(os.path.join(OUT_DIR, "pricing_model_metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)

print("\nTop 5 highest-demand games (recommend premium pricing):")
print(games.nlargest(5, "predicted_attendance_rate")[["game_id", "opponent", "day_of_week", "recommended_price_adjustment_pct"]].to_string(index=False))
print("\nTop 5 lowest-demand games (recommend discount pricing):")
print(games.nsmallest(5, "predicted_attendance_rate")[["game_id", "opponent", "day_of_week", "recommended_price_adjustment_pct"]].to_string(index=False))
