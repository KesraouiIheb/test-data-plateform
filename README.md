# Data Platform Infrastructure

This repository provisions a managed PostgreSQL service on **Google Cloud SQL** and exposes it to Metaflow workloads running on **GKE**.  The setup enables the `pgSTAC` API and PostGIS extensions while keeping the database lifecycle independent from the Metaflow cluster.

## 1. Provision Cloud SQL with Terraform

The Terraform configuration in [`terraform/`](terraform) creates:

- A PostgreSQL 15 Cloud SQL instance with a `pgstac` database.
- A service account with the minimal roles required to access the instance (`roles/cloudsql.client`).
- Workload Identity bindings so a Kubernetes service account can authenticate as the Cloud SQL service account.
- PostGIS and `pgstac` extensions using the PostgreSQL provider.

### Usage

```bash
cd terraform
terraform init
terraform apply \
  -var project_id="<PROJECT_ID>" \
  -var region="<REGION>" \
  -var private_network="<VPC_SELF_LINK>" \
  -var db_password="<STRONG_PASSWORD>"
```

Outputs include the instance connection name and service account e‑mail used by GKE.

## 2. GKE access (Workload Identity + Auth Proxy)

[`terraform/kubernetes/cloudsql-auth-proxy.yaml`](terraform/kubernetes/cloudsql-auth-proxy.yaml) shows how to run a Metaflow task with the Cloud SQL Auth Proxy sidecar. Replace the placeholders (project, region, instance name, password, service account e‑mail) and deploy:

```bash
kubectl apply -f terraform/kubernetes/cloudsql-auth-proxy.yaml
```

The pod uses Workload Identity and connects to Cloud SQL over a local TCP port exposed by the proxy.

## 3. Metaflow configuration

[`configs/metaflow_gcp.yaml`](configs/metaflow_gcp.yaml) contains environment variables consumed by Metaflow flows. Set `PGSTAC_URI` to match your database credentials and ensure the file is loaded when launching flows:

```bash
export $(cat configs/metaflow_gcp.yaml | xargs)
python metaflow_flows/sentinel2_ingestion_flow.py run
```

## 4. Enable PostGIS and pgSTAC

The Terraform module installs the extensions automatically. If manual setup is preferred, connect with `psql` and run:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgstac;
```

## 5. Least‑privilege access

Only the dedicated service account created by Terraform has the `roles/cloudsql.client` permission. Kubernetes pods authenticate using Workload Identity with that account; no passwords or keys are stored in the cluster.

## 6. Performance & operations tips

- Choose an appropriate machine tier (`db-custom-*`) and enable automatic backups.
- Use connection pooling (e.g. `pgbouncer`) for high‑concurrency workloads.
- Monitor the instance with Cloud SQL insights and set up alerts for CPU, storage and connection metrics.

## 7. Developer workflow

Developers can iterate on Metaflow flows locally and then deploy to GKE:

```bash
# Run locally
python metaflow_flows/sentinel2_ingestion_flow.py run

# Execute on GKE (Metaflow CLI must be configured for GCP)
python metaflow_flows/sentinel2_ingestion_flow.py --with kubernetes run
```

## 8. Testing

A minimal smoke test prints a greeting:

```bash
python main.py
```

`pytest` can be executed even when no tests exist to validate the environment:

```bash
pytest
```

## 9. Self-hosted Postgres and pgSTAC VMs

An alternative to Cloud SQL is to run the databases on self-managed VMs. Terraform
configuration and bootstrap scripts live under [`terraform/postgres_vms/`](terraform/postgres_vms).

### Provision the VMs

```bash
cd terraform/postgres_vms
terraform init
terraform apply \
  -var project_id="<PROJECT_ID>"
```

Two compute instances are created with startup scripts that install PostgreSQL:

- **ingest-postgres** – standard PostgreSQL instance for ingestion flows.
- **pgstac-postgres** – PostgreSQL with PostGIS and the pgSTAC schema.

Passwords can be supplied via the `INGEST_PASSWORD` and `PGSTAC_PASSWORD`
metadata variables or by editing the shell scripts before apply.

### Database creation scripts

Standalone scripts in [`scripts/db`](scripts/db) show how to create the
databases and load `pgstac.sql.gz` manually if needed:

```bash
# On the Postgres VM
INGEST_PASSWORD=strongpass ./scripts/db/init-postgres.sh

# On the pgSTAC VM
PGSTAC_PASSWORD=strongpass ./scripts/db/init-pgstac.sh
```

### Connecting from Metaflow

Expose the connection strings as environment variables before running a flow:

```bash
export INGEST_DB_DSN="postgresql://ingest_user:<PASSWORD>@<INGEST_VM_IP>:5432/ingest"
export PGSTAC_DSN="postgresql://pgstac_user:<PASSWORD>@<PGSTAC_VM_IP>:5432/pgstac"
python metaflow_flows/sentinel2_ingestion_flow.py run
```

The `download_items` utility writes STAC metadata to pgSTAC when `PGSTAC_DSN`
is set. The flow's `write_to_db` step records processed items into the
`ingestion_log` table and prints row counts from both databases.

### Team access

Developers can connect using the VM's external IP addresses:

```bash
ssh <user>@<INGEST_VM_IP>
psql "$INGEST_DB_DSN"
# or
pgadmin4 --server "<PGSTAC_VM_IP>"
```

### Collaboration workflow

1. Create feature branches from `main`.
2. Commit Terraform and SQL/script changes.
3. Open pull requests for review before applying infrastructure changes.

### Verifying the setup

1. After provisioning, ensure `psql` connects to both VMs and lists databases.
2. Run `python metaflow_flows/sentinel2_ingestion_flow.py run` with the DSNs set.
   The flow prints counts from the ingestion and pgSTAC databases.
3. Query data manually, e.g.:

```sql
-- Ingestion database
SELECT * FROM ingestion_log LIMIT 5;

-- pgSTAC database
SELECT id FROM pgstac.collections;
```
