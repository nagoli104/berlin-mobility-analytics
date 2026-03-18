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
import psycopg2

conn = psycopg2.connect(
    host="postgres",
    port=5432,
    dbname="metabase",
    user="airflow",
    password="airflow",
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
DB_EXISTS=$(curl -sSf -H "X-Metabase-Session: $SESSION" "$METABASE_URL/api/database" \
  | python -c 'import sys, json; payload=json.load(sys.stdin); items=payload.get("data", payload); print(any(db.get("name")=="mobility" for db in items))')

if [ "$DB_EXISTS" = "True" ]; then
  echo "Datasource 'mobility' already exists. Skipping creation."
else
  echo "Adding mobility datasource..."
  curl -sSf -X POST "$METABASE_URL/api/database" \
    -H "Content-Type: application/json" \
    -H "X-Metabase-Session: $SESSION" \
    -d '{
      "name":"mobility",
      "engine":"postgres",
      "details":{
        "host":"postgres",
        "port":5432,
        "dbname":"mobility",
        "user":"airflow",
        "password":"airflow",
        "ssl":false
      }
    }' >/dev/null
  echo "Datasource added."
fi

echo "Metabase setup finished."