#!/usr/bin/env bash
set -euo pipefail

METABASE_URL="http://metabase:3000"

echo "Waiting for Metabase..."
until curl -sSf "$METABASE_URL/api/health" >/dev/null; do
  sleep 2
done
echo "Metabase is ready."

echo "Checking whether a real admin user already exists..."
USER_COUNT=$(python - <<'PY'
import os

import psycopg2

conn = psycopg2.connect(
    host="postgres",
    port=5432,
    dbname=os.environ["METABASE_DB"],
    user=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
)
cur = conn.cursor()
cur.execute("""
    SELECT count(*)
    FROM core_user
    WHERE email <> 'internal@metabase.com'
""")
print(cur.fetchone()[0])
cur.close()
conn.close()
PY
)

if [ "$USER_COUNT" = "0" ]; then
  echo "No admin user found. Running initial setup..."
  curl -sSf -X POST "$METABASE_URL/api/setup" \
    -H "Content-Type: application/json" \
    -d "{
      \"token\":\"$MB_SETUP_TOKEN\",
      \"user\":{
        \"email\":\"$METABASE_SETUP_EMAIL\",
        \"password\":\"$METABASE_SETUP_PASSWORD\",
        \"first_name\":\"$METABASE_SETUP_FIRSTNAME\",
        \"last_name\":\"$METABASE_SETUP_LASTNAME\"
      },
      \"prefs\":{\"site_name\":\"Mobility Analytics\"}
    }" >/dev/null
  echo "Initial setup completed."
else
  echo "Admin user already exists. Skipping initial setup."
fi

echo "Creating session..."
SESSION=$(curl -sSf -X POST "$METABASE_URL/api/session" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$METABASE_SETUP_EMAIL\",\"password\":\"$METABASE_SETUP_PASSWORD\"}" \
  | python -c 'import sys, json; print(json.load(sys.stdin)["id"])')

test -n "$SESSION"
echo "Session created."

echo "Checking whether datasource 'mobility' already exists..."
MOBILITY_DB_ID=$(curl -sSf -H "X-Metabase-Session: $SESSION" "$METABASE_URL/api/database" \
  | python -c 'import sys, json; payload=json.load(sys.stdin); items=payload.get("data", payload); matches=[db for db in items if db.get("name")=="mobility"]; print(matches[0]["id"] if matches else "")')

if [ -n "$MOBILITY_DB_ID" ]; then
  echo "Datasource 'mobility' already exists. Skipping creation."
else
  echo "Adding mobility datasource..."
  DATASOURCE_PAYLOAD=$(python - <<'PY'
import json
import os

print(json.dumps({
    "name": "mobility",
    "engine": "postgres",
    "details": {
        "host": "postgres",
        "port": 5432,
        "dbname": os.environ["MOBILITY_DB"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
        "ssl": False,
    },
}))
PY
)
  curl -sSf -X POST "$METABASE_URL/api/database" \
    -H "Content-Type: application/json" \
    -H "X-Metabase-Session: $SESSION" \
    -d "$DATASOURCE_PAYLOAD" >/dev/null
  echo "Datasource added."

  MOBILITY_DB_ID=$(curl -sSf -H "X-Metabase-Session: $SESSION" "$METABASE_URL/api/database" \
    | python -c 'import sys, json; payload=json.load(sys.stdin); items=payload.get("data", payload); matches=[db for db in items if db.get("name")=="mobility"]; print(matches[0]["id"] if matches else "")')
fi

test -n "$MOBILITY_DB_ID"

echo "Syncing mobility datasource schema..."
curl -sSf -X POST "$METABASE_URL/api/database/$MOBILITY_DB_ID/sync_schema" \
  -H "Content-Type: application/json" \
  -H "X-Metabase-Session: $SESSION" \
  -d "{}" >/dev/null
echo "Schema sync requested."

echo "Configuring mart metadata if fact_mobility_weather exists..."
python - "$METABASE_URL" "$SESSION" "$MOBILITY_DB_ID" <<'PY'
import json
import sys
import time
import urllib.request


metabase_url = sys.argv[1]
session = sys.argv[2]
database_id = sys.argv[3]

TABLE_SCHEMA = "analytics"
TABLE_NAME = "fact_mobility_weather"

FIELD_METADATA = {
    "observed_at": {"display_name": "Observed At"},
    "observed_local_at": {"display_name": "Observed Local At"},
    "station_id": {"display_name": "Station ID", "semantic_type": "type/Category"},
    "bike_count": {"display_name": "Bike Count", "semantic_type": "type/Quantity"},
    "observed_date": {"display_name": "Observed Date"},
    "observed_hour": {"display_name": "Observed Hour"},
    "observed_isodow": {"display_name": "Observed ISO Day of Week"},
    "is_weekend": {"display_name": "Is Weekend"},
    "station_description": {"display_name": "Station Description", "semantic_type": "type/Description"},
    "station_latitude": {"display_name": "Station Latitude", "semantic_type": "type/Latitude"},
    "station_longitude": {"display_name": "Station Longitude", "semantic_type": "type/Longitude"},
    "station_installed_date": {"display_name": "Station Installed Date"},
    "station_direction": {"display_name": "Station Direction", "semantic_type": "type/Category"},
    "temperature_2m": {"display_name": "Temperature 2m", "semantic_type": "type/Quantity"},
    "apparent_temperature": {"display_name": "Apparent Temperature", "semantic_type": "type/Quantity"},
    "precipitation": {"display_name": "Precipitation", "semantic_type": "type/Quantity"},
    "weather_code": {"display_name": "Weather Code", "semantic_type": "type/Category"},
    "cloud_cover": {"display_name": "Cloud Cover", "semantic_type": "type/Quantity"},
    "wind_speed_10m": {"display_name": "Wind Speed 10m", "semantic_type": "type/Quantity"},
    "relative_humidity_2m": {"display_name": "Relative Humidity 2m", "semantic_type": "type/Quantity"},
    "wind_gusts_10m": {"display_name": "Wind Gusts 10m", "semantic_type": "type/Quantity"},
    "weather_description": {"display_name": "Weather Description", "semantic_type": "type/Description"},
}

COLLECTION_NAME = "Mobility Analytics"
DASHBOARD_NAME = "Mobility Overview"

CARDS = [
    {
        "name": "Daily Bike Counts",
        "description": "Total bike counts by observation date.",
        "display": "line",
        "query": """
            select
                observed_date,
                sum(bike_count) as bike_count
            from analytics.fact_mobility_weather
            group by observed_date
            order by observed_date
        """,
        "visualization_settings": {
            "graph.dimensions": ["observed_date"],
            "graph.metrics": ["bike_count"],
        },
    },
    {
        "name": "Bike Counts by Hour",
        "description": "Total bike counts by local hour of day.",
        "display": "bar",
        "query": """
            select
                observed_hour,
                sum(bike_count) as bike_count
            from analytics.fact_mobility_weather
            group by observed_hour
            order by observed_hour
        """,
        "visualization_settings": {
            "graph.dimensions": ["observed_hour"],
            "graph.metrics": ["bike_count"],
        },
    },
    {
        "name": "Top Stations by Bike Count",
        "description": "Highest-volume counting stations by total bike count.",
        "display": "bar",
        "query": """
            select
                coalesce(station_description, station_id) as station,
                sum(bike_count) as bike_count
            from analytics.fact_mobility_weather
            group by station
            order by bike_count desc
            limit 15
        """,
        "visualization_settings": {
            "graph.dimensions": ["station"],
            "graph.metrics": ["bike_count"],
        },
    },
    {
        "name": "Bike Counts by Weather",
        "description": "Average and total bike counts split by precipitation state.",
        "display": "bar",
        "query": """
            select
                case when precipitation > 0 then 'Wet' else 'Dry' end as precipitation_state,
                avg(bike_count) as avg_bike_count,
                sum(bike_count) as bike_count
            from analytics.fact_mobility_weather
            group by precipitation_state
            order by precipitation_state
        """,
        "visualization_settings": {
            "graph.dimensions": ["precipitation_state"],
            "graph.metrics": ["avg_bike_count", "bike_count"],
        },
    },
]

DASHCARD_LAYOUT = {
    "Daily Bike Counts": {"row": 0, "col": 0, "size_x": 12, "size_y": 8},
    "Bike Counts by Hour": {"row": 0, "col": 12, "size_x": 12, "size_y": 8},
    "Top Stations by Bike Count": {"row": 8, "col": 0, "size_x": 12, "size_y": 8},
    "Bike Counts by Weather": {"row": 8, "col": 12, "size_x": 12, "size_y": 8},
}


def api(path, payload=None, method=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{metabase_url}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-Metabase-Session": session,
        },
        method=method,
    )
    with urllib.request.urlopen(request) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else None


def find_table():
    metadata = api(f"/api/database/{database_id}/metadata")
    for table in metadata.get("tables", []):
        if table.get("schema") == TABLE_SCHEMA and table.get("name") == TABLE_NAME:
            return table
    return None


def normalize_sql(sql):
    return "\n".join(line.strip() for line in sql.strip().splitlines())


def find_collection():
    for collection in api("/api/collection"):
        if collection.get("name") == COLLECTION_NAME:
            return collection
    return None


def ensure_collection():
    collection = find_collection()
    if collection:
        return collection["id"]
    created = api(
        "/api/collection",
        {
            "name": COLLECTION_NAME,
            "description": "Saved questions and dashboards for the Berlin mobility analytics project.",
            "color": "#509EE3",
        },
        method="POST",
    )
    return created["id"]


def find_card(name, collection_id):
    payload = api("/api/card")
    for card in payload:
        if card.get("name") == name and card.get("collection_id") == collection_id:
            return card
    return None


def card_payload(card, collection_id):
    return {
        "name": card["name"],
        "description": card["description"],
        "display": card["display"],
        "collection_id": collection_id,
        "dataset_query": {
            "database": int(database_id),
            "type": "native",
            "native": {"query": normalize_sql(card["query"])},
        },
        "visualization_settings": card["visualization_settings"],
    }


def ensure_card(card, collection_id):
    existing = find_card(card["name"], collection_id)
    payload = card_payload(card, collection_id)
    if existing:
        api(f"/api/card/{existing['id']}", payload, method="PUT")
        return existing["id"]
    created = api("/api/card", payload, method="POST")
    return created["id"]


def find_dashboard(collection_id):
    for dashboard in api("/api/dashboard"):
        if dashboard.get("name") == DASHBOARD_NAME and dashboard.get("collection_id") == collection_id:
            return dashboard
    return None


def ensure_dashboard(collection_id):
    dashboard = find_dashboard(collection_id)
    if dashboard:
        dashboard_id = dashboard["id"]
        api(
            f"/api/dashboard/{dashboard_id}",
            {
                "name": DASHBOARD_NAME,
                "description": "First overview dashboard for Berlin bike counts and weather context.",
                "collection_id": collection_id,
            },
            method="PUT",
        )
        return dashboard_id
    created = api(
        "/api/dashboard",
        {
            "name": DASHBOARD_NAME,
            "description": "First overview dashboard for Berlin bike counts and weather context.",
            "collection_id": collection_id,
        },
        method="POST",
    )
    return created["id"]


def dashboard_card_payload(dashcard_id, card_id, card_name):
    layout = DASHCARD_LAYOUT[card_name]
    return {
        "id": dashcard_id,
        "card_id": card_id,
        "card": {"id": card_id},
        "parameter_mappings": [],
        "series": [],
        "size_x": layout["size_x"],
        "size_y": layout["size_y"],
        "row": layout["row"],
        "col": layout["col"],
    }


def ensure_dashboard_cards(dashboard_id, card_ids):
    dashboard = api(f"/api/dashboard/{dashboard_id}")
    existing_by_card_id = {}
    for dashcard in dashboard.get("dashcards", []):
        card_id = dashcard.get("card_id") or dashcard.get("card", {}).get("id")
        if card_id:
            existing_by_card_id[card_id] = dashcard

    dashcards = []
    next_temporary_id = -1
    for card_name, card_id in card_ids.items():
        existing = existing_by_card_id.get(card_id)
        if existing:
            dashcard_id = existing["id"]
        else:
            dashcard_id = next_temporary_id
            next_temporary_id -= 1
        dashcards.append(dashboard_card_payload(dashcard_id, card_id, card_name))

    api(
        f"/api/dashboard/{dashboard_id}",
        {
            "name": DASHBOARD_NAME,
            "description": "First overview dashboard for Berlin bike counts and weather context.",
            "collection_id": dashboard.get("collection_id"),
            "dashcards": dashcards,
            "tabs": dashboard.get("tabs", []),
        },
        method="PUT",
    )


table = None
for _ in range(15):
    table = find_table()
    if table:
        break
    time.sleep(2)

if not table:
    print("Mart analytics.fact_mobility_weather not found yet. Run dbt/Airflow and rerun this seed to apply metadata.")
    sys.exit(0)

table_id = table["id"]
api(
    f"/api/table/{table_id}",
    {
        "display_name": "Mobility Weather",
        "description": "Hourly bike counts enriched with station metadata and Berlin weather observations.",
    },
    method="PUT",
)

table_metadata = api(f"/api/table/{table_id}/query_metadata")
updated_fields = 0
for field in table_metadata.get("fields", []):
    field_update = FIELD_METADATA.get(field.get("name"))
    if not field_update:
        continue
    api(f"/api/field/{field['id']}", field_update, method="PUT")
    updated_fields += 1

print(f"Configured metadata for analytics.fact_mobility_weather ({updated_fields} fields).")

collection_id = ensure_collection()
card_ids = {}
for card in CARDS:
    card_ids[card["name"]] = ensure_card(card, collection_id)

dashboard_id = ensure_dashboard(collection_id)
ensure_dashboard_cards(dashboard_id, card_ids)

print(f"Seeded {len(card_ids)} saved questions and dashboard '{DASHBOARD_NAME}'.")
PY

echo "Metabase setup finished."
