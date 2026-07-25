-- stg_ticketmaster_customers: normalizes name/email casing captured at checkout
-- so it can be reliably joined against stg_fans in int_fan_identity_map.

select
    ticketmaster_customer_id,
    trim(full_name) as full_name,
    lower(trim(email)) as email
from bronze_ticketmaster_customers
