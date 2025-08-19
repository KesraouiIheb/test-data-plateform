# Data Platform Infrastructure

This repository provisions two self-hosted PostgreSQL databases on Google Cloud Compute Engine and shows how Metaflow flows can interact with them.

## 1. Provision Postgres VMs

Prerequisites:
- [gcloud CLI](https://cloud.google.com/sdk/docs/install)
- [Terraform](https://developer.hashicorp.com/terraform/install)
- `gcloud auth login`
- `gcloud config set project <PROJECT_ID>`

Enable the Compute Engine API:

```bash
gcloud services enable compute.googleapis.com
```

Provision the VMs:

```bash
cd terraform/postgres_vms
terraform init
terraform apply \
  -var project_id="<PROJECT_ID>" \
  -var region="us-central1" \
  -var zone="us-central1-a"
```

After apply completes, capture the IP addresses:

```bash
terraform output -raw ingest_ip
terraform output -raw pgstac_ip
```

## 2. Database setup

Startup scripts create the databases and users automatically. To rerun them or change passwords:

```bash
# Ingestion database
 gcloud compute scp scripts/db/init-postgres.sh ingest-postgres: --zone us-central1-a
 gcloud compute ssh ingest-postgres --zone us-central1-a -- \
   'INGEST_PASSWORD=strongpass bash init-postgres.sh'

# pgSTAC database
 gcloud compute scp scripts/db/init-pgstac.sh pgstac-postgres: --zone us-central1-a
 gcloud compute ssh pgstac-postgres --zone us-central1-a -- \
   'PGSTAC_PASSWORD=strongpass bash init-pgstac.sh'
```

## 3. Run Metaflow flows

Export connection strings and run the flow:

```bash
export INGEST_DB_DSN="postgresql://ingest_user:strongpass@$(terraform -chdir=terraform/postgres_vms output -raw ingest_ip):5432/ingest"
export PGSTAC_DSN="postgresql://pgstac_user:strongpass@$(terraform -chdir=terraform/postgres_vms output -raw pgstac_ip):5432/pgstac"

python metaflow_flows/sentinel2_ingestion_flow.py run
```

## 4. Accessing the VMs

```bash
# SSH
 gcloud compute ssh ingest-postgres --zone us-central1-a
 gcloud compute ssh pgstac-postgres --zone us-central1-a

# psql from your workstation
 psql "$INGEST_DB_DSN"
 psql "$PGSTAC_DSN"
```

## 5. Collaboration workflow

1. Create feature branches from `main`.
2. Commit Terraform, shell script, or Metaflow changes.
3. Open pull requests for review before applying infrastructure changes.

## 6. Verification

```bash
# Check databases
psql "$INGEST_DB_DSN" -c '\dt'
psql "$PGSTAC_DSN" -c 'SELECT count(*) FROM pgstac.collections;'

# Run flow and verify output
python metaflow_flows/sentinel2_ingestion_flow.py run
```

## 7. Testing

```bash
python main.py
pytest
```
