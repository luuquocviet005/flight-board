with cleaned as (
    select
        airport_id,
        nullif(upper(trim(iata_code)), '')    as iata_code,
        nullif(upper(trim(icao_code)), '')    as icao_code,
        trim(name)                            as airport_name,
        nullif(upper(trim(country_code)), '') as country_code,
        latitude,
        longitude
    from {{ source('airlabs', 'airports') }}
)

-- AirLabs contains exact duplicate rows (e.g. THD Tho Xuan twice): keep the first one.
select distinct on (iata_code, icao_code, airport_name) *
from cleaned
order by iata_code, icao_code, airport_name, airport_id
