#!/bin/bash
set -euxo pipefail

# Install PostgreSQL
apt-get update
apt-get install -y postgresql

# Create ingestion database and user
INGEST_PASSWORD=${INGEST_PASSWORD:-changeme}

sudo -u postgres psql <<EOSQL
CREATE USER ingest_user WITH PASSWORD '${INGEST_PASSWORD}';
CREATE DATABASE ingest OWNER ingest_user;
GRANT ALL PRIVILEGES ON DATABASE ingest TO ingest_user;
EOSQL
