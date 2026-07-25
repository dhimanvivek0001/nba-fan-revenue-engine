-- dim_fan: one row per resolved fan, enriched with season-ticket-holder attributes
-- where applicable. This is the canonical fan dimension every fact table joins to.

with sth as (
    select
        fan_id,
        sth_account_id,
        section,
        seat,
        membership_tier,
        join_year,
        prior_season_renewal_status
    from {{ ref('stg_season_ticket_accounts') }}
)

select
    f.fan_id,
    f.first_name,
    f.last_name,
    f.first_name || ' ' || f.last_name as full_name,
    f.email,
    f.phone,
    f.city,
    f.state,
    f.zip,
    f.signup_date,
    f.is_season_ticket_holder,
    f.had_duplicate_registration,
    s.sth_account_id,
    s.section,
    s.seat,
    s.membership_tier,
    s.join_year,
    s.prior_season_renewal_status
from {{ ref('stg_fans') }} f
left join sth s on f.fan_id = s.fan_id
