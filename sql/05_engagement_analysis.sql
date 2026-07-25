-- =============================================================================
-- Phase 6 — Descriptive Analysis
-- 05_engagement_analysis.sql
-- Email engagement and NPS sentiment — secondary churn signals for Phase 7
-- (given the NPS response rate is only 2.52% per Phase 3, these matter most
-- in combination with attendance, not alone).
-- =============================================================================

-- Q30: Campaign-level open and click rates
select
    campaign_id,
    count(*) as emails_sent,
    round(100.0 * sum(case when opened then 1 else 0 end) / count(*), 1) as open_rate_pct,
    round(100.0 * sum(case when clicked then 1 else 0 end) / count(*), 1) as click_rate_pct
from main_marts.fact_engagement
group by 1
order by campaign_id;


-- Q31: Fan-level email engagement score — feeds the Phase 7 churn model
-- as a disengagement signal (never opens = early warning)
select
    fan_id,
    count(*) as emails_received,
    sum(case when opened then 1 else 0 end) as emails_opened,
    round(100.0 * sum(case when opened then 1 else 0 end) / count(*), 1) as open_rate_pct
from main_marts.fact_engagement
where fan_id is not null
group by 1
having count(*) >= 5  -- only fans with enough email history to score meaningfully
order by open_rate_pct asc
limit 20;


-- Q32: Season ticket holders who NEVER opened a single email — the clearest
-- disengagement signal identified in Phase 1's stakeholder interviews
select
    f.fan_id,
    f.full_name,
    f.membership_tier,
    count(e.engagement_id) as emails_received
from main_marts.dim_fan f
join main_marts.fact_engagement e on f.fan_id = e.fan_id
where f.is_season_ticket_holder = true
group by 1, 2, 3
having sum(case when e.opened then 1 else 0 end) = 0 and count(e.engagement_id) >= 5
order by emails_received desc;


-- Q33: NPS score distribution (0-10) league-wide
select
    score,
    count(*) as responses,
    round(100.0 * count(*) / sum(count(*)) over (), 1) as pct_of_responses
from main_marts.fact_nps
group by 1
order by 1;


-- Q34: NPS category breakdown (Promoters 9-10, Passives 7-8, Detractors 0-6)
-- and the resulting Net Promoter Score
with categorized as (
    select
        case
            when score >= 9 then 'Promoter'
            when score >= 7 then 'Passive'
            else 'Detractor'
        end as nps_category
    from main_marts.fact_nps
)
select
    round(
        100.0 * (
            sum(case when nps_category = 'Promoter' then 1 else 0 end)
            - sum(case when nps_category = 'Detractor' then 1 else 0 end)
        ) / count(*),
        1
    ) as net_promoter_score,
    sum(case when nps_category = 'Promoter' then 1 else 0 end) as promoters,
    sum(case when nps_category = 'Passive' then 1 else 0 end) as passives,
    sum(case when nps_category = 'Detractor' then 1 else 0 end) as detractors
from categorized;


-- Q35: Average NPS score by game — flags specific games with operational issues
select
    g.game_id,
    g.game_date,
    g.opponent,
    round(avg(n.score), 2) as avg_nps_score,
    count(*) as responses
from main_marts.fact_nps n
join main_marts.dim_game g on n.game_id = g.game_id
group by 1, 2, 3
having count(*) >= 5
order by avg_nps_score asc
limit 10;


-- Q36: Cross-channel view — fans who attend often but never engage with email
-- (a segment invisible to marketing today, per the Phase 1 AS-IS finding)
select
    s.fan_id,
    s.full_name,
    s.frequency_games_attended,
    coalesce(e.emails_received, 0) as emails_received,
    coalesce(e.emails_opened, 0) as emails_opened
from main_marts.fan_rfm_segments s
left join (
    select fan_id, count(*) as emails_received, sum(case when opened then 1 else 0 end) as emails_opened
    from main_marts.fact_engagement
    where fan_id is not null
    group by 1
) e on s.fan_id = e.fan_id
where s.frequency_games_attended >= 20
  and coalesce(e.emails_opened, 0) = 0
order by s.frequency_games_attended desc
limit 20;
