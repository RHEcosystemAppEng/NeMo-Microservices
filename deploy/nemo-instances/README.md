# NeMo Instances Helm Chart

A Helm chart for creating and deploying NVIDIA NeMo microservices instances - example deployments that demonstrate how to use the NeMo infrastructure.

## Overview

This chart installs the NeMo and NIM operators, then deploys 7 custom resources that represent example NeMo microservices:

**Operators** (installed first):
- **NeMo Operator**: Kubernetes operator for managing NeMo microservices and training jobs
- **NIM Operator**: Kubernetes operator for managing NVIDIA NIM (NVIDIA Inference Microservices)

**NeMo Instances** (deployed after operators):
- **NemoCustomizer**: Fine-tuning and model customization service
- **NemoDatastore**: Data management and storage service
- **NemoEntitystore**: Entity and model metadata management
- **NemoEvaluator**: Model evaluation and benchmarking service
- **NemoGuardrail**: Safety and content filtering service
- **NIMCache**: Model caching for embedding model (nv-embedqa-1b-v2)
  - Note: Chat model caching is handled by RHOAI/OpenShift AI NIM Serving Runtime Model
- **NIMPipeline**: Inference pipeline for embedding model (nv-embedqa-1b-v2)
  - Note: Chat models (e.g., meta/llama-3.2-1b-instruct) are deployed via RHOAI/OpenShift AI NIM Serving Runtime Model (KServe InferenceService), not via Helm chart

## Prerequisites

📖 **Installation prerequisites**: See [main README](../../README.md#installation) for complete prerequisites and secret creation steps.

### Infrastructure Requirements

1. **Infrastructure must be deployed**: The `nemo-infra` chart must be installed first
2. **Volcano scheduler must be installed**: Required for NeMo Operator (installed via `nemo-infra` chart)

### Pre-Install Validation

**✅ Automatic Validation**: The Helm chart includes a pre-install hook that automatically validates all required secrets exist before proceeding with installation.

The validation hook checks:
- ✅ NGC secrets (`ngc-secret`, `ngc-api-secret`) - **REQUIRED**
- ✅ Infrastructure PostgreSQL secrets (for auto-creation) - Optional (falls back to defaults)
- ⚠️ Optional secrets (WandB) - Optional

**If validation fails**, Helm installation will stop with a clear error message showing which secrets are missing and how to create them.

### Required Secrets

#### PostgreSQL Secrets (Automatically Created)

**IMPORTANT**: PostgreSQL secrets are **automatically created** by the Helm chart. You do NOT need to create them manually.

The Helm chart automatically:
1. Reads passwords from infrastructure PostgreSQL secrets (`nemo-infra-*-postgresql`)
2. Creates the required `*-pg-existing-secret` secrets with the correct passwords
3. Falls back to defaults from `values.yaml` if infrastructure secrets don't exist

**Automatically Created Secrets:**
- `customizer-pg-existing-secret` - Customizer PostgreSQL password
- `datastore-pg-existing-secret` - Datastore PostgreSQL password
- `entity-store-pg-existing-secret` - Entity Store PostgreSQL password
- `evaluator-pg-existing-secret` - Evaluator PostgreSQL password
- `guardrail-pg-existing-secret` - Guardrail PostgreSQL password

These secrets are created from the `postgresql-secrets.yaml` template.

**Manual Override (if needed):**
If infrastructure secrets are in a different namespace or you need custom passwords, you can:
1. Override via `--set` flags: `--set postgresqlSecrets.evaluator.password=<custom-password>`
2. Or create secrets manually before installation (they will not be overwritten)

**PostgreSQL Password Reference**: Default passwords (used as fallbacks):
- Customizer: `ncspassword`
- Datastore: `ndspass`
- Entity Store: `nespass`
- Evaluator: `evalpass`
- Guardrail: `guardrailpass`

#### Datastore Secrets (Automatically Created)

**IMPORTANT**: The datastore secrets are **automatically created** by the Helm chart. You do NOT need to create them manually.

The following secrets are created automatically:
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

helm install nemo-instances ./deploy/nemo-instances \
  -n <namespace> \
  --set datastore.gitea.adminPassword=$GITEA_ADMIN_PASSWORD \
  --set datastore.lfsJwtSecret=$LFS_JWT_SECRET
```

**⚠️ WARNING**: Do NOT use default credentials in production environments!

#### NGC Secrets (Required - Validated Before Installation)

**IMPORTANT**: NGC secrets are **required** and will be validated by the pre-install hook. Installation will fail if these secrets are missing.

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

**Validation**: The pre-install hook automatically checks these secrets exist and validates their structure before Helm proceeds.

#### Optional Secrets

```bash
# Weights & Biases (optional, for Customizer)
oc create secret generic wandb-secret \
  --from-literal=apiKey=<wandb-api-key> \
  --from-literal=encryptionKey=<encryption-key> \
  -n <namespace>
```

### 3. Required ConfigMaps (For NemoCustomizer)

**IMPORTANT**: Both `nemo-training-config` and `nemo-model-config` ConfigMaps are **automatically created** by the Helm chart with the correct configuration.

**Automatically Created ConfigMaps:**
- `nemo-training-config`: Training job configuration (container defaults, environment variables)
- `nemo-model-config`: Model configuration with:
  - `customizationTargets`: Defines the models that can be customized (default: meta/llama-3.2-1b-instruct@2.0)
  - `customizationConfigTemplates`: Defines training templates for those models (default: one template for llama-3.2-1b-instruct)

**Note**: You do NOT need to create these ConfigMaps manually. They are automatically created by the Helm chart.

**Customization**: If you need to customize the model configuration, you can:
1. Edit the ConfigMap after installation: `oc edit configmap nemo-model-config -n <namespace>`
2. Override via Helm values (if supported in future versions)

## Components

### NeMo Operator

**Purpose**: Kubernetes operator for managing NeMo microservices and training jobs

**Details**:
- Chart: NVIDIA NeMo Operator v25.06 (exact from quickstart line 122)
- Repository: `https://helm.ngc.nvidia.com/nvidia-nemo` (requires NGC authentication)
- Image: `nvcr.io/nvidia/nemo-operator:v25.06`
- Resource Limits: 512Mi memory limit, 256Mi memory request (exact from quickstart lines 124-125)
- Post-install Hook: Automatically patches ServiceAccount with `ngc-secret` (matches quickstart line 129)
- Pod Restart: Automatically restarts operator pods after patching (matches quickstart line 132)
- CRDs: Installs NeMo Custom Resource Definitions (nemocustomizers, nemodatastores, etc.)

**Prerequisites**:
- NGC Helm repository must be added and authenticated (quickstart lines 118-119):
  ```bash
  helm repo add nvidia-nemo https://helm.ngc.nvidia.com/nvidia-nemo
  helm repo update
  ```
- **NGC image pull secret (`ngc-secret`) must exist in the namespace BEFORE installation** (quickstart lines 43-47):
  ```bash
  oc create secret docker-registry ngc-secret \
    --docker-server=nvcr.io \
    --docker-username='$oauthtoken' \
    --docker-password=$NGC_API_KEY \
    -n <namespace>
  ```
- Volcano scheduler must be installed (required dependency, quickstart Step 3)

**Installation Process** (matches quickstart Step 4 exactly):
1. Helm installs NeMo Operator subchart with resource limits (lines 122-126)
2. Post-install hook patches ServiceAccount with `ngc-secret` (line 129)
3. Post-install hook restarts operator pods to pick up the secret (line 132)

### NIM Operator

**Purpose**: Kubernetes operator for managing NVIDIA NIM (NVIDIA Inference Microservices)

**Details**:
- Chart: k8s-nim-operator v3.0.0 (local OpenShift-specific chart)
- Repository: Local chart from `deploy-on-openshift/deployments/helm/k8s-nim-operator`
- Image: `ghcr.io/nvidia/k8s-nim-operator:release-3.0` (exact from chart values.yaml)
- Resource Limits: 512Mi memory limit, 256Mi memory request (exact from quickstart lines 143-144)
- CRDs: Installs NIM Custom Resource Definitions (nimpipelines, nimcaches, nimservices, nimbuilds)

**Prerequisites**:
- **CRITICAL**: Uses local OpenShift-specific Helm chart (NOT the official NVIDIA repo chart)
  - The official NVIDIA Helm repository chart (`nvidia/k8s-nim-operator`) is NOT compatible with OpenShift
  - due to security context and permission differences (quickstart line 150)
  - Chart must be packaged: `cd deploy-on-openshift/deployments/helm/k8s-nim-operator && helm package . --destination ../../../../NeMo-Microservices/deploy/nemo-instances/charts`
- NeMo Operator must be installed (required dependency)

**Installation Process** (matches quickstart Step 5 exactly):
1. Helm installs NIM Operator subchart with resource limits (lines 141-145)
2. No post-install steps required (unlike NeMo Operator)

## Installation

📖 **Installation guide**: See [main README](../../README.md#installation) for complete installation instructions, including prerequisites and secret creation.

**Quick reference:**
```bash
cd deploy/nemo-instances
helm dependency update
helm install nemo-instances . -n <namespace> --set namespace.name=<namespace>
```

**Deployment Order**:
1. NeMo Operator is installed first
2. NIM Operator is installed second (depends on NeMo Operator)
3. NeMo instances are deployed last (depends on both operators)

**Expected**: Operators installed, then 7 custom resources created (matches quickstart Step 6, line 164)

## Service Endpoints

After deployment, services are available at:

- `http://nemocustomizer-sample.<namespace>.svc.cluster.local:8000`
- `http://nemodatastore-sample.<namespace>.svc.cluster.local:8000`
- `http://nemoentitystore-sample.<namespace>.svc.cluster.local:8000`
- `http://nemoevaluator-sample.<namespace>.svc.cluster.local:8000`
- `http://nemoguardrails-sample.<namespace>.svc.cluster.local:8000`
- `http://nv-embedqa-1b-v2.<namespace>.svc.cluster.local:8000` (embedding model)
- Chat models are deployed via RHOAI/OpenShift AI (KServe InferenceService)

## GPU Requirements

- **NIMCache** and **NIMPipeline** (embedding model) require GPU nodes
  - Note: Chat models are deployed via RHOAI/OpenShift AI, not via Helm chart
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

<details>
<summary><strong>Example: Verify All NeMo Instances Components</strong></summary>

To verify all NeMo instances (operators, microservices, and NIM services) are running, use the following command:

```bash
# Replace <namespace> with your actual namespace, e.g., arhkp-nemo-helm
oc get pods -n <namespace> | grep -E "(nemo-operator|nim-operator|nemocustomizer|nemodatastore|nemoentitystore|nemoevaluator|nemoguardrails|nimcache|nimpipeline)"
```

**Expected Output:**
```
nemo-samples-nemo-operator-controller-manager-b4bd4bd69-vbh7z    2/2     Running     0          152m
nemo-samples-nim-operator-666b78dd44-crmtm                       1/1     Running     0          152m
nemocustomizer-sample-5d8b5fb5fb-qqd8c                           1/1     Running     0          50m
nemodatastore-sample-74dcb5568d-qbkc8                            1/1     Running     0          152m
nemoentitystore-sample-66b4fc4fdc-9n82g                          1/1     Running     0          152m
nemoevaluator-sample-79544995db-b4h4b                            1/1     Running     0          152m
nemoguardrails-sample-74bb7f5bc9-w2q68                           1/1     Running     0          152m
```

All pods should show `Running` status. The NeMo Operator pod shows `2/2 Running` (controller + manager containers), while other pods show `1/1 Running`. If any pods are not running, check the troubleshooting section or review pod logs.

</details>

## Uninstallation

📖 **Uninstall documentation**: See [main README](../../README.md#uninstallation) for complete uninstallation instructions.

**Quick reference:**
```bash
# Uninstall nemo-instances first (pre-delete hook handles CR cleanup automatically)
helm uninstall nemo-instances -n <namespace>

# Then uninstall nemo-infra
helm uninstall nemo-infra -n <namespace>
```

The pre-delete hook (`pre-delete-cleanup.yaml`) automatically deletes Custom Resources before Helm uninstall.

## Notes

- This chart follows the quickstart Step 6 exactly (lines 152-164)
- All namespace references are automatically templated
- Service hostnames are automatically updated to match namespace
- GPU tolerations are pre-configured for common OpenShift setups
- **Pre-delete hook** automatically cleans up Custom Resources before Helm uninstall - just run `helm uninstall` and it works!

