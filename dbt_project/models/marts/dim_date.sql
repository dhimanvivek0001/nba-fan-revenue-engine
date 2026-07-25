-- dim_date: calendar spine covering 2017-01-01 through 2026-12-31 (wide enough
-- to cover the earliest fan signup_date through the current synthetic season).
-- Built with DuckDB's native generate_series — no external package dependency.

select
    cast(d as date) as date_day,
    extract(year from d) as year,
    extract(month from d) as month,
    extract(day from d) as day,
    strftime(d, '%A') as day_name,
    strftime(d, '%B') as month_name,
    case when strftime(d, '%A') in ('Friday', 'Saturday', 'Sunday') then true else false end as is_weekend
from (
    select unnest(generate_series(date '2017-01-01', date '2026-12-31', interval 1 day)) as d
)
