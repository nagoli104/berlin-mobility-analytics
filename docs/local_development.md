## Local Development

This project uses Docker Compose to run:

- PostgreSQL (Airflow metadata, Metabase application storage, analytics database)
- Apache Airflow (webserver + scheduler)
- Metabase (BI dashboard)

All services are configured via a `.env` file located in the project root.

---

### 1️⃣ Environment Setup

Create a project-local Python environment with `uv`:

    uv sync

Run host-side extraction scripts through that environment:

    uv run python scripts/bike_data_extraction.py --help
    uv run python scripts/openmeteo_weather_export.py --help

Airflow runs in Docker. If you need to import-check Airflow DAGs on the host, install the optional Airflow dependency group:

    uv sync --group airflow

Create a local `.env` file based on `.env.example`:

    cp .env.example .env

Adjust values if needed.

If `.env` already exists from an earlier project version, add any new variables from `.env.example`, especially `AIRFLOW_DB`, `METABASE_DB`, and `MOBILITY_DB`.

⚠️ The `.env` file is not committed to the repository.

---

### 2️⃣ First-Time Bootstrap (Airflow Metadata Initialization)

On first startup, initialize the Airflow metadata database and create the admin user:

    docker compose --env-file .env -f docker/docker-compose.yml up airflow-init

Wait until the container exits with:

    Exited (0)

This step:
- Migrates the Airflow metadata database
- Creates the Admin user

PostgreSQL initializes three local databases on first volume creation:

- `airflow` for Airflow metadata
- `metabase` for Metabase application state
- `mobility` for analytics data

If you already created the Postgres volume before these databases existed, recreate the local volume:

    docker compose --env-file .env -f docker/docker-compose.yml down -v

---

### 3️⃣ Start All Services

    docker compose --env-file .env -f docker/docker-compose.yml up -d

Verify running containers:

    docker ps

---

### 4️⃣ Access the Services

| Service    | URL                     |
|------------|-------------------------|
| Airflow UI | http://localhost:8080   |
| Metabase   | http://localhost:3000   |
| Postgres   | localhost:5432          |

Airflow login credentials are defined in `.env`.

---

### 5️⃣ PostgreSQL Quick Verification

Connect to the database:

    docker exec -it mobility_postgres psql -U ${POSTGRES_USER} -d ${MOBILITY_DB}

Check connection:

    \conninfo

Test persistence:

    CREATE TABLE test_table (id INT);

Restart services:

    docker compose --env-file .env -f docker/docker-compose.yml down
    docker compose --env-file .env -f docker/docker-compose.yml up -d postgres

Reconnect and verify:

    \dt

The table should still exist, confirming volume persistence.

---

### 6️⃣ Stop Services

    docker compose --env-file .env -f docker/docker-compose.yml down

To remove volumes (⚠️ deletes database data):

    docker compose --env-file .env -f docker/docker-compose.yml down -v

---

## Project Architecture (Local)

Host (Mac)
│
├─ Port 8080 → Airflow Webserver
├─ Port 3000 → Metabase
├─ Port 5432 → PostgreSQL
│
└─ Docker Network (mobility_net)
    ├─ postgres
    ├─ airflow_webserver
    ├─ airflow_scheduler
    └─ metabase

Airflow connects internally to Postgres via the Docker network using the service name `postgres`.

---

## Notes

- Airflow metadata is stored in PostgreSQL.
- Airflow, Metabase, and analytics use separate PostgreSQL databases.
- `.env` variables are injected using `--env-file`.
- The `airflow-init` service is a one-time bootstrap container.
- This setup is intended for local development only.
