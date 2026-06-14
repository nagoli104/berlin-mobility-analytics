# Dashboard

The local Metabase dashboard is seeded from `scripts/metabase_seed.sh`.

The seed creates:

- collection: `Mobility Analytics`
- dashboard: `Mobility Overview`
- saved questions built on `analytics.fact_mobility_weather`

---

## Open the dashboard

Start the local stack:

    docker compose --env-file .env -f docker/docker-compose.yml up -d

Open Metabase:

    http://localhost:3000

Log in with the Metabase credentials from `.env`:

- `METABASE_SETUP_EMAIL`
- `METABASE_SETUP_PASSWORD`

Navigate to:

    Our analytics -> Mobility Analytics -> Mobility Overview

---

## Refresh the dashboard seed

The dashboard depends on the dbt mart `analytics.fact_mobility_weather`.

After running the Airflow pipeline or rebuilding dbt models, refresh Metabase metadata and the seeded dashboard with:

    docker compose --env-file .env -f docker/docker-compose.yml run --rm metabase-seed

The seed is intended to be idempotent. It updates the existing collection, saved questions, dashboard, layout, and mart metadata instead of creating duplicate active dashboard cards.

---

## Current cards

### Daily Bike Counts

Shows total bike counts per observation date.

Use this to inspect overall volume patterns and gaps in the loaded time range.

### Bike Counts by Hour

Shows total bike counts by Berlin-local hour of day.

Use this to inspect the daily usage pattern. It currently combines weekdays and weekends.

### Top Stations by Bike Count

Shows the highest-volume counting stations by total bike count.

The station label uses `station_description` when available and falls back to `station_id`.

### Bike Counts by Rain Intensity

Shows average hourly bike counts by precipitation bucket.

The card aggregates station rows to hourly totals first, then groups hours into:

- `0 None`: no precipitation
- `1 Trace`: precipitation below `0.5`
- `2 Light`: precipitation from `0.5` up to below `2`
- `3 Moderate+`: precipitation of `2` or more

This card is descriptive, not causal. It does not yet control for weekday/weekend, hour of day, season, or station mix. Trace rain can behave differently from meaningful rain, so it is intentionally separated from stronger precipitation.

---

## Known next improvements

- Add normalized wet-vs-dry comparisons by hour of day and weekday/weekend.
- Add date filters once the dashboard has more history loaded.
- Add a station activity mart for cleaner map and station-level cards.
- Add station point-map visualizations using latitude and longitude.
