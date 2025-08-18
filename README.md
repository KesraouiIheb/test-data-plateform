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
