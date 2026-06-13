# Data Model

## Modeling scope

The current project state consists of two raw extraction pipelines:

- a bike-count extraction that exports long-format hourly mobility data and station metadata
- a weather extraction that exports hourly historical weather data from Open-Meteo

This document describes the resulting data entities and their intended analytical interpretation.

---

## Current extraction outputs

### Mobility outputs

The mobility extraction currently produces two CSV files:

- `mobility_long.csv`
- `mobility_metadata.csv`

#### mobility_long.csv
This dataset contains hourly bike count observations in long format.

Current fields:
- `observed_at`
- `station_id`
- `bike_count`

Transformation logic:
- yearly Excel sheets are selected by name in the form `Jahresdatei <year>`
- station headers are cleaned so that only the station code remains
- the source table is reshaped from wide to long format using `melt`
- rows with missing `bike_count` are removed
- `observed_at` is parsed as datetime

#### mobility_metadata.csv
This dataset contains station metadata extracted from the `Standortdaten` sheet.

Current fields:
- `station_id`
- `description`
- `latitude`
- `longitude`
- `installed`
- `direction`

Transformation logic:
- station metadata is loaded from the dedicated metadata sheet
- `installed` is parsed as datetime
- `direction` is derived from the station description if it ends with:
  - `West`
  - `Ost`
  - `Nord`
  - `Süd`

---

### Weather output

The weather extraction currently produces one CSV file per script run.

Current fields:
- `date`
- selected hourly weather variables
- `weather_description` if `weather_code` is requested

Default hourly variables:
- `temperature_2m`
- `apparent_temperature`
- `precipitation`
- `weather_code`
- `cloud_cover`
- `wind_speed_10m`
- `relative_humidity_2m`
- `wind_gusts_10m`

Transformation logic:
- the script requests historical hourly weather data for one coordinate pair
- timestamps are generated from the API response interval
- timestamps are converted from UTC to the configured timezone
- `weather_code` is cast to nullable integer and mapped to `weather_description`

---

## Current model state

The project currently contains an implemented extraction layer that already defines the core analytical entities.

The current exported datasets can be understood as:

- `mobility_long.csv` → proto-`fact_mobility`
- `mobility_metadata.csv` → proto-`dim_station`
- weather export CSV → proto-`fact_weather_hourly`

These files are not yet warehouse tables, but they already establish the analytical grain, keys, and field structure of the model.

---

## Mobility model

## dim_station

### Purpose
Represents the metadata of each counting station.

### Primary key
- `station_id`

### Current fields
- `station_id`
- `description`
- `latitude`
- `longitude`
- `installed`
- `direction`

### Notes
- `station_id` is treated as the stable identifier of the measurement unit
- station direction is currently inferred from the description text
- stations without directional suffix remain valid single stations
- the metadata table is extracted directly from the source workbook and is suitable as the basis for a future station dimension

---

## fact_mobility

### Purpose
Stores hourly observed bike counts per station.

### Current grain
- one row per station and hour

### Natural key
- `observed_at + station_id`

### Current fields
- `observed_at`
- `station_id`
- `bike_count`

### Notes
- source sheets are stored in wide format and reshaped to long format
- only rows with actual measurements are retained
- missing values are dropped after reshaping
- the current fact representation contains only observed measurements, not a complete station-time grid

### Interpretation of missingness
The current extraction logic excludes rows where `bike_count` is missing.

This is consistent with the modeling decision that the fact table should initially contain only measurements that actually exist.

This avoids conflating different meanings of missingness, such as:
- station not yet installed
- technical measurement outage
- incomplete source delivery
- true zero measurement

---

## Weather model

## fact_weather_hourly

### Purpose
Stores hourly historical weather observations for one requested location.

### Current grain
- one row per hour and weather coordinate pair

### Natural key
- `date` plus the coordinate context of the extraction run

### Current fields
At minimum:
- `date`
- requested hourly weather variables

By default:
- `temperature_2m`
- `apparent_temperature`
- `precipitation`
- `weather_code`
- `cloud_cover`
- `wind_speed_10m`
- `relative_humidity_2m`
- `wind_gusts_10m`
- `weather_description`

### Notes
- the current script is parameterized by latitude and longitude
- one run corresponds to one weather location
- timestamps are localized to the configured timezone, currently `Europe/Berlin`
- weather code descriptions are normalized into a human-readable field

---

## Integrated analytical model

## fact_mobility_weather

### Purpose
Represents an integrated analytical table for dashboarding and exploratory analysis.

### Planned grain
- one row per station and hour

### Planned join logic
- mobility observations are joined to hourly weather observations on timestamp
- spatial integration depends on the selected weather location strategy

### Spatial interpretation
Two possible spatial interpretations exist:

#### One shared Berlin weather series
- simple and analytically sufficient for a first integrated model
- all stations share the same hourly weather observations

#### Station-level weather extraction
- weather observations are tied directly to station coordinates
- this provides finer spatial realism but requires a more granular extraction strategy

---

## Data quality considerations

### Mobility data
Observed source characteristics:
- yearly sheets start at January 1st 00:00
- some earlier years contain only one station
- some rows may contain no measurement values across all stations
- station headers contain both station code and commissioning date
- color formatting in the Excel workbook may signal questionable measurements

Current implementation status:
- commissioning date in the count-sheet headers is ignored during extraction
- missing count values are dropped
- Excel formatting-based quality flags are not extracted

### Weather data
Current safeguards:
- retry-enabled HTTP requests
- local caching via `requests_cache`
- failure if the API returns no response
- deterministic weather code mapping

---

## Suggested warehouse interpretation

The current extraction outputs already map naturally to a simple analytical warehouse structure.

### Station entity
Derived from `mobility_metadata.csv`:
- `station_id`
- `description`
- `latitude`
- `longitude`
- `installed`
- `direction`

### Mobility observation entity
Derived from `mobility_long.csv`:
- `observed_at`
- `station_id`
- `bike_count`

### Weather observation entity
Derived from the Open-Meteo export:
- `date`
- selected hourly weather variables
- `weather_description`

### Integrated analytical entity
A combined hourly table can be formed from:
- station-level mobility observations
- hourly weather observations
- optional station metadata enrichment

---

## Current limitations

- the bike extraction script does not yet extract Excel formatting-based quality flags
- the weather extraction script operates on a single coordinate pair per run
- no explicit station activation filter is currently applied using `installed`
- no quality flag is derived from Excel formatting
- no final dbt schema has yet been implemented on top of the extracted CSVs

---

## Summary

The current project already establishes the essential analytical entities:

- a long-format hourly bike-count table
- a station metadata table
- a timezone-adjusted hourly weather table

Together, these datasets define the current analytical foundation of the project.
