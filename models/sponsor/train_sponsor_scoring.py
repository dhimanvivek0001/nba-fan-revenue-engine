"""
Phase 7 — Model 5: Sponsor Audience Scoring.

Fulfills BRD FR-09 (score fan segments for sponsor-audience fit, exportable
to a sponsorship-deck-ready table). This is a transparent weighted-scoring
model rather than a black-box classifier — appropriate here, since a
sponsorship team needs to be able to explain to a prospective sponsor exactly
why an audience scored the way it did, not just trust an opaque number.

Data limitation, stated upfront: this synthetic dataset has no age, income,
or household data, and fan city/state was generated with no geographic
clustering (pure random US addresses) — so a genuine "local audience reach"
or demographic-fit archetype isn't supportable here. Only 3 archetypes are
scored, each grounded in a signal that actually exists and varies meaningfully
in the data: spend, attendance-driven reach, and digital engagement. A real
franchise with actual fan addresses and any demographic append data could add
a geographic/demographic archetype on top of this same framework.
"""
import duckdb
import pandas as pd
import numpy as np
import os
import json

BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DUCKDB_PATH = os.path.join(BASE, "data", "warehouse", "nba_fan_engine.duckdb")
OUT_DIR = os.path.dirname(__file__)

con = duckdb.connect(DUCKDB_PATH)

# Per-fan channel mix (mobile app share = digital engagement proxy)
channel_mix = con.execute("""
    select
        fan_id,
        count(*) as total_tx,
        sum(case when purchase_channel = 'mobile_app' then 1 else 0 end) as mobile_tx
    from main_marts.fact_ticket_sales
    where fan_id is not null
    group by 1
""").fetchdf()
channel_mix["mobile_share"] = channel_mix["mobile_tx"] / channel_mix["total_tx"]

# Per-fan email engagement
email_eng = con.execute("""
    select fan_id, count(*) as emails_received, sum(case when opened then 1 else 0 end) as emails_opened
    from main_marts.fact_engagement
    where fan_id is not null
    group by 1
""").fetchdf()
email_eng["open_rate"] = np.where(email_eng["emails_received"] > 0, email_eng["emails_opened"] / email_eng["emails_received"], np.nan)

segments = con.execute("select * from main_marts.fan_rfm_segments").fetchdf()
con.close()

df = segments.merge(channel_mix[["fan_id", "mobile_share"]], on="fan_id", how="left")
df = df.merge(email_eng[["fan_id", "open_rate"]], on="fan_id", how="left")

# --- Segment-level aggregates ---
seg_stats = df.groupby("fan_segment").agg(
    fan_count=("fan_id", "count"),
    avg_spend=("monetary_total_spend", "mean"),
    avg_attendance_rate=("frequency_games_attended", lambda x: x.mean() / 82),
    avg_email_open_rate=("open_rate", "mean"),
    avg_mobile_share=("mobile_share", "mean"),
).reset_index()

# --- Percentile-normalize each raw metric to 0-100 across segments ---
def pct_scale(s):
    return (s.rank(pct=True) * 100).round(1)

seg_stats["spend_score"] = pct_scale(seg_stats["avg_spend"])
seg_stats["reach_score"] = pct_scale(seg_stats["fan_count"])
seg_stats["attendance_score"] = pct_scale(seg_stats["avg_attendance_rate"])
seg_stats["engagement_score"] = pct_scale(seg_stats["avg_email_open_rate"].fillna(0))
seg_stats["digital_score"] = pct_scale(seg_stats["avg_mobile_share"].fillna(0))

# --- 3 sponsor archetypes, each a transparent weighted blend ---
seg_stats["premium_luxury_fit"] = (
    0.6 * seg_stats["spend_score"] + 0.4 * seg_stats["attendance_score"]
).round(1)

seg_stats["mass_market_beverage_fit"] = (
    0.5 * seg_stats["reach_score"] + 0.5 * seg_stats["attendance_score"]
).round(1)

seg_stats["digital_fintech_fit"] = (
    0.5 * seg_stats["engagement_score"] + 0.5 * seg_stats["digital_score"]
).round(1)

# --- Sponsorship-deck-ready output table ---
deck_table = seg_stats[[
    "fan_segment", "fan_count", "avg_spend", "avg_attendance_rate",
    "premium_luxury_fit", "mass_market_beverage_fit", "digital_fintech_fit",
]].sort_values("fan_count", ascending=False)
deck_table.to_csv(os.path.join(OUT_DIR, "sponsor_audience_scores.csv"), index=False)

print("Sponsor Audience Scoring — by fan segment:\n")
print(deck_table.to_string(index=False))

metrics = {
    "n_segments": int(len(seg_stats)),
    "archetypes_scored": ["premium_luxury_fit", "mass_market_beverage_fit", "digital_fintech_fit"],
    "data_limitation": "No age/income/household data and no real geographic clustering in this synthetic dataset — a demographic or local-reach archetype was deliberately not built rather than faked.",
}
with open(os.path.join(OUT_DIR, "sponsor_model_metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)

print(f"\nSaved: sponsor_audience_scores.csv, sponsor_model_metrics.json")
