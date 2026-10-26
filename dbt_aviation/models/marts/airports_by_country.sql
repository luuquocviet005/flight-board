-- How many airports each country has, and how many carry IATA / ICAO codes.
select
    country_code,
    count(*)                 as total_airports,
    count(iata_code)         as with_iata_code,
    count(icao_code)         as with_icao_code,
    round(100.0 * count(iata_code) / count(*), 1) as pct_with_iata
from {{ ref('stg_airports') }}
where country_code is not null
group by country_code
order by total_airports desc
