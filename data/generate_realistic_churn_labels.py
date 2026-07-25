"""
Phase 7 — Realistic churn label generation.

Phase 3's `prior_season_renewal_status` was assigned as pure random noise
(np.random.choice, independent of any behavior). A churn model trained on
that label would learn nothing — AUC ~0.5 regardless of features used,
failing the BRD's FR-03 acceptance criterion (AUC >= 0.75).

This script replaces that label with one derived from real, already-generated
behavioral signals — attendance rate, spend, recency, email engagement, and
membership tier — combined with a logistic function and calibrated noise, so
the ~9% base churn rate from Phase 3 is preserved but now genuinely
correlated with the features a real model would have access to. This mirrors
how a real analytics team would catch and fix an unrealistic label before
model-building, which is a more honest project narrative than pretending the
original random label was fine.
"""
import duckdb
import numpy as np
import pandas as pd
import os

SEED = 42
np.random.seed(SEED)

BASE = os.path.dirname(__file__)
DUCKDB_PATH = os.path.join(BASE, "warehouse", "nba_fan_engine.duckdb")
RAW_STH_PATH = os.path.join(BASE, "raw", "season_ticket_accounts.csv")

con = duckdb.connect(DUCKDB_PATH)

# Pull real behavioral features for every STH from the already-built star schema
features = con.execute("""
    select
        s.sth_account_id,
        s.fan_id,
        coalesce(seg.frequency_games_attended, 0) as games_attended,
        coalesce(seg.monetary_total_spend, 0) as total_spend,
        coalesce(seg.recency_days_since_last_game, 999) as recency_days,
        s.membership_tier,
        coalesce(eng.emails_received, 0) as emails_received,
        coalesce(eng.emails_opened, 0) as emails_opened
    from main_staging.stg_season_ticket_accounts s
    left join main_marts.fan_rfm_segments seg on s.fan_id = seg.fan_id
    left join (
        select fan_id, count(*) as emails_received, sum(case when opened then 1 else 0 end) as emails_opened
        from main_marts.fact_engagement
        where fan_id is not null
        group by 1
    ) eng on s.fan_id = eng.fan_id
""").fetchdf()

con.close()

N_GAMES = 82
features["attendance_rate"] = features["games_attended"] / N_GAMES
features["email_open_rate"] = np.where(
    features["emails_received"] > 0,
    features["emails_opened"] / features["emails_received"],
    0.5,  # neutral default for accounts with no email history
)
# z-score spend within membership tier (a Platinum spending less than peers is
# a stronger signal than the same raw dollar amount for a Bronze account)
features["spend_z"] = features.groupby("membership_tier")["total_spend"].transform(
    lambda x: (x - x.mean()) / (x.std() + 1e-6)
)

tier_bonus = {"Platinum": 0.5, "Gold": 0.2, "Silver": -0.1, "Bronze": -0.3}
features["tier_bonus"] = features["membership_tier"].map(tier_bonus).fillna(0)

# Linear risk score: lower attendance, lower spend, lower email engagement,
# lower tier, and higher recency (longer since last game) all increase churn risk
risk_score = (
    -3.5 * features["attendance_rate"]
    - 1.2 * features["spend_z"]
    - 1.5 * features["email_open_rate"]
    - features["tier_bonus"]
    + 0.05 * features["recency_days"]
    + np.random.normal(0, 0.6, size=len(features))  # irreducible noise — no real-world churn is fully predictable
)

# Calibrate threshold so ~9% churn (matching Phase 3's original base rate) —
# but now the 9% who churn are the fans the risk score actually flags
threshold = np.quantile(risk_score, 0.91)
features["prior_season_renewal_status"] = np.where(
    risk_score >= threshold, "not_renewed", "renewed"
)

print("New label distribution:")
print(features["prior_season_renewal_status"].value_counts())
print("\nSanity check — avg attendance rate by label:")
print(features.groupby("prior_season_renewal_status")["attendance_rate"].mean())
print("\nSanity check — avg email open rate by label:")
print(features.groupby("prior_season_renewal_status")["email_open_rate"].mean())

# Write the new label back into the raw season_ticket_accounts.csv, preserving
# every other column exactly as Phase 3 generated it
sth_raw = pd.read_csv(RAW_STH_PATH)
label_map = dict(zip(features["sth_account_id"], features["prior_season_renewal_status"]))
sth_raw["prior_season_renewal_status"] = sth_raw["sth_account_id"].map(label_map)
sth_raw.to_csv(RAW_STH_PATH, index=False)
print(f"\nWrote updated labels to {RAW_STH_PATH}")
