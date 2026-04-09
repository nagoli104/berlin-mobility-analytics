# Source Inspection

## Overview

The project currently uses two source systems:

- Berlin cycling count data provided as an Excel workbook
- historical weather data retrieved from the Open-Meteo archive API

These sources differ in both structure and access method:

- mobility data is file-based and semi-structured
- weather data is API-based and already close to tabular form

---

## Mobility source

### Source format

The mobility source is provided as an Excel workbook.

Observed structure:
- the workbook contains separate yearly sheets for hourly measurement data
- each yearly sheet starts at January 1st 00:00 of the respective year
- each row represents one hourly timestamp
- each station is represented as a separate column
- the workbook also contains a separate metadata sheet with station information

This means that the raw measurement data is stored in wide format.

### Temporal coverage

The workbook contains yearly data starting in 2012.

Observed structure by period:
- years 2012 to 2014 contain only a single station
- later years contain a broader and more stable station network

For the current analytical scope, the more consistent multi-station period is the relevant part of the source.

### Station column headers

The hourly measurement columns use headers of the following form:

```text
01-MI-AL-W
16.12.2021
```

Observed interpretation:
- first line: station identifier
- second line: station commissioning date

For analytical use, only the station identifier is required in the measurement table.  
The commissioning date is already available in the station metadata table and does not need to be duplicated from the sheet headers.

### Station metadata

The workbook contains a separate legend-style metadata table.

Observed metadata fields:
- `station_id`
- `description`
- `latitude`
- `longitude`
- `installed`

The current extraction additionally derives:

- `direction`

from directional suffixes in the station description:
- `West`
- `Ost`
- `Nord`
- `Süd`

### Directionality

The source contains both:
- stations that appear as directional pairs
- stations that appear as a single measurement point

Examples of directional patterns include suffixes such as:
- `-N`
- `-S`
- `-O`
- `-W`

This indicates that the most stable analytical unit in the source is the individual station identifier, not an already aggregated site concept.

### Data layout implications

The raw mobility source is not directly suitable for SQL-based analysis or dashboarding because the station identifiers are encoded as column headers.

The source must therefore be reshaped from:

- one row per hour with many station columns

to:

- one row per hour and station

This reshaping step is central to the mobility extraction logic.

---

## Mobility missingness and quality characteristics

### Structural absence

Not all missing values represent data quality issues.

A substantial portion of missingness is structurally explained by station rollout over time:
- some stations were installed only during the course of a year
- earlier timestamps before station activation therefore do not represent missing measurements in the analytical sense

### Technical missingness

The source also contains observations that appear to reflect technical or source-side issues.

Observed example:
- in the 2025 data, at least one row contains no measurements across all stations

This kind of case differs conceptually from:
- station not yet active
- true zero measurement

### Formatting-based quality indicators

The workbook uses cell formatting to visually indicate periods where measurements may be faulty.

Observed characteristic:
- quality information is represented through Excel formatting
- the quality annotations are not provided as explicit tabular fields

This means the source contains quality information that is visible to a human reader but not yet directly accessible through a simple `read_excel()` workflow.

### Current extraction interpretation

The current extraction keeps only rows where `bike_count` is present after reshaping.

This results in:
- a fact-like mobility table containing only observed measurements
- no materialization of empty station-hour combinations
- no automated extraction of formatting-based quality flags

---

## Weather source

### Source format

The weather source is retrieved from the Open-Meteo archive API.

Observed characteristics:
- API-based access
- one coordinate pair per request
- hourly time series output
- structured response that is already close to tabular format

Compared with the mobility source, the weather source is significantly more regular and easier to normalize.

### Requested variables

The current extraction supports arbitrary hourly variables, with a default set consisting of:

- `temperature_2m`
- `apparent_temperature`
- `precipitation`
- `weather_code`
- `cloud_cover`
- `wind_speed_10m`
- `relative_humidity_2m`
- `wind_gusts_10m`

### Time handling

The raw API response uses UTC-based timestamps and interval metadata.

The extraction converts timestamps to the configured local timezone, currently:
- `Europe/Berlin`

This is an important normalization step for later integration with hourly mobility observations.

### Weather code handling

If `weather_code` is requested, the script maps numeric weather codes to human-readable categories.

This introduces a first semantic normalization layer directly in the extraction output.

---

## Source comparison

### Mobility source
Characteristics:
- file-based
- yearly partitioning through Excel sheets
- wide format
- embedded metadata in headers
- additional metadata table
- formatting-based quality annotations
- semi-structured

### Weather source
Characteristics:
- API-based
- request-based temporal scope
- long/tabular output
- explicit variables
- no formatting-based ambiguity
- structurally regular

---

## Analytical relevance

The inspected source structures imply three core analytical entities:

### Station entity
Derived from the metadata sheet of the mobility workbook.

Relevant fields:
- `station_id`
- `description`
- `latitude`
- `longitude`
- `installed`
- `direction`

### Mobility observation entity
Derived from the reshaped yearly measurement sheets.

Relevant fields:
- `observed_at`
- `station_id`
- `bike_count`

### Weather observation entity
Derived from the Open-Meteo API export.

Relevant fields:
- `date`
- hourly weather variables
- `weather_description`

These three entities define the current source-side basis for the analytical model.

---

## Current source-level limitations

### Mobility source
- yearly data is embedded in Excel sheets rather than provided as a normalized table
- station quality annotations are encoded in formatting rather than columns
- station rollout over time introduces structurally incomplete coverage
- source headers contain mixed information (identifier plus commissioning date)

### Weather source
- each extraction run covers only one coordinate pair
- spatial interpretation depends on the chosen weather location strategy
- the weather source is structurally clean, but spatial alignment with stations remains an analytical decision rather than a source property

---

## Summary

The source inspection shows a clear contrast between the two source systems:

- the mobility source is structurally rich but requires substantial normalization
- the weather source is structurally simple and already close to analytical use

The current extraction layer resolves the most important source-side normalization tasks by:
- turning hourly bike counts into long format
- separating station metadata into its own table
- converting weather timestamps to local time
- enriching weather codes with human-readable descriptions

These source characteristics define the current analytical foundation of the project.