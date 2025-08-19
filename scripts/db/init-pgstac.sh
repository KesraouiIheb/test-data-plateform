#!/bin/bash
set -euo pipefail

# Usage: PGSTAC_PASSWORD=strongpass ./init-pgstac.sh
PASSWORD=${PGSTAC_PASSWORD:-changeme}

psql -v ON_ERROR_STOP=1 <<EOSQL
CREATE USER pgstac_user WITH PASSWORD '${PASSWORD}';
CREATE DATABASE pgstac OWNER pgstac_user;
EOSQL

psql -d pgstac -c "CREATE EXTENSION IF NOT EXISTS postgis;"

if [ ! -f pgstac.sql.gz ]; then
  wget https://github.com/stac-utils/pgstac/releases/latest/download/pgstac.sql.gz
fi
gunzip -c pgstac.sql.gz | psql -d pgstac
