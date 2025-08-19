#!/bin/bash
set -euxo pipefail

# Install PostgreSQL, PostGIS and pgSTAC dependencies
apt-get update
apt-get install -y postgresql postgresql-contrib postgis wget

PGSTAC_PASSWORD=${PGSTAC_PASSWORD:-changeme}

# Create database and user
sudo -u postgres psql <<EOSQL
CREATE USER pgstac_user WITH PASSWORD '${PGSTAC_PASSWORD}';
CREATE DATABASE pgstac OWNER pgstac_user;
EOSQL

# Enable PostGIS extension
sudo -u postgres psql -d pgstac -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Load pgSTAC schema
wget -q https://github.com/stac-utils/pgstac/releases/latest/download/pgstac.sql.gz -O /tmp/pgstac.sql.gz
gunzip -c /tmp/pgstac.sql.gz | sudo -u postgres psql -d pgstac
