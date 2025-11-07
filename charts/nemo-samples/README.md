# NeMo Samples Helm Chart

A Helm chart for deploying NVIDIA NeMo microservices samples - example deployments that demonstrate how to use the NeMo infrastructure.

## Overview

This chart deploys 7 custom resources that represent example NeMo microservices:
- **NemoCustomizer**: Fine-tuning and model customization service
- **NemoDatastore**: Data management and storage service
- **NemoEntitystore**: Entity and model metadata management
- **NemoEvaluator**: Model evaluation and benchmarking service
- **NemoGuardrail**: Safety and content filtering service
- **NIMCache**: Model caching (meta-llama3-1b-instruct)
- **NIMPipeline**: Inference pipeline for Llama 3.2 1B model

## Prerequisites

### 1. Infrastructure and Operators

1. **Infrastructure must be deployed**: The `nemo-infra` chart must be installed first
2. **Operators must be running**: Both NeMo Operator and NIM Operator must be installed

### 2. Required Secrets (Must be created BEFORE installation)

Following quickstart Step 1.3 (lines 37-53), create these secrets:

#### NGC Secrets (Required)
```bash
export NGC_API_KEY="<YOUR_NGC_API_KEY>"

# NGC Image Pull Secret (for pulling images)
oc create secret docker-registry ngc-secret \
  --docker-server=nvcr.io \
  --docker-username='$oauthtoken' \
  --docker-password=$NGC_API_KEY \
  -n <namespace>

# NGC API Secret (for model downloads)
oc create secret generic ngc-api-secret \
  --from-literal=NGC_API_KEY=$NGC_API_KEY \
  -n <namespace>
```

#### PostgreSQL Secrets (Required)
These secrets contain the PostgreSQL passwords matching your infrastructure deployment:

```bash
# Get passwords from infrastructure PostgreSQL secrets
# Then create the required secrets:

# Customizer PostgreSQL
oc create secret generic customizer-pg-existing-secret \
  --from-literal=password=<customizer-postgresql-password> \
  -n <namespace>

# Datastore PostgreSQL
oc create secret generic datastore-pg-existing-secret \
  --from-literal=password=<datastore-postgresql-password> \
  -n <namespace>

# Entity Store PostgreSQL
oc create secret generic entity-store-pg-existing-secret \
  --from-literal=password=<entity-store-postgresql-password> \
  -n <namespace>

# Evaluator PostgreSQL
oc create secret generic evaluator-pg-existing-secret \
  --from-literal=password=<evaluator-postgresql-password> \
  -n <namespace>

# Guardrail PostgreSQL
oc create secret generic guardrail-pg-existing-secret \
  --from-literal=password=<guardrail-postgresql-password> \
  -n <namespace>
```

**Note**: The passwords should match the values in `nemo-infra/values.yaml`:
- Customizer: `ncspassword`
- Datastore: `ndspass`
- Entity Store: `nespass`
- Evaluator: `evalpass`
- Guardrail: `guardrailpass`

#### Datastore Secrets (Automatically Created)

**IMPORTANT**: The datastore secrets are **automatically created** by the Helm chart. You do NOT need to create them manually.

The following secrets are created automatically when `datastore.enabled: true`:
- `nemo-ms-nemo-datastore` - Datastore configuration scripts
- `nemo-ms-nemo-datastore-init` - Init container scripts (init_directory_structure.sh, configure_gitea.sh, etc.)
- `nemo-ms-nemo-datastore-inline-config` - Gitea inline configuration
- `gitea-admin-credentials` - Gitea admin user credentials (configurable via `datastore.gitea.*`)
- `nemo-ms-nemo-datastore--lfs-jwt` - LFS JWT secret (configurable via `datastore.lfsJwtSecret`)

These secrets are created from the `datastore-secrets.yaml` template.

**Security Note**: Default credentials are provided for **development/testing only** (matching quickstart defaults). These are exposed in `values.yaml` for convenience but **MUST be overridden for production**:

```bash
# For production: Override via --set flags
export GITEA_ADMIN_PASSWORD="$(openssl rand -base64 32)"
export LFS_JWT_SECRET="$(openssl rand -base64 32 | base64)"

helm install nemo-samples ./charts/nemo-samples \
  -n arhkp-nemo-helm \
  --set datastore.gitea.adminPassword=$GITEA_ADMIN_PASSWORD \
  --set datastore.lfsJwtSecret=$LFS_JWT_SECRET
```

**⚠️ WARNING**: Do NOT use default credentials in production environments!

#### Optional Secrets

```bash
# Weights & Biases (optional, for Customizer)
oc create secret generic wandb-secret \
  --from-literal=apiKey=<wandb-api-key> \
  --from-literal=encryptionKey=<encryption-key> \
  -n <namespace>
```

### 3. Required ConfigMaps (For NemoCustomizer)

**IMPORTANT**: The `nemo-training-config` ConfigMap is **automatically created** by the Helm chart with the correct configuration.

**Manual ConfigMap (Required):**
```bash
# Model configuration ConfigMap (must be created manually)
# See quickstart Step 3 (lines 1257-1332) for the complete configuration
oc create configmap nemo-model-config \
  --from-file=<model-config-file> \
  -n <namespace>
```

**Note**: The `nemo-training-config` ConfigMap is created automatically by the chart with the correct YAML structure. You do NOT need to create it manually.

## Quick Start

**IMPORTANT**: Ensure all prerequisites (secrets and configmaps) are created before installation.

```bash
# Install samples
helm install nemo-samples ./charts/nemo-samples \
  -n arhkp-nemo-helm \
  --set namespace.name=arhkp-nemo-helm
```

**Expected**: 7 custom resources created (matches quickstart Step 6, line 164)

## Configuration

### Namespace

```yaml
namespace:
  name: arhkp-nemo-helm  # Must match your infrastructure namespace
```

### Enable/Disable Components

```yaml
customizer:
  enabled: true
datastore:
  enabled: true
entitystore:
  enabled: true
evaluator:
  enabled: true
guardrail:
  enabled: true
nimCache:
  enabled: true
nimPipeline:
  enabled: true
```

## Images (Exact from Quickstart)

All images match the quickstart exactly:

- **NemoCustomizer**: `nvcr.io/nvidia/nemo-microservices/customizer-api:25.08`
- **NemoDatastore**: `nvcr.io/nvidia/nemo-microservices/datastore:25.08`
- **NemoEntitystore**: `nvcr.io/nvidia/nemo-microservices/entity-store:25.08`
- **NemoEvaluator**: `nvcr.io/nvidia/nemo-microservices/evaluator:25.06`
- **NemoGuardrail**: `nvcr.io/nvidia/nemo-microservices/guardrails:25.08`
- **NIMCache**: `nvcr.io/nim/meta/llama-3.2-1b-instruct:1.8.3`
- **NIMPipeline**: `nvcr.io/nim/meta/llama-3.2-1b-instruct:1.8.3`

## Service Endpoints

After deployment, services are available at:

- `http://nemocustomizer-sample.<namespace>.svc.cluster.local:8000`
- `http://nemodatastore-sample.<namespace>.svc.cluster.local:8000`
- `http://nemoentitystore-sample.<namespace>.svc.cluster.local:8000`
- `http://nemoevaluator-sample.<namespace>.svc.cluster.local:8000`
- `http://nemoguardrails-sample.<namespace>.svc.cluster.local:8000`
- `http://meta-llama3-1b-instruct.<namespace>.svc.cluster.local:8000`

## GPU Requirements

- **NIMCache** and **NIMPipeline** require GPU nodes
- GPU tolerations are pre-configured for:
  - `g5-gpu` taint
  - `nvidia.com/gpu` taint

## Storage

Default PVC sizes:
- Customizer model PVC: 50Gi
- Customizer workspace PVC: 10Gi
- Datastore PVC: 10Gi
- Guardrail config PVC: 1Gi
- NIMCache PVC: 50Gi

## Verification

```bash
# Check all NeMo microservices
oc get -n <namespace> nemoentitystore,nemodatastore,nemoguardrails,nemocustomizer,nemoevaluator

# Check NIM services
oc get -n <namespace> nimpipeline,nimcache,nimservice

# Expected: All services showing STATUS: Ready
```

## Notes

- This chart follows the quickstart Step 6 exactly (lines 152-164)
- All namespace references are automatically templated
- Service hostnames are automatically updated to match namespace
- GPU tolerations are pre-configured for common OpenShift setups

