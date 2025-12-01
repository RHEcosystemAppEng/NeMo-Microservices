# NVIDIA NeMo Microservices on OpenShift AI

Helm charts for deploying NVIDIA NeMo microservices infrastructure and demos on OpenShift.

## Prerequisites

- OpenShift 4.x cluster
- Helm 3.x
- `oc` CLI configured
- NGC API key (for pulling NVIDIA images)
- GPU nodes (for training/inference workloads)

## Charts

- **`deploy/nemo-infra`**: Infrastructure components (databases, MLflow, Argo, Milvus, Volcano, Operators)
- **`deploy/nemo-instances`**: Example NeMo microservices deployments

## Installation

### Prerequisites

Before installation, ensure you have:

1. **NGC Helm Repository** (required for NeMo Operator):
   ```bash
   helm repo add nvidia-nemo https://helm.ngc.nvidia.com/nvidia-nemo
   helm repo update
   ```

2. **NGC API Key** for pulling NVIDIA images and downloading models

3. **OpenShift Cluster** with GPU nodes available

### Step 1: Deploy Infrastructure

Deploy all infrastructure components (PostgreSQL, MLflow, Argo Workflows, Milvus, Volcano, Operators):

```bash
cd deploy/nemo-infra

# Update dependencies
helm dependency update

# Deploy infrastructure
helm install nemo-infra . \
  -n <namespace> \
  --create-namespace
```

**Verify installation:**
```bash
oc get pods -n <namespace> | grep -E "(postgresql|mlflow|volcano|argo|milvus|opentelemetry|jupyter|minio)"
```

**Expected Output:**
```
jupyter-notebook-5fc745674d-9gq29                                1/1     Running     0          175m
nemo-infra-argo-workflows-server-6ccf84f45d-rnvxg                1/1     Running     0          175m
nemo-infra-argo-workflows-workflow-controller-68d456d755-hds5p   1/1     Running     0          175m
nemo-infra-customizer-mlflow-tracking-6787ff598-fjmmr            1/1     Running     0          175m
nemo-infra-customizer-opentelemetry-648455b458-zq8v6             1/1     Running     0          175m
nemo-infra-customizer-postgresql-0                               1/1     Running     0          175m
nemo-infra-datastore-postgresql-0                                1/1     Running     0          175m
nemo-infra-entity-store-postgresql-0                             1/1     Running     0          175m
nemo-infra-evaluator-milvus-standalone-86599fc78f-gkhhv          1/1     Running     0          175m
nemo-infra-evaluator-opentelemetry-577d4d757-lnlcm               1/1     Running     0          175m
nemo-infra-evaluator-postgresql-0                                1/1     Running     0          175m
nemo-infra-guardrail-postgresql-0                                1/1     Running     0          175m
nemo-infra-minio-89bdcdd79-s28km                                 1/1     Running     0          175m
nemo-infra-postgresql-0                                          1/1     Running     0          175m
```

All pods should show `1/1 Running` status. If any pods are not running, check the troubleshooting section in [deploy/nemo-infra/README.md](deploy/nemo-infra/README.md#troubleshooting).

📖 **Configuration options**: [deploy/nemo-infra/README.md](deploy/nemo-infra/README.md#configuration)

### Step 2: Create Required Secrets

Before deploying NeMo instances, create the required secrets:

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

These secrets must match the PostgreSQL passwords from your infrastructure deployment. Default passwords (development only):

```bash
# Customizer PostgreSQL
oc create secret generic customizer-pg-existing-secret \
  --from-literal=password=ncspassword \
  -n <namespace>

# Datastore PostgreSQL
oc create secret generic datastore-pg-existing-secret \
  --from-literal=password=ndspass \
  -n <namespace>

# Entity Store PostgreSQL
oc create secret generic entity-store-pg-existing-secret \
  --from-literal=password=nespass \
  -n <namespace>

# Evaluator PostgreSQL
oc create secret generic evaluator-pg-existing-secret \
  --from-literal=password=evalpass \
  -n <namespace>

# Guardrail PostgreSQL
oc create secret generic guardrail-pg-existing-secret \
  --from-literal=password=guardrailpass \
  -n <namespace>
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
nemo-samples-nemo-operator-controller-manager-b4bd4bd69-vbh7z    2/2     Running     0          152m
nemo-samples-nim-operator-666b78dd44-crmtm                       1/1     Running     0          152m
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
- **Purpose**: Allows model downloader jobs to run with specific security contexts
- **Granted to**: `nemocustomizer-sample` ServiceAccount only
- **Why**: Model downloader jobs need `RunAsAny` to match PVC ownership (user 1000, group 2000)
- **Not granted to**: `default` ServiceAccount (principle of least privilege)

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

