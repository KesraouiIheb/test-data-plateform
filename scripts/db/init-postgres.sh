#!/bin/bash
set -euo pipefail

# Usage: INGEST_PASSWORD=strongpass ./init-postgres.sh
PASSWORD=${INGEST_PASSWORD:-changeme}

psql -v ON_ERROR_STOP=1 <<EOSQL
CREATE USER ingest_user WITH PASSWORD '${PASSWORD}';
CREATE DATABASE ingest OWNER ingest_user;
GRANT ALL PRIVILEGES ON DATABASE ingest TO ingest_user;
EOSQL
