-- fact_nps: grain is one row per survey response. fan_id joined on normalized
-- respondent email where present (70.1% of rows per Phase 3) — the remaining
-- anonymous responses still feed game-level sentiment aggregation.

-- fact_nps: grain is one row per survey response. fan_id joined on normalized
-- respondent email where present (70.1% of rows per Phase 3) — the remaining
-- anonymous responses still feed game-level sentiment aggregation. Deduped to
-- one fan per email for the same reason as fact_engagement.

with fan_by_email as (
    select fan_id, email
    from {{ ref('stg_fans') }}
    where email is not null
    qualify row_number() over (partition by email order by fan_id) = 1
)

select
    n.survey_id,
    n.game_id,
    f.fan_id,
    n.score,
    n.comment,
    n.is_anonymous
from {{ ref('stg_nps_surveys') }} n
left join fan_by_email f
    on n.respondent_email = f.email
