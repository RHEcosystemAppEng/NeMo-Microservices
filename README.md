# NVIDIA NeMo Microservices on OpenShift AI

Helm charts for deploying NVIDIA NeMo microservices infrastructure and demos on OpenShift.

## Prerequisites

- **OpenShift 4.x cluster** with sufficient capacity (see [Storage requirements](#storage-requirements) below)
- **Helm 3.x** and **`oc` CLI** configured
- **NGC API key** for pulling NVIDIA images and downloading models
- **GPU nodes** for training and inference workloads
- **Cluster admin permissions** (or equivalent) for:
  - Creating and managing **Security Context Constraints (SCCs)** (e.g. for Customizer jobs, NIM, inference pods)
  - Installing cluster-scoped or namespace-scoped operators and webhooks (e.g. Volcano)
  - Creating service accounts and RBAC as required by the charts
- **Service Mesh / Istio** (if used in your cluster): Ensure the deployment namespace is part of the mesh or that mesh policies (e.g. `PeerAuthentication`, `DestinationRule`) allow traffic to NeMo services. Unmanaged or disabled mesh in the namespace is also supported.

## Storage requirements

Plan and allocate persistent storage for the following. Default sizes are from the Helm chart values; adjust in `values.yaml` (or `values.yaml.sample`) as needed.

| Component | Purpose | Default size | Notes |
|-----------|---------|--------------|--------|
| **Customizer (model PVC)** | Base model cache for fine-tuning | 100 Gi | Large base models (e.g. Llama 3.2 1B ~62 GB); increase if using larger models. |
| **Customizer (workspace PVC)** | Training job workspace and checkpoints | 50 Gi | Increase for long runs or many experiments. |
| **MLflow (MinIO)** | MLflow artifacts and model registry storage | 50 Gi | Object storage for tracked runs and artifacts. |
| **MLflow (tracking DB volume)** | MLflow tracking DB persistence | 20 Gi | PostgreSQL-backed tracking store. |
| **Vector DB (Milvus)** | Embedding vectors for RAG and evaluator | 100 Gi | Grows with document count and embedding dimension. |
| **NIMCache (chat)** | Cached chat model (e.g. Llama 3.2 1B) | 100 Gi | Multiple GPU profiles (H100, L40S, etc.); 50 Gi often fills. |
| **NIMCache (embedding)** | Cached embedding model | 50 Gi | For RAG embedding pipeline. |
| **NIMCache (retriever)** | Cached retriever/reranker model | 50 Gi | For RAG retriever pipeline. |
| **Datastore** | Shared data and Gitea storage | 10 Gi | Versioned datasets and configs. |
| **Guardrail** | Guardrail config store | 1 Gi | Small config and rule storage. |
| **PostgreSQL (per DB)** | Datastore, Entity Store, Customizer, Guardrail, Evaluator | 2 Gi each | Five databases; total ~10 Gi by default. |

Ensure your cluster’s storage classes and quotas can satisfy these volumes. For production, use appropriate storage classes (e.g. for performance or backups).

## Configuration (minimal changes for new users)

To use this repo with your own environment, set configuration in a few places instead of editing code:

| What | Where | Set to |
|------|--------|--------|
| **Deployment namespace** | `deploy/nemo-infra/values.yaml` and `deploy/nemo-instances/values.yaml` (copy from `values.yaml.sample`) | Your OpenShift project name |
| **Service URLs / InferenceService** | Helm `values.yaml` (e.g. `llamastack.inferenceServiceName`), or RHOAI YAML (e.g. `deploy/rhoai/copilot-llama-stack.yaml` `VLLM_URL`) | Your InferenceService name and namespace |
| **Demos and notebooks** | `env.donotcommit` in each demo (copy from `env.donotcommit.example`) | `NMS_NAMESPACE`, `NIM_CHAT_URL` / `NIM_MODEL_SERVING_URL_EXTERNAL`, tokens as needed |

There are no hard-coded namespaces or service URLs in the repo; all are driven by these config files and environment variables.

## Charts

- **`deploy/nemo-infra`**: Infrastructure components (databases, MLflow, Argo, Milvus, Volcano, Operators)
- **`deploy/nemo-instances`**: Example NeMo microservices deployments

## Installation

### Prerequisites

Before installation, ensure you have:

1. **Cluster admin permissions** (or equivalent) for SCCs, operators, and RBAC (see [Prerequisites](#prerequisites) above).

2. **Service Mesh / Istio**: If your cluster uses a service mesh, ensure the deployment namespace is configured appropriately (included in the mesh or exempted). Adjust `PeerAuthentication` or `DestinationRule` if NeMo services need to communicate across mesh boundaries.

3. **NGC Helm Repository** (required for NeMo Operator):
   ```bash
   helm repo add nvidia-nemo https://helm.ngc.nvidia.com/nvidia-nemo
   helm repo update
   ```

4. **NGC API Key** for pulling NVIDIA images and downloading models.

5. **OpenShift cluster** with GPU nodes available and sufficient storage (see [Storage requirements](#storage-requirements)).

### Step 1: Deploy Infrastructure

Deploy all infrastructure components (PostgreSQL, MLflow, Argo Workflows, Milvus, Volcano, Operators):

```bash
cd deploy/nemo-infra

# Update dependencies (downloads all subcharts)
helm dependency update

# Deploy infrastructure
helm install nemo-infra . \
  -n <namespace> \
  --create-namespace \
  --wait \
  --timeout 30m
```

**Verify installation:**
```bash
oc get pods -n <namespace> | grep nemo-infra
```

**Expected Output (15 pods, all Running):**
```
nemo-infra-admission-57fbdf685d-x5gts                           1/1     Running     0          3m23s
nemo-infra-argo-workflows-server-7f995cbbc7-42mh5               1/1     Running     0          7m36s
nemo-infra-argo-workflows-workflow-controller-f6548b9d9-7xrfs   1/1     Running     0          7m36s
nemo-infra-customizer-mlflow-tracking-c8d7fb779-tnlnj           1/1     Running     0          7m36s
nemo-infra-customizer-opentelemetry-5cfddf4989-5pr4q             1/1     Running     0          7m36s
nemo-infra-customizer-postgresql-0                               1/1     Running     0          7m35s
nemo-infra-datastore-postgresql-0                                1/1     Running     0          7m35s
nemo-infra-entity-store-postgresql-0                             1/1     Running     0          7m35s
nemo-infra-evaluator-milvus-standalone-859d889bb8-4f6p5          1/1     Running     0          7m36s
nemo-infra-evaluator-opentelemetry-79d666d58c-z24h5             1/1     Running     0          7m36s
nemo-infra-evaluator-postgresql-0                                1/1     Running     0          7m35s
nemo-infra-guardrail-postgresql-0                               1/1     Running     0          7m35s
nemo-infra-minio-647ff8cbf9-nx6kk                                1/1     Running     0          7m36s
nemo-infra-postgresql-0                                          1/1     Running     0          7m35s
nemo-infra-scheduler-7f468fdc5b-fvbpm                            1/1     Running     0          7m36s
```

All pods should show `1/1 Running` status. If any pods are not running, check the troubleshooting section in [deploy/nemo-infra/README.md](deploy/nemo-infra/README.md#troubleshooting).

**Component Versions (Latest Stable):**
- PostgreSQL (Bitnami): 18.2.3
- MLflow (Bitnami): 5.1.17
- OpenTelemetry Collector: 0.143.0
- Argo Workflows: 0.47.0
- Milvus: 4.1.11 (OpenShift-compatible, uses embedded woodpecker message queue)
- Volcano: 1.13.1

**OpenShift-Specific Fixes Applied:**
- ✅ Volcano admission-init override (SCC compatibility)
- ✅ Milvus Pulsar disablement (embedded woodpecker queue)
- ✅ Volcano controller security context patch
- ✅ Default queue creation
- ✅ Webhook failure policy (set to Ignore)
- ✅ PodGroup status patch (auto-sets status to Inqueue)
- ✅ PodGroup annotation controller (auto-adds annotation to worker pods)

📖 **Configuration options**: [deploy/nemo-infra/README.md](deploy/nemo-infra/README.md#configuration)

📖 **Clean uninstall/reinstall**: [deploy/nemo-infra/README.md](deploy/nemo-infra/README.md#installation)

### Step 2: Create Required Secrets

Before deploying NeMo instances, create the required secrets:

**Note**: 
- PostgreSQL secrets are **automatically created** by the Helm chart
- NGC secrets are **required** and will be validated by a pre-install hook before Helm proceeds
- If NGC secrets are missing, Helm installation will fail with a clear error message

#### NGC Secrets (Required - Validated Before Installation)
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

#### PostgreSQL Secrets (Automatically Created)

**✅ PostgreSQL secrets are automatically created by the Helm chart.**

The Helm chart automatically:
1. Reads passwords from infrastructure PostgreSQL secrets (`nemo-infra-*-postgresql`)
2. Creates all required `*-pg-existing-secret` secrets with the correct passwords
3. Falls back to defaults if infrastructure secrets don't exist

**You do NOT need to create PostgreSQL secrets manually.**

If you need to override passwords (e.g., for production), use:
```bash
helm install nemo-instances ./deploy/nemo-instances \
  -n <namespace> \
  --set namespace.name=<namespace> \
  --set postgresqlSecrets.evaluator.password=<your-password> \
  --set postgresqlSecrets.guardrail.password=<your-password>
```

⚠️ **Security Note**: Default passwords are for **development/testing only**. For production, use strong, randomly generated passwords.

📖 **Full secrets documentation**: [deploy/nemo-instances/README.md](deploy/nemo-instances/README.md#prerequisites)

### Step 3: Deploy NeMo Instances

Deploy example NeMo microservices (Customizer, Datastore, Entity Store, Evaluator, Guardrail, NIM services):

```bash
cd deploy/nemo-instances

# Update dependencies (downloads operator charts)
helm dependency update

# Deploy operators and create NeMo instances
helm install nemo-instances . \
  -n <namespace> \
  --set namespace.name=<namespace>
```

**Deployment Order:**
1. NeMo Operator is installed first
2. NIM Operator is installed second (depends on NeMo Operator)
3. NeMo instances are deployed last (depends on both operators)

**Verify installation:**
```bash
# Check all NeMo microservices
oc get -n <namespace> nemoentitystore,nemodatastore,nemoguardrails,nemocustomizer,nemoevaluator

# Check NIM services
oc get -n <namespace> nimpipeline,nimcache,nimservice

# Check pods
oc get pods -n <namespace> | grep -E "(nemo-operator|nim-operator|nemocustomizer|nemodatastore|nemoentitystore|nemoevaluator|nemoguardrails|nimcache|nimpipeline)"
```

**Expected Output:**
```
nemo-instances-nemo-operator-controller-manager-...    2/2     Running     0          152m
nemo-instances-nim-operator-...                       1/1     Running     0          152m
nemocustomizer-sample-5d8b5fb5fb-qqd8c                           1/1     Running     0          50m
nemodatastore-sample-74dcb5568d-qbkc8                           1/1     Running     0          152m
nemoentitystore-sample-66b4fc4fdc-9n82g                         1/1     Running     0          152m
nemoevaluator-sample-79544995db-b4h4b                           1/1     Running     0          152m
nemoguardrails-sample-74bb7f5bc9-w2q68                          1/1     Running     0          152m
```

All pods should show `Running` status. The NeMo Operator pod shows `2/2 Running` (controller + manager containers), while other pods show `1/1 Running`. If any pods are not running, check the troubleshooting section in [deploy/nemo-instances/README.md](deploy/nemo-instances/README.md#troubleshooting).

📖 **Configuration options**: [deploy/nemo-instances/README.md](deploy/nemo-instances/README.md#configuration)

### Upgrade

To upgrade existing deployments:

```bash
# Upgrade infrastructure
cd deploy/nemo-infra
helm upgrade nemo-infra . -n <namespace>

# Upgrade instances
cd deploy/nemo-instances
helm upgrade nemo-instances . -n <namespace> --set namespace.name=<namespace>
```

## Security Context Constraints (SCCs)

OpenShift uses Security Context Constraints (SCCs) to control what security settings pods can use. The NeMo deployment follows the **principle of least privilege** by granting specific SCCs only to the ServiceAccounts that need them.

### SCC Access Pattern

**1. NemoCustomizer SCC (`nemo-customizer-scc`)**
- **Purpose**: Allows model downloader jobs and entity handler jobs to run with specific security contexts
- **Granted to**: 
  - `nemocustomizer-sample` ServiceAccount (for customizer workloads)
  - `default` ServiceAccount (for entity handler jobs created by NemoTrainingJob)
- **Why**: 
  - Model downloader jobs need `RunAsAny` to match PVC ownership (user 1000, group 2000)
  - Entity handler jobs use `default` ServiceAccount and need `RunAsAny` to support non-numeric users (e.g., 'nvs') in container images

**2. Nonroot SCC (`nonroot`)**
- **Purpose**: Standard SCC for inference workloads (requires non-root user)
- **Granted to**: `default` ServiceAccount (for UI-created InferenceServices)
- **Why**: UI-created InferenceServices that don't go through NIMService operator use `default` ServiceAccount
- **Note**: NIMService-created InferenceServices use their own ServiceAccounts (handled by NIMService operator)

### Best Practices

1. **Dedicated ServiceAccounts**: Each workload should have its own ServiceAccount
   - NIMService operator creates a ServiceAccount per NIMService (name = NIMService name)
   - Customizer uses `nemocustomizer-sample` ServiceAccount
   - UI-created InferenceServices use `default` ServiceAccount

2. **Explicit SCC Access**: SCCs are granted via RBAC Role/Binding, not via `oc adm policy`
   - See `deploy/nemo-instances/templates/nemocustomizer-oc-rbac.yaml`
   - Follows OpenShift best practices for RBAC

3. **Principle of Least Privilege**: Only grant the minimum SCC required
   - Customizer jobs need `nemo-customizer-scc` (RunAsAny)
   - Inference workloads need `nonroot` (MustRunAsNonRoot)

### Troubleshooting SCC Issues

If pods fail with SCC errors:

```bash
# Check which SCCs are available to a ServiceAccount
oc get rolebinding -n <namespace> | grep <serviceaccount-name>

# Check SCC details
oc get scc nonroot -o yaml
oc get scc nemo-customizer-scc -o yaml

# Verify ServiceAccount is bound correctly
oc get rolebinding default-scc-nonroot-binding -n <namespace> -o yaml
oc get rolebinding customizer-scc-nemo-customizer-scc-binding -n <namespace> -o yaml
```

**Common Issues:**
- **Permission denied errors**: Check if pod's ServiceAccount has the correct SCC access
- **SCC conflicts**: Ensure only one SCC is granted per ServiceAccount (OpenShift selects the most permissive)
- **UI-created InferenceServices**: Should use `default` ServiceAccount with `nonroot` SCC (automatically configured)

## Uninstallation

### ⚠️ Important: Uninstall Order

**Always uninstall `nemo-instances` BEFORE `nemo-infra`** because:
- `nemo-instances` depends on infrastructure components
- Custom Resources in `nemo-instances` must be deleted first
- The pre-delete hook in `nemo-instances` handles CR cleanup automatically

### Standard Uninstall (Recommended)

**Simply run `helm uninstall`** - the pre-delete hook will automatically clean up Custom Resources:

```bash
# Step 1: Uninstall nemo-instances first (pre-delete hook handles CR cleanup)
helm uninstall nemo-instances -n <namespace>

# Step 2: Uninstall infrastructure
helm uninstall nemo-infra -n <namespace>
```

The pre-delete hook (`pre-delete-cleanup.yaml`) in `nemo-instances` automatically:
1. Deletes all Custom Resources (NemoCustomizer, NemoDatastore, etc.)
2. **Handles finalizers** - Automatically removes finalizers if they block deletion
3. Waits for pods to terminate
4. Then Helm proceeds with normal uninstall

**That's it!** The hook handles everything automatically, including finalizer cleanup.

### Why the Pre-Delete Hook Is Needed

When you run `helm uninstall`, Helm only removes resources it manages directly. However:

- **Custom Resources** (NemoCustomizer, NemoDatastore, etc.) are managed by the **NeMo Operator**
- The operator continues to reconcile these CRs and create pods
- Helm doesn't delete CRs because they're not part of the Helm chart templates (they're created by the operator)

The pre-delete hook (`pre-delete-cleanup.yaml`) automatically deletes CRs before Helm uninstall, so `helm uninstall` works seamlessly.

### Fallback: Manual Cleanup (If Hook Fails)

If the pre-delete hook fails (rare), you can manually delete CRs first:

```bash
NAMESPACE="<your-namespace>"

# Step 1: Delete Custom Resources first (CRITICAL - must be done first)
oc delete nemocustomizer,nemodatastore,nemoentitystore,nemoevaluator,nemoguardrail,nimcache,nimpipeline --all -n "$NAMESPACE"

# Step 2: Wait for pods to terminate
oc wait --for=delete pod --all -n "$NAMESPACE" --timeout=300s

# Step 3: Uninstall Helm releases (in correct order)
helm uninstall nemo-instances -n "$NAMESPACE"
helm uninstall nemo-infra -n "$NAMESPACE"

# Step 4: Clean up remaining resources (optional)
oc delete all --all -n "$NAMESPACE" --ignore-not-found=true
oc delete jobs --all -n "$NAMESPACE" --ignore-not-found=true
oc delete configmap,secret,serviceaccount,role,rolebinding --all -n "$NAMESPACE" --ignore-not-found=true

# Step 5: Clean up cluster resources (optional)
oc delete clusterrole,clusterrolebinding -l component=volcano --ignore-not-found=true
oc delete validatingwebhookconfigurations \
  volcano-admission-service-jobs-validate \
  volcano-admission-service-pods-validate \
  volcano-admission-service-queues-validate \
  --ignore-not-found=true

# Step 6: Optionally delete PVCs (preserves data by default)
# oc delete pvc --all -n "$NAMESPACE"
```

### Troubleshooting Stuck Resources

If resources are stuck after cleanup:

```bash
# Check for finalizers blocking deletion
oc get nemocustomizer -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.finalizers}'

# Force delete by removing finalizers (use with caution)
oc patch nemocustomizer <name> -n "$NAMESPACE" -p '{"metadata":{"finalizers":[]}}' --type=merge

# Check for stuck pods
oc get pods -n "$NAMESPACE"

# Force delete stuck pods (if needed)
oc delete pod <pod-name> -n "$NAMESPACE" --force --grace-period=0
```

### Resources Retained by Default

Some resources are retained by default due to resource policies:
- **CustomResourceDefinitions (CRDs)**: Cluster-scoped, typically retained
- **PVCs**: Retained to preserve data (delete manually if needed)
- **ClusterRole/ClusterRoleBinding**: May be retained if used by other namespaces

## Demos

This repository includes several demo notebooks and tutorials:

### Available Demos

1. **RAG (Retrieval-Augmented Generation) Demo** - [`demos/rag/`](demos/rag/)
   - Build a complete RAG pipeline using NeMo Data Store, Entity Store, and NIM models
   - Document ingestion, embedding generation, vector storage, and query processing
   - 📖 [Full documentation](demos/rag/README.md)

2. **LLM-as-a-Judge Demo** - [`demos/custom-llm-as-a-judge/`](demos/custom-llm-as-a-judge/)
   - Use NeMo Evaluator's Custom LLM-as-a-Judge feature to evaluate LLM outputs
   - Evaluate medical consultation summaries on completeness and correctness metrics
   - 📖 [Full documentation](demos/custom-llm-as-a-judge/README.md)

3. **LlamaStack Demo** - [`demos/llamastack/`](demos/llamastack/)
   - End-to-end flow using LlamaStack for unified API access
   - 📖 [Full documentation](demos/llamastack/README.md)

4. **NeMo Retriever Demo** - [`demos/retriever/`](demos/retriever/)
   - Use NeMo Retriever for text reranking to improve RAG pipeline quality
   - Demonstrate reranking API usage and RAG integration
   - 📖 [Full documentation](demos/retriever/README.md)

### Quick Command Reference

For a concise command reference covering infrastructure deployment, configuration, and running demos, see [commands.md](commands.md).

### Demo Prerequisites

All demos require:
- NeMo Microservices deployed (see [Installation](#installation) above)
- KServe InferenceService with `meta/llama-3.2-1b-instruct` model (for RAG and Judge demos)
- Service Account Token for authentication (see demo-specific READMEs)
- Jupyter Workbench or local Jupyter environment

Each demo includes detailed setup instructions in its respective README.

