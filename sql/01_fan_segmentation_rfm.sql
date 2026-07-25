-- =============================================================================
-- Phase 6 — Descriptive Analysis
-- 01_fan_segmentation_rfm.sql
--
-- RFM (Recency, Frequency, Monetary) segmentation of every fan based on their
-- ticket purchase behavior across the season. This is the analytical
-- foundation the Phase 7 churn model builds directly on top of.
--
-- Recency anchor: the most recent game_date in the season (this is a
-- point-in-time, single-season retrospective — in production this would be
-- "today", refreshed daily by the Phase 4 pipeline).
-- =============================================================================

-- Q1: Season anchor date (most recent game) — used as "today" for recency
select max(game_date) as season_anchor_date
from main_marts.dim_game;


-- Q2: Raw RFM inputs per fan (games attended, total spend, days since last game)
with anchor as (
    select max(game_date) as anchor_date from main_marts.dim_game
),
fan_rfm_raw as (
    select
        f.fan_id,
        f.full_name,
        f.is_season_ticket_holder,
        f.membership_tier,
        count(distinct t.game_id) as frequency_games_attended,
        coalesce(sum(t.price_paid), 0) as monetary_total_spend,
        max(g.game_date) as last_game_date,
        date_diff('day', max(g.game_date), (select anchor_date from anchor)) as recency_days_since_last_game
    from main_marts.dim_fan f
    left join main_marts.fact_ticket_sales t on f.fan_id = t.fan_id
    left join main_marts.dim_game g on t.game_id = g.game_id
    group by 1, 2, 3, 4
)
select * from fan_rfm_raw
order by monetary_total_spend desc
limit 20;


-- Q3: RFM quartile scoring (1 = worst, 4 = best) and segment assignment.
-- This is the reusable view Phase 7's churn model will pull segment labels from.
create or replace view main_marts.fan_rfm_segments as
with anchor as (
    select max(game_date) as anchor_date from main_marts.dim_game
),
fan_rfm_raw as (
    select
        f.fan_id,
        f.full_name,
        f.is_season_ticket_holder,
        f.membership_tier,
        f.prior_season_renewal_status,
        count(distinct t.game_id) as frequency_games_attended,
        coalesce(sum(t.price_paid), 0) as monetary_total_spend,
        case
            when max(g.game_date) is null then null
            else date_diff('day', max(g.game_date), (select anchor_date from anchor))
        end as recency_days_since_last_game
    from main_marts.dim_fan f
    left join main_marts.fact_ticket_sales t on f.fan_id = t.fan_id
    left join main_marts.dim_game g on t.game_id = g.game_id
    group by 1, 2, 3, 4, 5
),
scored as (
    select
        *,
        ntile(4) over (order by recency_days_since_last_game desc nulls first) as recency_score,
        ntile(4) over (order by frequency_games_attended asc) as frequency_score,
        ntile(4) over (order by monetary_total_spend asc) as monetary_score
    from fan_rfm_raw
)
select
    *,
    (recency_score + frequency_score + monetary_score) as rfm_total_score,
    case
        when recency_score >= 3 and frequency_score >= 3 and monetary_score >= 3 then 'Champions'
        when frequency_score >= 3 and monetary_score >= 3 then 'Loyal Fans'
        when recency_score <= 2 and frequency_score >= 3 then 'At Risk'
        when recency_score <= 2 and frequency_score <= 2 and monetary_score <= 2 then 'Lost / Churned'
        when recency_score >= 3 and frequency_score <= 2 then 'New / Occasional'
        else 'Needs Attention'
    end as fan_segment
from scored;


-- Q4: Segment size and average value — the headline table for a stakeholder deck
select
    fan_segment,
    count(*) as fan_count,
    round(avg(monetary_total_spend), 2) as avg_spend,
    round(avg(frequency_games_attended), 1) as avg_games_attended,
    round(100.0 * count(*) / sum(count(*)) over (), 1) as pct_of_base
from main_marts.fan_rfm_segments
group by 1
order by avg_spend desc;


-- Q5: "At Risk" season ticket holders specifically — the Phase 1 $2.4M cohort,
-- now identified at the individual account level instead of an estimate
select
    s.fan_id,
    s.full_name,
    s.membership_tier,
    s.frequency_games_attended,
    s.monetary_total_spend,
    s.recency_days_since_last_game,
    s.prior_season_renewal_status
from main_marts.fan_rfm_segments s
where s.is_season_ticket_holder = true
  and s.fan_segment = 'At Risk'
order by s.monetary_total_spend desc;


-- Q6: RFM segment vs. actual prior-season renewal outcome — validates the
-- segmentation against a real-world label before Phase 7 builds a model on it
select
    fan_segment,
    prior_season_renewal_status,
    count(*) as fan_count
from main_marts.fan_rfm_segments
where is_season_ticket_holder = true
group by 1, 2
order by 1, 2;


-- Q7: Membership tier composition within each RFM segment
select
    fan_segment,
    membership_tier,
    count(*) as fan_count
from main_marts.fan_rfm_segments
where is_season_ticket_holder = true and membership_tier is not null
group by 1, 2
order by 1, 2;


-- Q8: Distribution of games attended (histogram-style buckets) across all fans
select
    case
        when frequency_games_attended = 0 then '0 games'
        when frequency_games_attended between 1 and 5 then '1-5 games'
        when frequency_games_attended between 6 and 20 then '6-20 games'
        when frequency_games_attended between 21 and 50 then '21-50 games'
        else '50+ games'
    end as attendance_bucket,
    count(*) as fan_count
from main_marts.fan_rfm_segments
group by 1
order by min(frequency_games_attended);
