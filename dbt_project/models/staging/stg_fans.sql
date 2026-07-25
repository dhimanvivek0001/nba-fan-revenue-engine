-- stg_fans: collapses the 750 duplicate fan registrations found in Phase 3.
-- Duplicate registrations share last_name, city, state, zip, and signup_date
-- (re-registration doesn't change your address or your signup history) but
-- often have a different email/first_name casing and a missing phone.
-- Resolution rule: group on the stable attributes, keep the most complete row
-- (prefer non-null phone; break ties by lowest true_fan_id for determinism).

with ranked as (

    select
        true_fan_id,
        first_name,
        last_name,
        lower(trim(email)) as email,
        phone,
        city,
        state,
        zip,
        signup_date,
        is_season_ticket_holder,
        row_number() over (
            partition by last_name, city, state, zip, signup_date, is_season_ticket_holder
            order by (phone is not null) desc, true_fan_id asc
        ) as rn,
        count(*) over (
            partition by last_name, city, state, zip, signup_date, is_season_ticket_holder
        ) as group_size
    from bronze_fans

)

select
    true_fan_id as fan_id,
    first_name,
    last_name,
    email,
    phone,
    city,
    state,
    zip,
    signup_date,
    is_season_ticket_holder,
    group_size > 1 as had_duplicate_registration
from ranked
where rn = 1
