-- Vietnamese airports that have an IATA code (i.e. serve commercial flights: SGN, HAN, DAD, ...).
-- Real airports also have an ICAO code; rows without one are junk (e.g. a spam "XHG" casino entry).
select
    iata_code,
    icao_code,
    airport_name,
    latitude,
    longitude
from {{ ref('stg_airports') }}
where country_code = 'VN'
  and iata_code is not null
  and icao_code is not null
order by iata_code
