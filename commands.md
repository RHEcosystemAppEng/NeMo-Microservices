# NeMo Microservices - Quick Command Reference

This guide provides essential commands to deploy and configure NeMo Microservices on OpenShift. For detailed explanations, see the respective demo READMEs:
- [RAG Demo](demos/rag/README.md)
- [LLM-as-a-Judge Demo](demos/custom-llm-as-a-judge/README.md)

## Prerequisites

### 1. Verify Namespace
```bash
# Find your namespace
oc projects

# Set your namespace (replace <your-namespace> with actual value)
export NAMESPACE=<your-namespace>
```

### 2. Verify Namespace is in Istio Mesh
```bash
oc get servicemeshmember -n $NAMESPACE
# Should show your namespace as a member
```

## Infrastructure Installation

### 1. Install nemo-infra
```bash
cd NeMo-Microservices/deploy/nemo-infra
helm install nemo-infra . -n $NAMESPACE
```

### 2. Wait for Infrastructure (Optional - can proceed while starting)
```bash
# Check status
oc get pods -n $NAMESPACE | grep nemo-infra

# Wait for key components
oc wait --for=condition=ready pod -l app.kubernetes.io/instance=nemo-infra -n $NAMESPACE --timeout=300s
```

### 3. Verify Infrastructure is Ready
```bash
# Check all infrastructure pods
oc get pods -n $NAMESPACE | grep nemo-infra

# Verify operators are running
oc get pods -n $NAMESPACE | grep -E "operator|controller"
```

## Instances Installation

### 1. Install nemo-instances
```bash
cd NeMo-Microservices/deploy/nemo-instances
helm install nemo-instances . -n $NAMESPACE
```

### 2. Wait for Services to Start
```bash
# Monitor progress
watch oc get pods -n $NAMESPACE

# Or check specific services
oc get pods -n $NAMESPACE | grep -E "datastore|entitystore|customizer|evaluator|guardrail|llamastack"
```

### 3. Verify Services are Ready
```bash
# Check all NeMo service pods
oc get pods -n $NAMESPACE | grep -E "datastore|entitystore|customizer|evaluator|guardrail|llamastack"

# Check Custom Resources
oc get nemodatastore,nemoentitystore,nemocustomizer,nemoevaluator,nemoguardrail -n $NAMESPACE

# Check InferenceService (if deployed)
oc get inferenceservice -n $NAMESPACE
```

**Note**: LlamaStack deployment will be in `Pending` state until the InferenceService is deployed. Once the InferenceService is deployed and creates the service account (`<inferenceservice-name>-sa`), LlamaStack will automatically deploy. This is expected behavior.

## Configuration

### 1. Get Service Account Token (Required for LlamaStack and NIM Model Serving)
```bash
# Get the token (replace <service-account-name> with your actual SA name)
# Typically: <inferenceservice-name>-sa
oc create token <service-account-name> -n $NAMESPACE --duration=8760h

# Example:
# oc create token anemo-rhoai-model-sa -n anemo-rhoai --duration=8760h
```

**Save this token** - you'll need it for demo `env.donotcommit` files

### 2. Get InferenceService External URL (Required for demos)
```bash
# Get the external URL of your InferenceService
oc get inferenceservice <your-inferenceservice-name> -n $NAMESPACE -o jsonpath='{.status.url}'

# Example:
# oc get inferenceservice anemo-rhoai-model -n anemo-rhoai -o jsonpath='{.status.url}'
```

**Save this URL** - used for demos and fallback if LlamaStack is unavailable

### 3. Find Service Names
```bash
# Find Chat NIM service (KServe InferenceService)
oc get svc -n $NAMESPACE | grep predictor

# Find Embedding NIM service
oc get svc -n $NAMESPACE | grep embedqa

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

## Running RAG Demo

### 1. Configure RAG Demo
```bash
cd NeMo-Microservices/demos/rag
cp env.donotcommit.example env.donotcommit
```

Edit `env.donotcommit` and set:
```bash
NMS_NAMESPACE=<your-namespace>
NIM_SERVICE_ACCOUNT_TOKEN=<your-token-from-configuration-step-1>
RUN_LOCALLY=false  # Set to true only if running locally with port-forwards
```

### 2. Run in Cluster (Recommended)
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

### 3. Run Locally (Requires Port-Forwards)
```bash
# Set up port-forwards (run in separate terminals or use port-forward.sh script)
oc port-forward -n $NAMESPACE svc/nemodatastore-sample 8001:8000 &
oc port-forward -n $NAMESPACE svc/nemoentitystore-sample 8002:8000 &
oc port-forward -n $NAMESPACE svc/nemoguardrails-sample 8005:8000 &
oc port-forward -n $NAMESPACE svc/nv-embedqa-1b-v2 8007:8000 &
oc port-forward -n $NAMESPACE svc/llamastack 8321:8321 &

# Run notebook
jupyter lab rag-tutorial.ipynb
```

## Running LLM-as-a-Judge Demo

### 1. Configure Judge Demo
```bash
cd NeMo-Microservices/demos/custom-llm-as-a-judge
cp env.donotcommit.example env.donotcommit
```

Edit `env.donotcommit` and set:
```bash
NMS_NAMESPACE=<your-namespace>
NIM_SERVICE_ACCOUNT_TOKEN=<your-token-from-configuration-step-1>
NIM_MODEL_SERVING_SERVICE=<your-inferenceservice-name>
NIM_MODEL_SERVING_URL_EXTERNAL=<your-external-url-from-configuration-step-2>
USE_NIM_MODEL_SERVING=true
USE_EXTERNAL_URL=true
RUN_LOCALLY=false  # Set to true only if running locally with port-forwards
```

### 2. Run in Cluster (Recommended)
```bash
# Get Jupyter pod name
JUPYTER_POD=$(oc get pods -n $NAMESPACE -l app=jupyter-notebook -o jsonpath='{.items[0].metadata.name}')

# Copy files to pod
oc cp llm-as-a-judge-tutorial.ipynb $JUPYTER_POD:/work -n $NAMESPACE
oc cp config.py $JUPYTER_POD:/work -n $NAMESPACE
oc cp env.donotcommit $JUPYTER_POD:/work -n $NAMESPACE

# Port-forward Jupyter
oc port-forward -n $NAMESPACE svc/jupyter-service 8888:8888
```

Access: http://localhost:8888 (token: `token`)

### 3. Run Locally (Requires Port-Forwards)
```bash
# Set up port-forwards
oc port-forward -n $NAMESPACE svc/nemodatastore-sample 8001:8000 &
oc port-forward -n $NAMESPACE svc/nemoentitystore-sample 8002:8000 &
oc port-forward -n $NAMESPACE svc/nemoevaluator-sample 8004:8000 &
oc port-forward -n $NAMESPACE svc/llamastack 8321:8321 &

# Run notebook
jupyter lab llm-as-a-judge-tutorial.ipynb
```

## GPU Taints and Tolerations

### Apply GPU Taints to Nodes

If you need to apply GPU taints to nodes (e.g., to restrict which pods can schedule on GPU nodes):

```bash
# Apply nvidia.com/gpu taint to a GPU node
oc taint nodes <node-name> nvidia.com/gpu=true:NoSchedule

# Apply g5-gpu taint to a GPU node
oc taint nodes <node-name> g5-gpu=true:NoSchedule

# Apply both taints (if needed)
oc taint nodes <node-name> nvidia.com/gpu=true:NoSchedule g5-gpu=true:NoSchedule

# Check existing taints on nodes
oc get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints

# Example: Apply taints to all GPU nodes
for node in $(oc get nodes -o jsonpath='{.items[?(@.status.capacity."nvidia.com/gpu")].metadata.name}'); do
  oc taint nodes $node nvidia.com/gpu=true:NoSchedule --overwrite
done
```

**Note**: Pods must have matching tolerations to schedule on tainted nodes.

### Apply GPU Tolerations to InferenceService

If your cluster has GPU nodes with taints (e.g., `g5-gpu=true:NoSchedule` or `nvidia.com/gpu=true:NoSchedule`), you need to add tolerations to your InferenceService:

```bash
# Add GPU tolerations to InferenceService (for both g5-gpu and nvidia.com/gpu taints)
oc patch inferenceservice <inferenceservice-name> -n $NAMESPACE --type='merge' -p='{"spec":{"predictor":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"}]}}}'

# Example:
# oc patch inferenceservice anemo-rhoai-model -n anemo-rhoai --type='merge' -p='{"spec":{"predictor":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"}]}}}'

# Delete the pending pod to trigger recreation with new toleration
oc delete pod <pending-pod-name> -n $NAMESPACE

# If there are multiple revisions (old and new), scale down the old revision to 0
# Find the old revision deployment name
oc get deployment -n $NAMESPACE | grep <inferenceservice-name>-predictor

# Scale down the old revision
oc scale deployment <old-revision-deployment-name> -n $NAMESPACE --replicas=0

# Example:
# oc scale deployment anemo-rhoai-model-predictor-00001-deployment -n anemo-rhoai --replicas=0

# Verify new pod is scheduled on GPU node
oc get pod <new-pod-name> -n $NAMESPACE -o wide
```

### Apply GPU Tolerations to Notebook/Workbench

For Notebook or Workbench resources that are pending due to missing GPU tolerations:

```bash
# Patch Notebook CR to add GPU tolerations (for both g5-gpu and nvidia.com/gpu taints)
oc patch notebook <notebook-name> -n $NAMESPACE --type='merge' -p='{"spec":{"template":{"spec":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"}]}}}}'

# Example:
# oc patch notebook anemo-rhoai-wb -n anemo-rhoai --type='merge' -p='{"spec":{"template":{"spec":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"}]}}}}'

# Delete the pending pod to trigger recreation with new tolerations
oc delete pod <pending-pod-name> -n $NAMESPACE

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

### Pod Stuck in Pending State (Missing GPU Tolerations)

If a pod is stuck in `Pending` state with events showing "untolerated taint":

```bash
# Check pod events to see why it's not scheduling
oc describe pod <pod-name> -n $NAMESPACE | grep -A 10 "Events:"

# Common error: "node(s) had untolerated taint {g5-gpu: true}" or "nvidia.com/gpu"
# This means the pod needs GPU tolerations

# Check what resource owns the pod (Notebook, InferenceService, etc.)
oc get pod <pod-name> -n $NAMESPACE -o jsonpath='{.metadata.ownerReferences[*].kind}'

# For Notebook resources:
oc patch notebook <notebook-name> -n $NAMESPACE --type='merge' -p='{"spec":{"template":{"spec":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"}]}}}}'

# For InferenceService:
oc patch inferenceservice <inferenceservice-name> -n $NAMESPACE --type='merge' -p='{"spec":{"predictor":{"tolerations":[{"key":"g5-gpu","operator":"Equal","value":"true","effect":"NoSchedule"},{"key":"nvidia.com/gpu","operator":"Exists","effect":"NoSchedule"}]}}}'

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

## Uninstallation

### Uninstall nemo-instances
```bash
helm uninstall nemo-instances -n $NAMESPACE
```

### Uninstall nemo-infra
```bash
helm uninstall nemo-infra -n $NAMESPACE
```

### Clean Up PVCs (Optional)
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
| LlamaStack | `llamastack` | 8321 |
| Chat NIM | `<inferenceservice-name>-predictor` | 80 |

### Common Commands

```bash
# Set namespace
export NAMESPACE=<your-namespace>

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
