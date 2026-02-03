# NeMo Microservices - Quick Command Reference

This guide provides essential commands to deploy and configure NeMo Microservices on OpenShift. For detailed explanations, see the respective demo READMEs:
- [RAG Demo](demos/rag/README.md)
- [LLM-as-a-Judge Demo](demos/custom-llm-as-a-judge/README.md)
- [NeMo Retriever Demo](demos/retriever/README.md)

## Quick Setup

Before you begin, set these essential environment variables:

```bash
# 1. Set your namespace
export NAMESPACE=<namespace>

# 2. Set your NGC API key
export NGC_API_KEY="<ngc-api-key>"
```

**Note**: 
- Replace `<namespace>` with your OpenShift project name (e.g., `anemo-rhoai`)
- Replace `<ngc-api-key>` with your NGC API key from [NGC Setup](https://ngc.nvidia.com/setup/api-key)
- InferenceService-related values (name, token, URL) are available only after the InferenceService is deployed. See the [Configuration](#configuration) section for those commands.

**Need help with placeholders?** See the [Placeholders Reference](#appendix-placeholders-reference) appendix for a complete list of all placeholders used in this guide.

## Prerequisites

### 1. Create or Verify Namespace
```bash
# Create a new project/namespace (if it doesn't exist)
oc new-project <namespace>

# Or find existing namespaces
oc projects

# Set your namespace (replace <namespace> with actual value)
export NAMESPACE=<namespace>

# Switch to your namespace
oc project $NAMESPACE
```

### 2. Verify Namespace is in Istio Mesh
```bash
oc get servicemeshmember -n $NAMESPACE
# Should show your namespace as a member
```

## Infrastructure Installation

### 1. Install nemo-infra

**Prerequisites:**
- OpenShift 4.x cluster
- Helm 3.x installed
- `oc` CLI configured and authenticated
- Sufficient cluster resources (CPU, memory, storage)
- Access to container registries (Docker Hub, NGC, Quay.io)

```bash
cd NeMo-Microservices/deploy/nemo-infra

# Update Helm dependencies (downloads all subcharts)
helm dependency update

# Install infrastructure (namespace should already exist)
helm install nemo-infra . -n $NAMESPACE --create-namespace --wait --timeout 30m
```

**Expected Components:**
- PostgreSQL (5 instances: datastore, entity-store, customizer, guardrail, evaluator)
- MLflow tracking server
- OpenTelemetry Collector (2 instances: customizer, evaluator)
- Argo Workflows (server + controller)
- Milvus standalone (vector database)
- Volcano Scheduler + Admission (required for NeMo Operator)
- MinIO (object storage for MLflow artifacts)

### 2. Wait for Infrastructure (Optional - can proceed while starting)
```bash
# Check status
oc get pods -n $NAMESPACE | grep nemo-infra

# Wait for key components
oc wait --for=condition=ready pod -l app.kubernetes.io/instance=nemo-infra -n $NAMESPACE --timeout=300s
```

### 3. Verify Infrastructure is Ready
```bash
# Check all infrastructure pods (should show 15 pods, all Running)
oc get pods -n $NAMESPACE | grep nemo-infra

# Expected output:
# - nemo-infra-*-postgresql-0 (5 pods)
# - nemo-infra-customizer-mlflow-tracking-*
# - nemo-infra-customizer-opentelemetry-*
# - nemo-infra-evaluator-opentelemetry-*
# - nemo-infra-argo-workflows-server-*
# - nemo-infra-argo-workflows-workflow-controller-*
# - nemo-infra-evaluator-milvus-standalone-*
# - nemo-infra-scheduler-*
# - nemo-infra-admission-*
# - nemo-infra-minio-*

# Verify all pods are Running
oc get pods -n $NAMESPACE | grep nemo-infra | grep -v Running
# Should return no results if all are running

# Verify operators are running (if nemo-instances is installed)
oc get pods -n $NAMESPACE | grep -E "operator|controller"
```

### 4. Clean Uninstall and Reinstall (For Fresh Deployment)

To ensure a clean deployment from scratch:

```bash
# Step 1: Uninstall existing deployment
helm uninstall nemo-infra -n $NAMESPACE

# Step 2: Wait for resources to be cleaned up
oc get pods -n $NAMESPACE | grep nemo-infra
# Wait until no nemo-infra pods remain (except PVCs which are retained)

# Step 3: Clean up any orphaned resources (if needed)
oc delete job,serviceaccount,role,rolebinding -n $NAMESPACE -l component=volcano --ignore-not-found=true

# Step 4: Clean up any stuck Pulsar resources (if upgrading from Milvus v5.0.12)
oc delete statefulset,job,pod,svc -n $NAMESPACE -l app.kubernetes.io/name=pulsar --ignore-not-found=true
oc get svc -n $NAMESPACE | grep pulsarv3 | awk '{print $1}' | xargs -r oc delete svc -n $NAMESPACE --ignore-not-found=true

# Step 5: Reinstall fresh
cd NeMo-Microservices/deploy/nemo-infra
helm dependency update
helm install nemo-infra . -n $NAMESPACE --create-namespace --wait --timeout 30m
```

### 5. Troubleshooting Infrastructure Issues

**If Volcano admission-init job fails:**
```bash
# Grant privileged SCC to admission service account
oc adm policy add-scc-to-user privileged system:serviceaccount:$NAMESPACE:nemo-infra-admission

# Delete the failing job to trigger recreation
oc delete job nemo-infra-admission-init-* -n $NAMESPACE
```

**If Volcano scheduler fails with "no endpoints available":**
```bash
# Grant privileged SCC to admission service account
oc adm policy add-scc-to-user privileged system:serviceaccount:$NAMESPACE:nemo-infra-admission

# Delete the failing admission replicaset to trigger recreation
oc delete replicaset -n $NAMESPACE -l app.kubernetes.io/name=volcano,app.kubernetes.io/component=admission

# Wait for admission pod to be ready
oc wait --for=condition=ready pod -l app.kubernetes.io/name=volcano,app.kubernetes.io/component=admission -n $NAMESPACE --timeout=300s

# Delete scheduler pod to trigger recreation
oc delete pod -n $NAMESPACE -l app.kubernetes.io/name=volcano,app.kubernetes.io/component=scheduler
```

**If Volcano Jobs not creating worker pods:**
```bash
# Check if default queue exists (chart creates it via post-install hook volcano-default-queue)
oc get queue default -n $NAMESPACE

# If missing (e.g. hook failed or volcano-queue-patch SA was not created), create it manually:
cat <<EOF | oc apply -f -
apiVersion: scheduling.volcano.sh/v1beta1
kind: Queue
metadata:
  name: default
  namespace: $NAMESPACE
spec:
  weight: 1
  capability:
    cpu: "1000"
    memory: "1000Gi"
  reclaimable: true
  state: Open
EOF

# Verify controller is running
oc get pods -n $NAMESPACE | grep controllers

# Check PodGroups and set status if needed
oc get podgroup -n $NAMESPACE

# If PodGroup status is empty, set it to Inqueue (required for pod creation):
PODGROUP_NAME=$(oc get podgroup -n $NAMESPACE | grep <job-name> | awk '{print $1}' | head -1)
if [ -n "$PODGROUP_NAME" ]; then
  oc patch podgroup $PODGROUP_NAME -n $NAMESPACE --type='json' \
    -p='[{"op": "add", "path": "/status/phase", "value": "Inqueue"}]'
fi

# If Volcano Job exists, PodGroup is Inqueue, queue is Open, but no worker pods are created:
# The Volcano controller may be stuck. Restart it to force re-sync:
oc delete pod -n $NAMESPACE -l app.kubernetes.io/name=volcano,app.kubernetes.io/component=controllers
# Wait ~10 seconds for controller to restart and create pods
```

**If Volcano worker pods stuck in Pending (not being scheduled):**
```bash
# Check if pod has PodGroup annotation (required for scheduling)
WORKER_POD=$(oc get pods -n $NAMESPACE -l volcano.sh/job-name -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$WORKER_POD" ]; then
  oc get pod $WORKER_POD -n $NAMESPACE -o jsonpath='{.metadata.annotations.scheduling\.volcano\.sh/podgroup}'
  echo ""
fi

# If annotation is missing, find PodGroup and add it:
PODGROUP_NAME=$(oc get podgroup -n $NAMESPACE | grep <job-name> | awk '{print $1}' | head -1)
if [ -n "$WORKER_POD" ] && [ -n "$PODGROUP_NAME" ]; then
  oc patch pod $WORKER_POD -n $NAMESPACE --type='json' \
    -p="[{\"op\": \"add\", \"path\": \"/metadata/annotations/scheduling.volcano.sh~1podgroup\", \"value\": \"$PODGROUP_NAME\"}]"
  
  # Also ensure PodGroup status is set
  oc patch podgroup $PODGROUP_NAME -n $NAMESPACE --type='json' \
    -p='[{"op": "add", "path": "/status/phase", "value": "Inqueue"}]'
fi

# Verify the PodGroup annotation controller is running (auto-patches new pods)
oc get pods -n $NAMESPACE | grep podgroup-annotation-controller

# Check controller logs
oc logs -n $NAMESPACE -l app=volcano-podgroup-annotation-controller --tail=50
```

**If Milvus is crashing or Pulsar components are stuck:**
```bash
# Verify Milvus is using v4.1.11 (not v5.0.12)
helm get values nemo-infra -n $NAMESPACE | grep -A 5 milvus

# Clean up stuck Pulsar resources
oc delete statefulset,job,pod,svc -n $NAMESPACE -l app.kubernetes.io/name=pulsar --ignore-not-found=true
oc get svc -n $NAMESPACE | grep pulsarv3 | awk '{print $1}' | xargs -r oc delete svc -n $NAMESPACE --ignore-not-found=true

# Verify Milvus configuration
oc get configmap -n $NAMESPACE | grep milvus
oc logs -n $NAMESPACE -l app.kubernetes.io/name=milvus --tail=100
```

**If Argo Workflows service account conflict:**
```bash
# Delete the conflicting service account
oc delete sa argo-workflows-executor -n $NAMESPACE

# Retry the upgrade
cd NeMo-Microservices/deploy/nemo-infra
helm upgrade nemo-infra . -n $NAMESPACE
```

For more detailed troubleshooting, see [deploy/nemo-infra/README.md](deploy/nemo-infra/README.md#troubleshooting).

## Instances Installation

### 0. Create Required NGC Secrets (REQUIRED)

Before installing nemo-instances, you must create NGC secrets for pulling NVIDIA images and accessing NGC API:

```bash
# Set your NGC API key (get it from https://ngc.nvidia.com/setup/api-key)
export NGC_API_KEY="<ngc-api-key>"

# Create NGC Image Pull Secret (for pulling images from nvcr.io)
oc create secret docker-registry ngc-secret \
  --docker-server=nvcr.io \
  --docker-username='$oauthtoken' \
  --docker-password=$NGC_API_KEY \
  -n $NAMESPACE

# Create NGC API Secret (for model downloads and API access)
oc create secret generic ngc-api-secret \
  --from-literal=NGC_API_KEY=$NGC_API_KEY \
  -n $NAMESPACE

# Verify secrets were created
oc get secret ngc-secret ngc-api-secret -n $NAMESPACE
```

**Note**: The pre-install validation hook will automatically check for these secrets and fail with a clear error message if they're missing.

### 1. Install nemo-instances (without LlamaStack)

**Important**: Install instances WITHOUT LlamaStack first. LlamaStack requires the InferenceService's service account to exist, which is created when you deploy the InferenceService.

```bash
cd NeMo-Microservices/deploy/nemo-instances

# Update Helm dependencies
helm dependency update

# Install instances WITHOUT LlamaStack
helm install nemo-instances . -n $NAMESPACE \
  --set namespace.name=$NAMESPACE \
  --set llamastack.enabled=false
```

**GPU taints:** The chart's `values.yaml` includes tolerations for `g5-gpu`, `g6e-gpu`, `nvidia.com/gpu`, and `node-role.kubernetes.io/master` for all GPU workloads (NIMCache, NIMPipeline, Customizer). A fresh install works on clusters that use either g5-gpu or g6e-gpu (and master) taints—**no separate patch commands are needed** after install.

### 2. Wait for Services to Start (Optional)

```bash
# Monitor progress
watch oc get pods -n $NAMESPACE

# Or check specific services
oc get pods -n $NAMESPACE | grep -E "datastore|entitystore|customizer|evaluator|guardrail"
```

### 3. Verify Services are Ready (Optional)

```bash
# Check all NeMo service pods
oc get pods -n $NAMESPACE | grep -E "datastore|entitystore|customizer|evaluator|guardrail|rerankqa"

# Check Custom Resources
oc get nemodatastore,nemoentitystore,nemocustomizer,nemoevaluator,nemoguardrail -n $NAMESPACE

# Check NIM services (embedding and retriever)
oc get nimcache,nimpipeline -n $NAMESPACE

# Verify retriever service specifically
oc get svc nv-rerankqa-1b-v2 -n $NAMESPACE
oc get pods -n $NAMESPACE | grep rerankqa
```

### 4. Deploy InferenceService Manually

**⚠️ Important: Check GPU Taints First**

If your cluster has GPU nodes with taints, you must add GPU tolerations to your InferenceService during deployment (or patch it immediately after). Otherwise, pods will be stuck in `Pending` state.

**Note:** NIMCache and NIMPipeline pods (from `nemo-instances` Helm chart) already get GPU tolerations from the chart's `values.yaml` (g5-gpu, g6e-gpu, nvidia.com/gpu, node-role.kubernetes.io/master). No separate patch is needed for those after a fresh install. The following applies to **InferenceService** (KServe) and **Notebook/Workbench** resources you deploy separately.

**Check if GPU nodes have taints:**
```bash
# Check for GPU taints on nodes
oc get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints | grep -E "gpu|GPU"

# If you see taints like "g5-gpu=true:NoSchedule", "g6e-gpu=true:NoSchedule", or "nvidia.com/gpu=...",
# add matching tolerations to InferenceService or Notebook (see below)
```

**If GPU taints exist, deploy InferenceService with tolerations:**

When deploying your InferenceService (via NIMPipeline, YAML, etc.), include GPU tolerations in the spec (include both g5-gpu and g6e-gpu if your cluster may use either):

```yaml
spec:
  predictor:
    tolerations:
      - key: "g5-gpu"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"
      - key: "g6e-gpu"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"
      - key: "nvidia.com/gpu"
        operator: "Exists"
        effect: "NoSchedule"
      - key: "node-role.kubernetes.io/master"
        operator: "Exists"
        effect: "NoSchedule"
```

**Or patch after deployment (if you forgot):**
```bash
# Add GPU tolerations (g5-gpu, g6e-gpu, nvidia.com/gpu, master) for common OpenShift GPU nodes
oc patch inferenceservice <inferenceservice-name> -n $NAMESPACE --type='merge' -p='{"spec":{"predictor":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"g6e-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"},{"key":"node-role.kubernetes.io/master","operator":"Exists","effect":"NoSchedule"}]}}}'

# For NemoTrainingJob (Customizer training jobs) - if worker pods are pending:
# 1. Patch the NemoTrainingJob to add g6e-gpu and master tolerations:
oc patch nemotrainingjob <job-name> -n $NAMESPACE --type='merge' -p='{"spec":{"trainingWorkload":{"trainerOverrides":{"spec":{"tolerations":[{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"},{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"g6e-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"node-role.kubernetes.io/master","operator":"Exists","effect":"NoSchedule"}]}}}}}'

# 2. Delete the Volcano Job so operator recreates it with new tolerations:
VOLCANO_JOB=$(oc get job.batch.volcano.sh -n $NAMESPACE | grep <job-name> | awk '{print $1}')
oc delete job.batch.volcano.sh $VOLCANO_JOB -n $NAMESPACE

# 3. If worker pods still don't appear after Volcano Job is recreated, restart Volcano controller:
oc delete pod -n $NAMESPACE -l app.kubernetes.io/name=volcano,app.kubernetes.io/component=controllers

# IMPORTANT: After patching InferenceService, scale down old revision to 0
oc get deployment -n $NAMESPACE | grep <inferenceservice-name>-predictor
oc scale deployment <deployment-name-old> -n $NAMESPACE --replicas=0
```

**For more details, see [GPU Taints and Tolerations](#gpu-taints-and-tolerations) section.**

---

Deploy your InferenceService using your preferred method (NIMPipeline, direct YAML, etc.). The InferenceService will automatically create a service account named `<inferenceservice-name>-sa`.

**Example**: If your InferenceService is named `anemo-rhoai-model`, the service account will be `anemo-rhoai-model-sa`.

**Verify InferenceService is deployed:**
```bash
oc get inferenceservice -n $NAMESPACE
```

**Verify service account exists:**
```bash
# Get InferenceService name
export INFERENCESERVICE_NAME=$(oc get inferenceservice -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
export SERVICE_ACCOUNT_NAME="${INFERENCESERVICE_NAME}-sa"

# Verify service account exists
oc get sa $SERVICE_ACCOUNT_NAME -n $NAMESPACE
```

### 5. Enable LlamaStack

After your InferenceService is deployed and the service account exists, enable LlamaStack:

```bash
# Get InferenceService name
export INFERENCESERVICE_NAME=$(oc get inferenceservice -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')

# Verify service account exists (auto-created by InferenceService)
export SERVICE_ACCOUNT_NAME="${INFERENCESERVICE_NAME}-sa"
oc get sa $SERVICE_ACCOUNT_NAME -n $NAMESPACE

# Enable LlamaStack
# Only need to provide inferenceServiceName - everything else is auto-constructed
cd NeMo-Microservices/deploy/nemo-instances
helm upgrade nemo-instances . -n $NAMESPACE \
  --set namespace.name=$NAMESPACE \
  --set llamastack.enabled=true \
  --set llamastack.inferenceServiceName=$INFERENCESERVICE_NAME \
  --set llamastack.createServiceAccount=false \
  --reuse-values
```

**Note**: 
- Only `llamastack.inferenceServiceName` is required (the Kubernetes resource name, e.g., `anemo-rhoai-model1`)
- The template auto-constructs:
  - Service account name: `<inferenceServiceName>-sa`
  - Predictor service name: `<inferenceServiceName>-predictor`
  - Service URL: `http://<inferenceServiceName>-predictor.<namespace>.svc.cluster.local:80`
  - RBAC resources (Role, RoleBinding): `<inferenceServiceName>-sa-token-reader`

**Verify LlamaStack is running:**
```bash
oc get pods -n $NAMESPACE | grep llamastack
# Should show: llamastack-xxxxx   2/2     Running

# Verify token is mounted
LLAMASTACK_POD=$(oc get pods -n $NAMESPACE -l app=nemo-llamastack -o jsonpath='{.items[0].metadata.name}')
oc exec -n $NAMESPACE $LLAMASTACK_POD -c llamastack-ctr -- env | grep NVIDIA_SERVICE_ACCOUNT_TOKEN
```

**Note**: LlamaStack will start successfully because:
- The service account already exists (created by InferenceService)
- The token secret is auto-created by Kubernetes
- LlamaStack uses the service account's token for authentication

## Configuration

**Prerequisites**: These commands require that your InferenceService is already deployed. If you haven't deployed it yet, do that first.

### 1. Get InferenceService Name and Related Values

After your InferenceService is deployed, get all related values:

```bash
# Get InferenceService name
export INFERENCESERVICE_NAME=$(oc get inferenceservice -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')

# Get service account name (automatically created by InferenceService)
export SERVICE_ACCOUNT_NAME="${INFERENCESERVICE_NAME}-sa"

# Get service account token (required for LlamaStack and NIM Model Serving)
export SERVICE_ACCOUNT_TOKEN=$(oc create token ${SERVICE_ACCOUNT_NAME} -n $NAMESPACE --duration=8760h)

# Get external URL (required for demos)
export EXTERNAL_URL=$(oc get inferenceservice $INFERENCESERVICE_NAME -n $NAMESPACE -o jsonpath='{.status.url}')

# Verify values
echo "InferenceService: $INFERENCESERVICE_NAME"
echo "Service Account: $SERVICE_ACCOUNT_NAME"
echo "External URL: $EXTERNAL_URL"
echo "Token: ${SERVICE_ACCOUNT_TOKEN:0:20}..." # Show first 20 chars only
```

**Save these values** - you'll need them for demo `env.donotcommit` files:
- `SERVICE_ACCOUNT_TOKEN` → use as `NIM_SERVICE_ACCOUNT_TOKEN` in env files
- `EXTERNAL_URL` → use as `NIM_MODEL_SERVING_URL_EXTERNAL` in env files
- `INFERENCESERVICE_NAME` → use as `NIM_MODEL_SERVING_SERVICE` in env files

### 2. Individual Commands (Alternative)

If you prefer to run commands individually:

```bash
# Get the token (replace <service-account-name> with your actual SA name)
# Typically: <inferenceservice-name>-sa
oc create token <service-account-name> -n $NAMESPACE --duration=8760h

# Example (replace with your actual service account and namespace):
# oc create token my-model-sa -n my-namespace --duration=8760h

# Get the external URL of your InferenceService
oc get inferenceservice <inferenceservice-name> -n $NAMESPACE -o jsonpath='{.status.url}'

# Example (replace with your actual InferenceService name and namespace):
# oc get inferenceservice my-model -n my-namespace -o jsonpath='{.status.url}'
# Output: https://my-model-my-namespace.apps.my-cluster.example.com
```

### 3. Find Service Names (Optional)
```bash
# Find Chat NIM service (KServe InferenceService)
oc get svc -n $NAMESPACE | grep predictor

# Find Embedding NIM service
oc get svc -n $NAMESPACE | grep embedqa

# Find Retriever NIM service
oc get svc -n $NAMESPACE | grep rerankqa

# Find LlamaStack service
oc get svc -n $NAMESPACE | grep llamastack

# Find all NeMo services
oc get svc -n $NAMESPACE | grep -E "datastore|entitystore|customizer|evaluator|guardrail"
```

### 4. Verify LlamaStack Configuration
```bash
# Check LlamaStack pod status
oc get pods -n $NAMESPACE | grep llamastack

# Verify Istio sidecar is present (required for KServe communication)
oc get pod -n $NAMESPACE -l app=nemo-llamastack -o jsonpath='{.items[0].spec.containers[*].name}'
# Should show: llamastack-ctr istio-proxy

# Test LlamaStack (optional)
LLAMASTACK_POD=$(oc get pods -n $NAMESPACE -l app=nemo-llamastack -o jsonpath='{.items[0].metadata.name}')
oc exec -n $NAMESPACE $LLAMASTACK_POD -- curl -s -X POST http://localhost:8321/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"nvidia/meta/llama-3.2-1b-instruct","messages":[{"role":"user","content":"test"}]}'
```

## Manually deploy Workbench and apply Tolerations

**⚠️ Important: Apply GPU Tolerations Before Running Demos**

If your cluster has GPU nodes with taints and you want to run demos in a Workbench/Notebook, you must add GPU tolerations to the Workbench resource. Otherwise, the Workbench pod will be stuck in `Pending` state.

**Check if GPU nodes have taints:**
```bash
# Check for GPU taints on nodes
oc get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints | grep -E "gpu|GPU"
```

**If GPU taints exist, apply GPU tolerations to Workbench:**

```bash
# Patch Notebook/Workbench CR to add GPU tolerations (g5-gpu, g6e-gpu, nvidia.com/gpu, master)
oc patch notebook <notebook-name> -n $NAMESPACE --type='merge' -p='{"spec":{"template":{"spec":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"g6e-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"},{"key":"node-role.kubernetes.io/master","operator":"Exists","effect":"NoSchedule"}]}}}}'

# Example (replace with your actual notebook name and namespace):
# oc patch notebook anemo-rhoai-wb -n anemo-rhoai --type='merge' -p='{"spec":{"template":{"spec":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"g6e-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"},{"key":"node-role.kubernetes.io/master","operator":"Exists","effect":"NoSchedule"}]}}}}'

# Find your notebook name:
oc get notebook -n $NAMESPACE

# Delete the pending pod to trigger recreation with new tolerations
oc delete pod <pod-name-pending> -n $NAMESPACE

# Verify the pod is scheduled and running
oc get pod <pod-name> -n $NAMESPACE -o wide
```

**For more details, see [GPU Taints and Tolerations](#gpu-taints-and-tolerations) section.**

## Running RAG Demo

### 1. Configure RAG Demo
```bash
cd NeMo-Microservices/demos/rag
cp env.donotcommit.example env.donotcommit
```

Edit `env.donotcommit` and set:
```bash
NMS_NAMESPACE=<namespace>
NIM_SERVICE_ACCOUNT_TOKEN=<service-account-token>
```

### 2. Run in Workbench/Notebook (Cluster Mode)
```bash
# Get Jupyter pod name
JUPYTER_POD=$(oc get pods -n $NAMESPACE -l app=jupyter-notebook -o jsonpath='{.items[0].metadata.name}')

# Copy files to pod
oc cp rag-tutorial.ipynb $JUPYTER_POD:/work -n $NAMESPACE
oc cp config.py $JUPYTER_POD:/work -n $NAMESPACE
oc cp env.donotcommit $JUPYTER_POD:/work -n $NAMESPACE

# Port-forward Jupyter
oc port-forward -n $NAMESPACE svc/jupyter-service 8888:8888
```

Access: http://localhost:8888 (token: `token`)

## Running Retriever Demo

### 1. Configure Retriever Demo
```bash
cd NeMo-Microservices/demos/retriever
cp env.donotcommit.example env.donotcommit
```

Edit `env.donotcommit` and set:
```bash
NMS_NAMESPACE=<namespace>
```

**Optional Configuration:**
```bash
RETRIEVER_TOP_K=10  # Number of documents to rerank
RETRIEVER_TOP_N=5   # Number of top results to return after reranking
```

### 2. Verify Retriever Service is Deployed
```bash
# Check retriever service
oc get svc -n $NAMESPACE | grep rerankqa

# Check retriever pods
oc get pods -n $NAMESPACE | grep rerankqa

# Check NIMCache and NIMPipeline
oc get nimcache nv-rerankqa-1b-v2 -n $NAMESPACE
oc get nimpipeline retriever-rerankqa-pipeline -n $NAMESPACE
```

### 3. Run in Workbench/Notebook (Cluster Mode)
```bash
# Get Jupyter pod name
JUPYTER_POD=$(oc get pods -n $NAMESPACE -l app=jupyter-notebook -o jsonpath='{.items[0].metadata.name}')

# Copy files to pod
oc cp retriever-tutorial.ipynb $JUPYTER_POD:/work -n $NAMESPACE
oc cp config.py $JUPYTER_POD:/work -n $NAMESPACE
oc cp env.donotcommit $JUPYTER_POD:/work -n $NAMESPACE

# Port-forward Jupyter
oc port-forward -n $NAMESPACE svc/jupyter-service 8888:8888
```

Access: http://localhost:8888 (token: `token`)

## Running LLM-as-a-Judge Demo

### 1. Configure Judge Demo
```bash
cd NeMo-Microservices/demos/custom-llm-as-a-judge
cp env.donotcommit.example env.donotcommit
```

Edit `env.donotcommit` and set:
```bash
NMS_NAMESPACE=<namespace>
NIM_SERVICE_ACCOUNT_TOKEN=<service-account-token>
NIM_MODEL_SERVING_SERVICE=<inferenceservice-name>
NIM_MODEL_SERVING_URL_EXTERNAL=<inferenceservice-url>
USE_NIM_MODEL_SERVING=true
USE_EXTERNAL_URL=true
```

**Find your InferenceService name:**
```bash
oc get inferenceservice -n $NAMESPACE
```

### 2. Run in Workbench/Notebook (Cluster Mode)
```bash
# Get Jupyter pod name
JUPYTER_POD=$(oc get pods -n $NAMESPACE -l app=jupyter-notebook -o jsonpath='{.items[0].metadata.name}')

# Copy files to pod
oc cp llm-as-a-judge-tutorial.ipynb $JUPYTER_POD:/work -n $NAMESPACE
oc cp config.py $JUPYTER_POD:/work -n $NAMESPACE
oc cp env.donotcommit $JUPYTER_POD:/work -n $NAMESPACE

# Copy data directory (if it exists)
if [ -d "data" ]; then
  oc cp data $JUPYTER_POD:/work -n $NAMESPACE
fi

# Port-forward Jupyter
oc port-forward -n $NAMESPACE svc/jupyter-service 8888:8888
```

Access: http://localhost:8888 (token: `token`)

## GPU Taints and Tolerations

### Apply GPU Taints to Nodes

If you need to apply GPU taints to nodes (e.g., to restrict which pods can schedule on GPU nodes):

```bash
# Apply nvidia.com/gpu taint to a GPU node
oc taint nodes <gpu-node-name> nvidia.com/gpu=true:NoSchedule

# Apply g5-gpu taint to a GPU node
oc taint nodes <gpu-node-name> g5-gpu=true:NoSchedule

# Apply g6e-gpu taint (e.g. some OpenShift GPU node types)
oc taint nodes <gpu-node-name> g6e-gpu=true:NoSchedule

# Apply both taints (if needed)
oc taint nodes <gpu-node-name> nvidia.com/gpu=true:NoSchedule g5-gpu=true:NoSchedule

# Check existing taints on nodes
oc get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints

# Example: Apply taints to all GPU nodes
for node in $(oc get nodes -o jsonpath='{.items[?(@.status.capacity."nvidia.com/gpu")].metadata.name}'); do
  oc taint nodes $node nvidia.com/gpu=true:NoSchedule --overwrite
done
```

**Note**: Pods must have matching tolerations to schedule on tainted nodes.

### Apply GPU Tolerations to InferenceService

If your cluster has GPU nodes with taints (e.g., `g5-gpu`, `g6e-gpu`, or `nvidia.com/gpu`), add tolerations to your InferenceService. (NIMCache/NIMPipeline from the nemo-instances chart already get these from `values.yaml` on fresh install.)

```bash
# Add GPU tolerations (g5-gpu, g6e-gpu, nvidia.com/gpu, master) for common OpenShift GPU nodes
oc patch inferenceservice <inferenceservice-name> -n $NAMESPACE --type='merge' -p='{"spec":{"predictor":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"g6e-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"},{"key":"node-role.kubernetes.io/master","operator":"Exists","effect":"NoSchedule"}]}}}'

# Example (replace with your actual InferenceService name and namespace):
# oc patch inferenceservice my-model -n my-namespace --type='merge' -p='{"spec":{"predictor":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"g6e-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"},{"key":"node-role.kubernetes.io/master","operator":"Exists","effect":"NoSchedule"}]}}}'

# IMPORTANT: Ensure only one instance is running
# When you patch the InferenceService, KServe may create a new revision while keeping the old one.
# You must scale down old revisions to 0 (scaling is preferred over deletion as deletion may not work)

# Find all predictor deployments (old and new revisions)
oc get deployment -n $NAMESPACE | grep <inferenceservice-name>-predictor

# Scale down old revision deployments to 0 (ensures only one instance is active)
oc scale deployment <deployment-name-old> -n $NAMESPACE --replicas=0

# Example (replace with your actual deployment name and namespace):
# oc scale deployment my-model-predictor-00001-deployment -n my-namespace --replicas=0

# Delete the pending pod to trigger recreation with new tolerations (if needed)
oc delete pod <pod-name-pending> -n $NAMESPACE

# Verify new pod is scheduled on GPU node
oc get pod <pod-name-new> -n $NAMESPACE -o wide
```

**Note**: Scaling down old deployments to 0 is preferred over deletion because:
- Deletion may not work if the deployment is managed by KServe
- Scaling to 0 ensures clean state while preserving the deployment for rollback if needed
- Only one active instance should be running at a time

### Apply GPU Tolerations to Notebook/Workbench

For Notebook or Workbench resources that are pending due to missing GPU tolerations:

```bash
# Patch Notebook CR to add GPU tolerations (g5-gpu, g6e-gpu, nvidia.com/gpu, master)
oc patch notebook <notebook-name> -n $NAMESPACE --type='merge' -p='{"spec":{"template":{"spec":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"g6e-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"},{"key":"node-role.kubernetes.io/master","operator":"Exists","effect":"NoSchedule"}]}}}}'

# Example (replace with your actual notebook name and namespace):
# oc patch notebook my-notebook -n my-namespace --type='merge' -p='{"spec":{"template":{"spec":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"g6e-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"},{"key":"node-role.kubernetes.io/master","operator":"Exists","effect":"NoSchedule"}]}}}}'

# Delete the pending pod to trigger recreation with new tolerations
oc delete pod <pod-name-pending> -n $NAMESPACE

# Verify the pod is scheduled and running
oc get pod <pod-name> -n $NAMESPACE -o wide
```

**Note**: If your pod shows "Pending" status with events mentioning "untolerated taint", you need to add the missing tolerations to the Notebook resource.

## Troubleshooting

### Check Service Status
```bash
oc get pods -n $NAMESPACE
oc get svc -n $NAMESPACE
oc get cr -n $NAMESPACE
```

### Check LlamaStack Logs
```bash
oc logs -n $NAMESPACE -l app=nemo-llamastack --tail=100
```

### LlamaStack CreateContainerConfigError

If LlamaStack pod shows `CreateContainerConfigError` with message about missing secret:

```bash
# Check if the service account token secret exists
oc get secret <inferenceservice-name>-sa-token-secret -n $NAMESPACE

# The secret is automatically created by Helm and populated by Kubernetes
# once the service account exists. If the secret exists but pod still fails:
# 1. Verify service account exists (created by InferenceService)
oc get sa <inferenceservice-name>-sa -n $NAMESPACE

# 2. Check if secret has token populated (should have data.token)
oc get secret <inferenceservice-name>-sa-token-secret -n $NAMESPACE -o jsonpath='{.data.token}' | wc -c
# Should be > 0

# 3. Delete the pod to trigger recreation once secret is populated
oc delete pod <llamastack-pod-name> -n $NAMESPACE
```

**Note**: This error is typically a timing issue. The Helm chart creates the secret, but Kubernetes needs the service account to exist first (created by InferenceService) to populate the token. The pod will automatically retry once the secret is populated.

### LlamaStack RBAC RoleBinding Error

If you encounter an error like:
```
Error: UPGRADE FAILED: failed to create resource: RoleBinding.rbac.authorization.k8s.io "-token-reader" is invalid: subjects[0].name: Required value
```

This indicates that the service account name was not properly set. **Solution**:

1. **Ensure you're using `llamastack.inferenceServiceName`** (not `llamastack.serviceAccountName`):
   ```bash
   helm upgrade nemo-instances . -n $NAMESPACE \
     --set namespace.name=$NAMESPACE \
     --set llamastack.enabled=true \
     --set llamastack.inferenceServiceName=$INFERENCESERVICE_NAME \
     --set llamastack.createServiceAccount=false \
     --reuse-values
   ```

2. **Verify the InferenceService name is correct**:
   ```bash
   export INFERENCESERVICE_NAME=$(oc get inferenceservice -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
   echo "Using InferenceService: $INFERENCESERVICE_NAME"
   ```

3. **The template auto-constructs all RBAC resources** (Role, RoleBinding) from `inferenceServiceName`:
   - Service account name: `<inferenceServiceName>-sa`
   - Role name: `<inferenceServiceName>-sa-token-reader`
   - RoleBinding name: `<inferenceServiceName>-sa-token-reader`

**Note**: The RBAC template automatically constructs the service account name from `inferenceServiceName`. You should not need to set `llamastack.serviceAccountName` manually unless you're using a custom service account name.

### Pod Stuck in Pending State (Missing GPU Tolerations)

If a pod is stuck in `Pending` state with events showing "untolerated taint":

**Note:** 
- **Fresh installs**: NIMCache, NIMPipeline, and Customizer workloads from the `nemo-instances` chart get GPU tolerations (g5-gpu, g6e-gpu, nvidia.com/gpu, master) from `values.yaml` automatically. **No separate patch commands are needed** for new resources created after install.
- **Existing resources**: If you have NIMCache, NIMPipeline, or NemoTrainingJob resources created before `values.yaml` was updated with g6e-gpu tolerations, you have two options:
  1. **Upgrade Helm release** (recommended): Run `helm upgrade nemo-instances` to update Customizer CR tolerations, then patch existing NemoTrainingJobs:
     ```bash
     # Upgrade to refresh Customizer CR tolerations
     cd NeMo-Microservices/deploy/nemo-instances
     helm upgrade nemo-instances . -n $NAMESPACE --set namespace.name=$NAMESPACE --set llamastack.enabled=false --reuse-values
     
     # Patch existing NemoTrainingJobs (if any are pending):
     for JOB in $(oc get nemotrainingjob -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}'); do
       oc patch nemotrainingjob $JOB -n $NAMESPACE --type='merge' -p='{"spec":{"trainingWorkload":{"trainerOverrides":{"spec":{"tolerations":[{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"},{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"g6e-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"node-role.kubernetes.io/master","operator":"Exists","effect":"NoSchedule"}]}}}}}'
     done
     ```
  2. **Manual patch**: Patch NIMCache, NIMPipeline, or NemoTrainingJob resources directly (see patches below).
- **Volcano controller stuck**: If Volcano Jobs exist, PodGroup is Inqueue, queue is Open, but no worker pods are created, the Volcano controller may be stuck. Restart it: `oc delete pod -n $NAMESPACE -l app.kubernetes.io/name=volcano,app.kubernetes.io/component=controllers`
- For InferenceService and Notebook (deployed separately), use the patches below.

```bash
# Check pod events to see why it's not scheduling
oc describe pod <pod-name> -n $NAMESPACE | grep -A 10 "Events:"

# Common error: "node(s) had untolerated taint {g5-gpu: true}", "{g6e-gpu: true}", or "nvidia.com/gpu"
# This means the pod needs GPU tolerations

# Check what resource owns the pod (Notebook, InferenceService, NIMCache, etc.)
oc get pod <pod-name> -n $NAMESPACE -o jsonpath='{.metadata.ownerReferences[*].kind}'

# For Notebook resources (use g5-gpu, g6e-gpu, nvidia.com/gpu, master for common OpenShift GPU nodes):
oc patch notebook <notebook-name> -n $NAMESPACE --type='merge' -p='{"spec":{"template":{"spec":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"g6e-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"},{"key":"node-role.kubernetes.io/master","operator":"Exists","effect":"NoSchedule"}]}}}}'

# For InferenceService:
oc patch inferenceservice <inferenceservice-name> -n $NAMESPACE --type='merge' -p='{"spec":{"predictor":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"g6e-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"},{"key":"node-role.kubernetes.io/master","operator":"Exists","effect":"NoSchedule"}]}}}'

# For NemoTrainingJob (Customizer training jobs) - if worker pods are pending:
# 1. Patch the NemoTrainingJob to add g6e-gpu and master tolerations:
oc patch nemotrainingjob <job-name> -n $NAMESPACE --type='merge' -p='{"spec":{"trainingWorkload":{"trainerOverrides":{"spec":{"tolerations":[{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"},{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"g6e-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"node-role.kubernetes.io/master","operator":"Exists","effect":"NoSchedule"}]}}}}}'

# 2. Delete the Volcano Job so operator recreates it with new tolerations:
VOLCANO_JOB=$(oc get job.batch.volcano.sh -n $NAMESPACE | grep <job-name> | awk '{print $1}')
oc delete job.batch.volcano.sh $VOLCANO_JOB -n $NAMESPACE

# 3. If worker pods still don't appear after Volcano Job is recreated, restart Volcano controller:
oc delete pod -n $NAMESPACE -l app.kubernetes.io/name=volcano,app.kubernetes.io/component=controllers

# After patching, delete the pending pod to trigger recreation
oc delete pod <pod-name> -n $NAMESPACE

# Verify pod is now scheduled
oc get pod <pod-name> -n $NAMESPACE -o wide
```

### Verify Service Account Token
```bash
# Check if token is set in env.donotcommit
grep NIM_SERVICE_ACCOUNT_TOKEN demos/*/env.donotcommit

# Verify token is valid
oc create token <service-account-name> -n $NAMESPACE --duration=8760h
```

### Verify Istio Mesh Membership
```bash
oc get servicemeshmember -n $NAMESPACE
```

### Check Operator Logs
```bash
# NeMo Operator
oc logs -n $NAMESPACE -l app.kubernetes.io/name=nemo-operator --tail=100

# NIM Operator
oc logs -n $NAMESPACE -l app.kubernetes.io/name=nim-operator --tail=100
```

## Cleanup and Uninstallation

### ⚠️ Important: Cleanup Order

**Always uninstall `nemo-instances` BEFORE `nemo-infra`** because:
- `nemo-instances` depends on infrastructure components
- Custom Resources in `nemo-instances` must be deleted first
- The pre-delete hook in `nemo-instances` handles CR cleanup automatically

### Complete Namespace Cleanup (Recommended)

This process cleans up everything including orphans (resources not managed by Helm). **Scale down deployments first** to ensure pods terminate quickly and the pre-delete hook doesn't get stuck:

```bash
# Set your namespace
export NAMESPACE=<namespace>

# Step 1: Scale down nemo-instances deployments (ensures pods terminate quickly)
echo "📉 Scaling down nemo-instances deployments..."
oc scale deployment -l app.kubernetes.io/instance=nemo-instances -n $NAMESPACE --replicas=0 --ignore-not-found=true

# Wait for pods to terminate
echo "⏳ Waiting for pods to terminate..."
sleep 5
oc wait --for=delete pod -l app.kubernetes.io/instance=nemo-instances -n $NAMESPACE --timeout=60s || true

# Step 2: Uninstall nemo-instances (pre-delete hook handles CR cleanup automatically)
echo "🗑️  Uninstalling nemo-instances..."
helm uninstall nemo-instances -n $NAMESPACE

# Step 3: Wait for cleanup to complete
echo "⏳ Waiting for cleanup to complete..."
sleep 10

# Step 4: Uninstall infrastructure
echo "🗑️  Uninstalling nemo-infra..."
helm uninstall nemo-infra -n $NAMESPACE

# Step 5: Clean up orphaned resources (not managed by Helm)
echo "🧹 Cleaning up orphaned resources..."

# Delete any remaining Custom Resources (orphans)
# Note: NIMService resources may have finalizers - remove them first if deletion fails
# This includes retriever NIMCache (nv-rerankqa-1b-v2) and NIMPipeline (retriever-rerankqa-pipeline)
oc delete nemocustomizer,nemodatastore,nemoentitystore,nemoevaluator,nemoguardrail,nimcache,nimpipeline,nimservice,inferenceservice --all -n $NAMESPACE --ignore-not-found=true --wait=false

# If NIMService deletion fails due to finalizers, remove them manually:
for NIMSERVICE in $(oc get nimservice -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
  echo "Removing finalizers from NIMService: $NIMSERVICE"
  oc patch nimservice $NIMSERVICE -n $NAMESPACE -p '{"metadata":{"finalizers":[]}}' --type=merge 2>/dev/null || true
  oc delete nimservice $NIMSERVICE -n $NAMESPACE --ignore-not-found=true --wait=false
done

# Delete orphaned deployments, replicasets, services, pods, jobs
oc delete deployment,replicaset,service,pod,job -l app.kubernetes.io/instance=nemo-instances -n $NAMESPACE --ignore-not-found=true --wait=false

# Delete orphaned configmaps, secrets, serviceaccounts, roles, rolebindings
oc delete configmap,secret,serviceaccount,role,rolebinding -l app.kubernetes.io/instance=nemo-instances -n $NAMESPACE --ignore-not-found=true

# Delete any remaining nemo-instances resources by name pattern
oc delete deployment,replicaset,service -n $NAMESPACE -l app.kubernetes.io/name=nemo-instances --ignore-not-found=true
oc delete configmap llamastack-config -n $NAMESPACE --ignore-not-found=true
oc delete secret sh.helm.release.v1.nemo-instances.* -n $NAMESPACE --ignore-not-found=true

# Delete orphaned cluster-scoped resources (if any)
oc delete clusterrole,clusterrolebinding -l app.kubernetes.io/instance=nemo-instances --ignore-not-found=true
oc delete validatingwebhookconfigurations,mutatingwebhookconfigurations -l app.kubernetes.io/instance=nemo-instances --ignore-not-found=true

# Step 6: Verify cleanup
echo "✅ Verifying cleanup..."
oc get all -n $NAMESPACE | grep -E "nemo-instances|llamastack" || echo "No nemo-instances resources found"
oc get cr -n $NAMESPACE
helm list -n $NAMESPACE

# Step 7: Clean up PVCs (Optional - preserves data by default)
# Uncomment to delete all PVCs:
# oc delete pvc --all -n $NAMESPACE
```

**Why scale down first?**
- The pre-delete hook waits for pods to terminate, but if deployments are still running, pods may not terminate quickly
- Scaling down ensures pods terminate immediately, allowing the cleanup hook to complete successfully
- This prevents the cleanup job from getting stuck waiting for pods that won't terminate

**What the pre-delete hook does automatically:**
- Deletes all Custom Resources (NemoCustomizer, NemoDatastore, etc.)
- Handles finalizers - automatically removes finalizers if they block deletion
- Waits for pods to terminate
- Cleans up cluster-scoped resources (ClusterRoles, ClusterRoleBindings, etc.)

### Quick Cleanup (Helm Only)

If you only want to uninstall Helm releases (pre-delete hook will handle CRs):

```bash
export NAMESPACE=<namespace>

# Step 1: Scale down deployments first (ensures cleanup doesn't get stuck)
oc scale deployment -l app.kubernetes.io/instance=nemo-instances -n $NAMESPACE --replicas=0 --ignore-not-found=true
sleep 5

# Step 2: Uninstall nemo-instances (pre-delete hook handles CR cleanup)
helm uninstall nemo-instances -n $NAMESPACE

# Step 3: Uninstall infrastructure
helm uninstall nemo-infra -n $NAMESPACE
```

### Manual Cleanup (If Hook Fails)

If the pre-delete hook fails or you need to manually clean up:

```bash
export NAMESPACE=<namespace>

# Step 1: Scale down all deployments first (ensures pods terminate)
echo "📉 Scaling down all nemo-instances deployments..."
oc scale deployment -l app.kubernetes.io/instance=nemo-instances -n $NAMESPACE --replicas=0 --ignore-not-found=true

# Step 2: Delete Custom Resources first (CRITICAL - must be done first)
echo "🗑️  Deleting Custom Resources..."
oc delete nemocustomizer,nemodatastore,nemoentitystore,nemoevaluator,nemoguardrail,nimcache,nimpipeline,inferenceservice --all -n $NAMESPACE --ignore-not-found=true

# Note: This includes retriever NIMCache (nv-rerankqa-1b-v2) and NIMPipeline (retriever-rerankqa-pipeline)

# Step 3: Wait for pods to terminate
echo "⏳ Waiting for pods to terminate..."
oc wait --for=delete pod -l app.kubernetes.io/instance=nemo-instances -n $NAMESPACE --timeout=300s || true

# Step 4: Uninstall Helm releases (in correct order)
echo "🗑️  Uninstalling Helm releases..."
helm uninstall nemo-instances -n $NAMESPACE || true
helm uninstall nemo-infra -n $NAMESPACE || true

# Step 5: Clean up remaining orphaned resources
echo "🧹 Cleaning up orphaned resources..."
oc delete deployment,replicaset,service,pod,job -l app.kubernetes.io/instance=nemo-instances -n $NAMESPACE --ignore-not-found=true
oc delete configmap,secret,serviceaccount,role,rolebinding -l app.kubernetes.io/instance=nemo-instances -n $NAMESPACE --ignore-not-found=true
oc delete configmap llamastack-config -n $NAMESPACE --ignore-not-found=true
oc delete secret sh.helm.release.v1.nemo-instances.* -n $NAMESPACE --ignore-not-found=true

# Step 6: Clean up cluster resources
echo "🧹 Cleaning up cluster resources..."
oc delete clusterrole,clusterrolebinding -l app.kubernetes.io/instance=nemo-instances --ignore-not-found=true
oc delete validatingwebhookconfigurations \
  volcano-admission-service-jobs-validate \
  volcano-admission-service-pods-validate \
  volcano-admission-service-queues-validate \
  --ignore-not-found=true
```

### Troubleshooting Stuck Resources

If resources are stuck after cleanup:

```bash
# Check for finalizers blocking deletion
oc get nemocustomizer -n $NAMESPACE -o jsonpath='{.items[*].metadata.finalizers}'

# Force delete by removing finalizers (use with caution)
oc patch nemocustomizer <name> -n $NAMESPACE -p '{"metadata":{"finalizers":[]}}' --type=merge

# Check for stuck pods
oc get pods -n $NAMESPACE

# Force delete stuck pods (if needed)
oc delete pod <pod-name> -n $NAMESPACE --force --grace-period=0
```

### TLS/mTLS Issues with Evaluator

If you encounter TLS/mTLS connection issues with the evaluator service, you may need to disable TLS for the evaluator service using an Istio DestinationRule.

**The Helm chart now includes this fix by default** (enabled in `values.yaml`). If you need to apply it manually:

```bash
# Create DestinationRule to disable TLS for evaluator
cat <<EOF | oc apply -f -
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: nemoevaluator-sample-plaintext
  namespace: $NAMESPACE
spec:
  host: nemoevaluator-sample.$NAMESPACE.svc.cluster.local
  trafficPolicy:
    tls:
      mode: DISABLE
EOF

# Verify the DestinationRule was created
oc get destinationrule -n $NAMESPACE | grep evaluator
```

**Note**: This is automatically applied when deploying with Helm if `evaluator.destinationRule.enabled: true` is set in `values.yaml` (which is the default).

### Clean Up PVCs (Optional)

PVCs are retained by default to preserve data. To delete them:

```bash
# List PVCs
oc get pvc -n $NAMESPACE

# Check if PVC is in use before deleting
# 1. Check for pods using the PVC
oc get pods -n $NAMESPACE -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .spec.volumes[*]}{.persistentVolumeClaim.claimName}{"\n"}{end}{end}' | grep <pvc-name>

# 2. Check for StatefulSets using the PVC
oc get statefulset -n $NAMESPACE -o yaml | grep <pvc-name>

# 3. Delete any dependent resources first (pods, StatefulSets, etc.)
# If PVC is used by a StatefulSet, delete the StatefulSet first
oc delete statefulset <statefulset-name> -n $NAMESPACE

# 4. Delete the PVC
oc delete pvc <pvc-name> -n $NAMESPACE

# If PVC deletion is stuck due to finalizers, remove finalizers (use with caution)
# oc patch pvc <pvc-name> -n $NAMESPACE -p '{"metadata":{"finalizers":[]}}' --type=merge
```

## Quick Reference

### Service Names and Ports

| Component | Service Name | Port |
|-----------|-------------|------|
| Data Store | `nemodatastore-sample` | 8000 |
| Entity Store | `nemoentitystore-sample` | 8000 |
| Customizer | `nemocustomizer-sample` | 8000 |
| Evaluator | `nemoevaluator-sample` | 8000 |
| Guardrails | `nemoguardrails-sample` | 8000 |
| Embedding NIM | `nv-embedqa-1b-v2` | 8000 |
| Retriever NIM | `nv-rerankqa-1b-v2` | 8000 |
| LlamaStack | `llamastack` | 8321 |
| Chat NIM | `<inferenceservice-name>-predictor` | 80 |

### Common Commands

```bash
# Set namespace
export NAMESPACE=<namespace>

# Check all pods
oc get pods -n $NAMESPACE

# Check services
oc get svc -n $NAMESPACE

# Check Custom Resources
oc get cr -n $NAMESPACE

# Get service account token
oc create token <service-account-name> -n $NAMESPACE --duration=8760h

# Get InferenceService URL
oc get inferenceservice <name> -n $NAMESPACE -o jsonpath='{.status.url}'
```

## Notes

- **Service Account Token**: Required for LlamaStack and NIM Model Serving authentication
- **Istio Sidecar**: LlamaStack requires Istio sidecar to communicate with KServe services
- **External URL**: Used for demos and as fallback when LlamaStack is unavailable
- **env.donotcommit**: These files are git-ignored and contain sensitive tokens - never commit them!

## Appendix: Placeholders Reference

This section provides a complete reference for all placeholders used throughout this guide. Refer to this when you encounter a placeholder you're not familiar with.

| Placeholder | Description | Example (from actual setup) | How to Get/Set |
|------------|-------------|----------------------------|----------------|
| `<namespace>` | Your OpenShift project/namespace name | `anemo-rhoai` | Create with `oc new-project <name>` or use existing: `oc projects` |
| `<ngc-api-key>` | NVIDIA NGC API key for pulling images and accessing NGC | `nvapi-...` (keep secret) | Get from [NGC Setup](https://ngc.nvidia.com/setup/api-key) |
| `<inferenceservice-name>` | Name of your KServe InferenceService | `anemo-rhoai-model` | Find with: `oc get inferenceservice -n $NAMESPACE` |
| `<service-account-name>` | Kubernetes ServiceAccount name (typically `<inferenceservice-name>-sa`) | `anemo-rhoai-model-sa` | Find with: `oc get sa -n $NAMESPACE \| grep <inferenceservice-name>` |
| `<service-account-token>` | Service account token for authentication | `eyJhbGciOiJ...` (keep secret) | Generate with: `oc create token <service-account-name> -n $NAMESPACE --duration=8760h` |
| `<inferenceservice-url>` | External URL of your InferenceService | `https://anemo-rhoai-model-anemo-rhoai.apps.ai-dev05.kni.syseng.devcluster.openshift.com` | Get with: `oc get inferenceservice <inferenceservice-name> -n $NAMESPACE -o jsonpath='{.status.url}'` |
| `<notebook-name>` | Name of your Notebook/Workbench resource | `anemo-rhoai-wb` | Find with: `oc get notebook -n $NAMESPACE` |
| `<pod-name-pending>` | Name of a pod stuck in Pending state | `anemo-rhoai-wb-0` | Find with: `oc get pods -n $NAMESPACE \| grep Pending` |
| `<pod-name-new>` | Name of newly created pod (after patching) | `anemo-rhoai-model-predictor-00002-deployment-db5b8b89f-hdh7h` | Find with: `oc get pods -n $NAMESPACE \| grep <resource-name>` |
| `<pod-name>` | Generic pod name (for troubleshooting) | `anemo-rhoai-wb-0` | Find with: `oc get pods -n $NAMESPACE` |
| `<deployment-name-old>` | Old deployment name (to scale down) | `anemo-rhoai-model-predictor-00001-deployment` | Find with: `oc get deployment -n $NAMESPACE \| grep <inferenceservice-name>-predictor` |
| `<gpu-node-name>` | GPU node name | `ip-10-0-12-250.ec2.internal` | Find with: `oc get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints \| grep gpu` |
