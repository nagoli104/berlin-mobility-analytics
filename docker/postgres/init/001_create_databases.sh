#!/usr/bin/env bash
set -euo pipefail

create_database() {
  local database="$1"

  psql \
    -v ON_ERROR_STOP=1 \
    --set=database="$database" \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" <<-'EOSQL'
SELECT format('CREATE DATABASE %I', :'database')
WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = :'database'
)
\gexec
EOSQL
}

create_database "${AIRFLOW_DB:-airflow}"
create_database "${METABASE_DB:-metabase}"
create_database "${MOBILITY_DB:-mobility}"
