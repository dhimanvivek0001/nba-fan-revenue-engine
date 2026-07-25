-- =============================================================================
-- Phase 6 — Descriptive Analysis
-- 03_revenue_analysis.sql
-- Revenue breakdowns by section, tier, and time — feeds Phase 7's CLV model
-- and the Phase 8 pricing/sponsorship dashboards.
-- =============================================================================

-- Q17: Total ticket revenue and average price by season ticket section
select
    f.section,
    count(distinct f.fan_id) as sth_accounts,
    round(sum(t.price_paid), 0) as total_revenue,
    round(avg(t.price_paid), 2) as avg_price_paid
from main_marts.dim_fan f
join main_marts.fact_ticket_sales t on f.fan_id = t.fan_id
where f.is_season_ticket_holder = true and not t.is_price_missing
group by 1
order by total_revenue desc;


-- Q18: Revenue and account count by membership tier
select
    membership_tier,
    count(*) as accounts,
    round(sum(monetary_total_spend), 0) as total_revenue,
    round(avg(monetary_total_spend), 2) as avg_revenue_per_account
from main_marts.fan_rfm_segments
where is_season_ticket_holder = true
group by 1
order by total_revenue desc;


-- Q19: Estimated fan lifetime-to-date value — join year vs. total spend
-- (a proxy CLV view; Phase 7 builds the full predictive CLV model on this base)
select
    join_year,
    count(*) as accounts,
    round(avg(monetary_total_spend), 2) as avg_spend_this_season,
    round(avg(monetary_total_spend) * (2026 - join_year + 1), 2) as est_cumulative_value_proxy
from main_marts.fan_rfm_segments s
join main_marts.dim_fan f using (fan_id)
where s.is_season_ticket_holder = true and f.join_year is not null
group by 1
order by 1;


-- Q20: Total revenue by month (ticket sales only)
select
    extract(month from purchase_date) as purchase_month,
    round(sum(price_paid), 0) as total_ticket_revenue,
    count(*) as transactions
from main_marts.fact_ticket_sales
where not is_price_missing
group by 1
order by 1;


-- Q21: Price distribution — percentiles, to spot outlier pricing
select
    round(min(price_paid), 2) as min_price,
    round(quantile_cont(price_paid, 0.25), 2) as p25,
    round(quantile_cont(price_paid, 0.50), 2) as median,
    round(quantile_cont(price_paid, 0.75), 2) as p75,
    round(max(price_paid), 2) as max_price,
    round(avg(price_paid), 2) as mean_price
from main_marts.fact_ticket_sales
where not is_price_missing;


-- Q22: Revenue per attendee by tenure bucket (newer vs. long-tenured fans)
select
    case
        when 2026 - join_year <= 2 then '0-2 years'
        when 2026 - join_year <= 5 then '3-5 years'
        else '6+ years'
    end as tenure_bucket,
    count(*) as accounts,
    round(avg(monetary_total_spend), 2) as avg_spend
from main_marts.fan_rfm_segments s
join main_marts.dim_fan f using (fan_id)
where s.is_season_ticket_holder = true and f.join_year is not null
group by 1
order by 1;
