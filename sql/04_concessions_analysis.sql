-- =============================================================================
-- Phase 6 — Descriptive Analysis
-- 04_concessions_analysis.sql
-- Concession sales patterns by stand, item, and game — feeds the Phase 7
-- concessions demand forecasting model and the Phase 9 matchday ops dashboard.
-- Note: only 28.0% of these transactions are fan-linked (per Phase 3/5
-- findings), so most queries here are at the game/stand level, not fan level.
-- =============================================================================

-- Q23: Top-selling items by total revenue and volume
select
    item,
    count(*) as transactions,
    round(sum(amount), 0) as total_revenue,
    round(avg(amount), 2) as avg_price
from main_marts.fact_concessions
where not is_refund_or_void
group by 1
order by total_revenue desc;


-- Q24: Revenue and transaction volume by stand
select
    stand_id,
    count(*) as transactions,
    round(sum(amount), 0) as total_revenue,
    round(avg(amount), 2) as avg_transaction_value
from main_marts.fact_concessions
where not is_refund_or_void
group by 1
order by total_revenue desc;


-- Q25: Concession spend per attendee, by game — the core signal for the
-- Phase 7 demand forecasting model
select
    g.game_id,
    g.game_date,
    g.opponent,
    g.final_attendance,
    round(sum(c.amount), 0) as total_concession_revenue,
    round(sum(c.amount) / g.final_attendance, 2) as revenue_per_attendee
from main_marts.fact_concessions c
join main_marts.dim_game g on c.game_id = g.game_id
where not c.is_refund_or_void
group by 1, 2, 3, 4
order by revenue_per_attendee desc
limit 15;


-- Q26: Concession transaction velocity by hour-of-game (using transaction_datetime)
select
    extract(hour from transaction_datetime) as hour_of_day,
    count(*) as transactions,
    round(sum(amount), 0) as total_revenue
from main_marts.fact_concessions
where not is_refund_or_void
group by 1
order by 1;


-- Q27: Refund/void rate by stand — an operational quality signal
select
    stand_id,
    count(*) as total_transactions,
    sum(case when is_refund_or_void then 1 else 0 end) as refunds_voids,
    round(100.0 * sum(case when is_refund_or_void then 1 else 0 end) / count(*), 2) as refund_rate_pct
from main_marts.fact_concessions
group by 1
order by refund_rate_pct desc;


-- Q28: Fan-linked concession spend vs. total (quantifies the 28% linkage ceiling)
select
    count(*) as total_transactions,
    sum(case when fan_id is not null then 1 else 0 end) as fan_linked_transactions,
    round(100.0 * sum(case when fan_id is not null then 1 else 0 end) / count(*), 1) as pct_fan_linked,
    round(sum(case when fan_id is not null then amount else 0 end), 0) as fan_linked_revenue,
    round(sum(amount), 0) as total_revenue
from main_marts.fact_concessions
where not is_refund_or_void;


-- Q29: Average concession spend per fan-linked transaction, by membership tier
-- (only usable for the 28% of transactions with a fan_id)
select
    f.membership_tier,
    count(*) as transactions,
    round(avg(c.amount), 2) as avg_spend_per_transaction
from main_marts.fact_concessions c
join main_marts.dim_fan f on c.fan_id = f.fan_id
where not c.is_refund_or_void and f.membership_tier is not null
group by 1
order by avg_spend_per_transaction desc;
