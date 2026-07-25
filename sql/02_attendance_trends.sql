-- =============================================================================
-- Phase 6 — Descriptive Analysis
-- 02_attendance_trends.sql
-- Attendance patterns across the season — feeds the Phase 7 dynamic pricing
-- model (day-of-week and opponent draw are primary pricing signals) and the
-- Phase 8 CEO dashboard.
-- =============================================================================

-- Q9: Attendance by day of week
select
    day_of_week,
    count(*) as games_played,
    round(avg(final_attendance), 0) as avg_attendance,
    round(100.0 * sum(case when is_sellout then 1 else 0 end) / count(*), 1) as pct_sellouts
from main_marts.dim_game
group by 1
order by avg_attendance desc;


-- Q10: Attendance by opponent — which teams draw the biggest crowds
select
    opponent,
    count(*) as games,
    round(avg(final_attendance), 0) as avg_attendance,
    sum(case when is_sellout then 1 else 0 end) as sellout_games
from main_marts.dim_game
group by 1
order by avg_attendance desc
limit 15;


-- Q11: Attendance trend over the season (month over month)
select
    game_year,
    game_month,
    count(*) as games,
    round(avg(final_attendance), 0) as avg_attendance
from main_marts.dim_game
group by 1, 2
order by 1, 2;


-- Q12: Weekend vs. weekday attendance comparison
select
    is_weekend,
    count(*) as games,
    round(avg(final_attendance), 0) as avg_attendance,
    round(avg(case when is_sellout then 1.0 else 0.0 end) * 100, 1) as pct_sellouts
from main_marts.dim_game
group by 1;


-- Q13: Season ticket holder attendance rate (games attended / total home games)
-- — the single most important input to the Phase 7 churn model
select
    fan_id,
    full_name,
    membership_tier,
    frequency_games_attended,
    round(100.0 * frequency_games_attended / (select count(*) from main_marts.dim_game), 1) as attendance_rate_pct
from main_marts.fan_rfm_segments
where is_season_ticket_holder = true
order by attendance_rate_pct asc
limit 20;


-- Q14: Ticket purchase channel mix (web / mobile / box office / phone)
select
    purchase_channel,
    count(*) as transactions,
    round(100.0 * count(*) / sum(count(*)) over (), 1) as pct_of_transactions,
    round(avg(price_paid), 2) as avg_price_paid
from main_marts.fact_ticket_sales
where not is_price_missing
group by 1
order by transactions desc;


-- Q15: Games ranked by total ticket revenue — highest earners
select
    g.game_id,
    g.game_date,
    g.opponent,
    g.final_attendance,
    round(sum(t.price_paid), 0) as ticket_revenue
from main_marts.fact_ticket_sales t
join main_marts.dim_game g on t.game_id = g.game_id
where not t.is_price_missing
group by 1, 2, 3, 4
order by ticket_revenue desc
limit 10;


-- Q16: Lowest-attendance games (candidates for promotional pricing — feeds Phase 7)
select
    game_id,
    game_date,
    opponent,
    day_of_week,
    final_attendance,
    is_sellout
from main_marts.dim_game
order by final_attendance asc
limit 10;
