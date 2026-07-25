-- int_fan_identity_map: THE core identity-resolution model for this project.
--
-- Problem (quantified in Phase 3): Ticketmaster maintains its own customer_id
-- space with no shared key back to the fan master record — 25,318 distinct
-- ticketmaster_customer_id values against 25,000 real fans, including ~750
-- "shadow" accounts from guest checkout.
--
-- Resolution strategy: normalized email is the highest-confidence join key,
-- since it's the one field both systems capture independently for the same
-- person. Where email doesn't resolve (no email on file at Ticketmaster, or a
-- guest-checkout using a secondary address), fall back to normalized
-- full-name match. Anything left unresolved is surfaced, not hidden — an
-- unresolved rate is itself a useful metric to report.

with fan_email as (
    select fan_id, email, lower(trim(first_name || ' ' || last_name)) as full_name
    from {{ ref('stg_fans') }}
),

tm_normalized as (
    select
        ticketmaster_customer_id,
        email,
        lower(trim(full_name)) as full_name
    from {{ ref('stg_ticketmaster_customers') }}
),

matched_on_email as (
    select
        t.ticketmaster_customer_id,
        f.fan_id,
        'email' as match_method
    from tm_normalized t
    inner join fan_email f
        on t.email = f.email
        and t.email is not null
),

matched_on_name as (
    select
        t.ticketmaster_customer_id,
        f.fan_id,
        'name_fallback' as match_method
    from tm_normalized t
    inner join fan_email f
        on t.full_name = f.full_name
    where t.ticketmaster_customer_id not in (select ticketmaster_customer_id from matched_on_email)
),

combined as (
    select * from matched_on_email
    union all
    select * from matched_on_name
),

-- a handful of names/emails aren't unique across 25,000 fans — keep the first
-- deterministic match rather than fanning out a transaction to multiple fans
deduped as (
    select
        ticketmaster_customer_id,
        fan_id,
        match_method,
        row_number() over (partition by ticketmaster_customer_id order by match_method) as rn
    from combined
)

select
    t.ticketmaster_customer_id,
    d.fan_id,
    d.match_method,
    (d.fan_id is null) as is_unresolved
from tm_normalized t
left join deduped d on t.ticketmaster_customer_id = d.ticketmaster_customer_id and d.rn = 1
