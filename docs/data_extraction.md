## Data Extraction

The project currently uses two standalone extraction scripts:

- `bike_data_extraction.py`
- `openmeteo_weather_export.py`

Together, they produce the raw CSV inputs for later modeling steps in SQL/dbt and downstream analysis in Metabase.

---

## 1. Bike count extraction

### Purpose

This script downloads and reshapes the Berlin cycling count data from the official Excel workbook into a long-format table that is easier to use for analysis and modeling.

### Source

The script reads directly from the published Excel file:

- Berlin hourly cycling count workbook
- station metadata sheet contained in the same workbook

### Output

The script writes two CSV files:

- `mobility_long.csv`
- `mobility_metadata.csv`

### Transformation logic

#### Hourly count data
For the yearly count sheets, the script:

1. builds yearly sheet names in the form `Jahresdatei <year>`
2. reads each selected sheet from the Excel workbook
3. cleans station headers by removing the installation date suffix
4. reshapes the data from wide format to long format
5. keeps only rows with an actual measurement value
6. parses `observed_at` as datetime

This produces a long-format table with the following core fields:

- `observed_at`
- `station_id`
- `bike_count`

#### Station metadata
The script also reads the `Standortdaten` sheet and exports a station dimension-like table containing:

- `station_id`
- `description`
- `latitude`
- `longitude`
- `installed`
- `direction`

A simple direction derivation is currently applied based on whether the description ends in:

- `West`
- `Ost`
- `Nord`
- `Süd`

### Parameters

The script is implemented as a command-line tool with defaults matching the current 2025 extraction.

Common parameters:

- `--file-path`
- `--start-year`
- `--end-year`
- `--output-counts`
- `--output-metadata`

Example:

    uv run python scripts/bike_data_extraction.py \
      --start-year 2025 \
      --end-year 2025 \
      --output-counts data/mobility_long.csv \
      --output-metadata data/mobility_metadata.csv

### Notes

- The station column headers in the raw workbook contain both the station code and the station installation date.
- Only the station code is retained in the count table.
- Rows without observed counts are dropped after reshaping.
- The exported metadata table is intended to serve as the basis for `dim_station`.

---

## 2. Weather extraction

### Purpose

This script downloads historical hourly weather data from Open-Meteo and exports it as a flat CSV file for later integration with mobility observations.

### Source

The script uses the Open-Meteo archive API through the `openmeteo_requests` client.

### Parameters

The script is implemented as a command-line tool and expects:

- `--latitude`
- `--longitude`
- `--start-date`
- `--end-date`
- `--output`

Optional parameters include:

- `--timezone`
- `--cache-path`
- `--retries`
- `--backoff-factor`
- `--hourly`

### Default hourly variables

Unless overridden, the script requests the following hourly variables:

- `temperature_2m`
- `apparent_temperature`
- `precipitation`
- `weather_code`
- `cloud_cover`
- `wind_speed_10m`
- `relative_humidity_2m`
- `wind_gusts_10m`

### Transformation logic

The script:

1. creates a cached and retry-enabled API client
2. requests historical hourly weather data for the specified coordinates and date range
3. converts the API response into a pandas DataFrame
4. builds a timezone-aware hourly timestamp series
5. converts timestamps to the configured timezone
6. maps numeric `weather_code` values to human-readable descriptions
7. exports the result to CSV

### Output structure

The output includes:

- `date`
- requested hourly weather variables
- `weather_description` if `weather_code` is included

### Notes

- Timestamps are converted from UTC to the configured local timezone.
- The current default timezone is `Europe/Berlin`.
- The script is suitable for extracting weather data for one coordinate pair at a time.
- For later station-level weather modeling, it may either be reused per station or applied to a single representative Berlin coordinate in v1.

---

## 3. Modeling relevance

These two extraction scripts form the raw data layer of the project.

### Mobility side
The bike extraction script produces:

- a long-format observation table
- a station metadata table

This supports the later creation of:

- `fact_mobility`
- `dim_station`

### Weather side
The weather extraction script produces:

- a flat hourly weather table

This supports the later creation of:

- `fact_weather_hourly`

### Future integration
In a later step, both sources can be joined into a first integrated analytical table, for example:

- `fact_mobility_weather`

Possible join keys for v1:

- hourly timestamp
- optionally station/location context depending on the weather modeling strategy

---

## 4. Current limitations

- Excel formatting-based quality flags in the mobility workbook are not yet extracted.
- The weather extraction script currently operates on one coordinate pair per run.
- No schema validation or automated data quality checks are implemented yet.
- The extracted CSVs currently represent raw-to-staged outputs, not final analytical marts.

---

## 5. Planned next steps

- run bike extraction for the full intended year range
- define the first stable analytical grain for integrated mobility and weather data
- decide whether weather should be modeled:
  - at one Berlin-wide location
  - or at station level
- add data quality checks for:
  - invalid timestamps
  - duplicate station-hour rows
  - structurally missing vs technically missing observations
- implement dbt staging models on top of the exported CSVs
