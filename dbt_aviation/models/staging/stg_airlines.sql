select
    airline_id,
    nullif(upper(trim(iata_code)), '') as iata_code,
    nullif(upper(trim(icao_code)), '') as icao_code,
    trim(name)                         as airline_name
from {{ source('airlabs', 'airlines') }}
