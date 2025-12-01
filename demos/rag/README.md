# RAG (Retrieval-Augmented Generation) Tutorial

This tutorial demonstrates how to build a RAG pipeline using NVIDIA NeMo Microservices on OpenShift.

> **Quick Start**: For a concise command reference for infrastructure, instances, and demos, see [../../commands.md](../../commands.md).

## Overview

This example implements a complete RAG workflow:
1. **Document Ingestion**: Upload documents to NeMo Data Store
2. **Embedding Generation**: Create embeddings using NeMo Embedding NIM
3. **Vector Storage**: Store embeddings in NeMo Entity Store
4. **Query Processing**: Retrieve relevant documents based on user queries
5. **Response Generation**: Generate answers using **LlamaStack client** (with fallback to direct Chat NIM) with retrieved context
6. **Optional Guardrails**: Apply safety guardrails to responses

## Prerequisites

### Deployed Services
- ✅ NeMo Data Store (v25.08+)
- ✅ NeMo Entity Store (v25.08+)
- ✅ NeMo Guardrails (v25.08+) - Optional but recommended
- ✅ **LlamaStack Server** - Unified API abstraction layer (deployed via Helm with Bearer token support)
- ✅ **KServe InferenceService** with `meta/llama-3.2-1b-instruct` model
  - Service name: Your InferenceService predictor service name
  - Must be accessible via Istio service mesh
  - LlamaStack must have Istio sidecar injected to communicate with KServe services
- ✅ Embedding NIM: `nv-embedqa-1b-v2` service

**Note**: The service name for the Chat NIM may differ from the model name. Find your service name:
```bash
oc get svc -n <your-namespace> | grep llama
oc get inferenceservice -n <your-namespace> | grep llama
```

### Required Configuration

#### 1. Service Account Token (REQUIRED for LlamaStack)

LlamaStack requires a Kubernetes service account token to authenticate with the KServe InferenceService. This token must be set in `env.donotcommit`:

**Get your service account token:**
```bash
# Replace <your-namespace> and <service-account-name> with your actual values
# The service account name is typically: <inferenceservice-name>-sa
oc create token <service-account-name> -n <your-namespace> --duration=8760h
```

**Example (replace with your actual service account and namespace):**
```bash
oc create token my-model-sa -n my-namespace --duration=8760h
```

**Add to `env.donotcommit`:**
```bash
NIM_SERVICE_ACCOUNT_TOKEN=eyJhbGciOiJSUzI1NiIsImtpZCI6...  # Your token here
```

#### 2. Model's External URL (REQUIRED for fallback)

The notebook uses the external HTTPS URL as a fallback when LlamaStack is unavailable. Find your InferenceService external URL:

```bash
# Get the external URL of your InferenceService
oc get inferenceservice <your-inferenceservice-name> -n <your-namespace> -o jsonpath='{.status.url}'
```

**Example:**
```bash
oc get inferenceservice my-model -n my-namespace -o jsonpath='{.status.url}'
# Example output: https://my-model-my-namespace.apps.my-cluster.example.com
```

**Add to `env.donotcommit` (if not auto-detected):**
The `config.py` file should auto-detect this, but you can override it if needed.

#### 3. Istio Service Mesh Membership

Your namespace must be a member of the Istio service mesh for LlamaStack to communicate with KServe InferenceService:

```bash
# Check if namespace is in the mesh
oc get servicemeshmember -n <your-namespace>

# If not, add it (requires cluster admin or service mesh admin)
# This is typically done during initial setup
```

#### 4. LlamaStack Configuration

**Important**: LlamaStack deployment depends on the InferenceService being deployed first. The LlamaStack pod will be in `Pending` state until the InferenceService creates the required service account.

LlamaStack must be deployed with:
- ✅ Istio sidecar injection enabled (`sidecar.istio.io/inject: "true"`)
- ✅ Bearer token authentication enabled (`llamastack.useBearerToken: true`)
- ✅ Service account token configured

These are typically configured in the Helm chart values. Verify LlamaStack deployment:

```bash
# Check LlamaStack pod status (may be Pending until InferenceService is deployed)
oc get pods -n <your-namespace> | grep llamastack

# Once deployed, verify Istio sidecar is present
oc get pod -n <your-namespace> -l app=nemo-llamastack -o jsonpath='{.items[0].spec.containers[*].name}'
# Should show: llamastack-ctr istio-proxy
```

**Note**: If LlamaStack pod is in `Pending` state with error about missing service account, this is expected. Deploy your InferenceService first, and LlamaStack will automatically deploy once the service account is created.

### Python Environment
- Python 3.8+
- Jupyter Lab
- `llama-stack-client` (installed automatically in notebook)

## Quick Start

### Option A: Run in Cluster (Recommended - Most Reliable)

Running the notebook inside the cluster is more reliable than port-forwards:

1. **Copy the notebook to the cluster Jupyter pod:**

```bash
# Replace <your-namespace> with your actual namespace (find with: oc projects)
NAMESPACE=<your-namespace>

# Get the Jupyter pod name
JUPYTER_POD=$(oc get pods -n $NAMESPACE -l app=jupyter-notebook -o jsonpath='{.items[0].metadata.name}')

# Copy the RAG demo files to the pod
oc cp demos/rag/rag-tutorial.ipynb $JUPYTER_POD:/work -n $NAMESPACE
oc cp demos/rag/config.py $JUPYTER_POD:/work -n $NAMESPACE
oc cp demos/rag/requirements.txt $JUPYTER_POD:/work -n $NAMESPACE
oc cp demos/rag/env.donotcommit.example $JUPYTER_POD:/work -n $NAMESPACE
```

2. **Access Jupyter in the cluster:**

```bash
# Port-forward Jupyter (one port-forward is more reliable than five)
# Replace <your-namespace> with your actual namespace
oc port-forward -n <your-namespace> svc/jupyter-service 8888:8888
```

3. **Open Jupyter in browser:** http://localhost:8888 (token: `token`)

4. **Install dependencies in the notebook:**

The notebook will auto-detect cluster mode and use cluster-internal service URLs. No port-forwards needed!

### Option B: Run Locally (Requires Port-Forwards)

**⚠️ Note:** Port-forwards can be unreliable. They may die if:
- Network connection drops
- Pods restart
- Connection times out

For better reliability, use Option A (run in-cluster).

1. **Install Dependencies**

```bash
cd NeMo-Microservices/demos/rag
pip install -r requirements.txt
```

2. **Configure Environment**

**🔒 SECURITY**: This demo uses `env.donotcommit` file for sensitive configuration. The file is git-ignored and will NOT be committed.

Create `env.donotcommit` file from the template:

```bash
# Copy the template
cp env.donotcommit.example env.donotcommit

# Edit env.donotcommit and fill in your values
```

**Required Configuration in `env.donotcommit`:**

1. **Namespace** (REQUIRED):
```bash
NMS_NAMESPACE=<your-namespace>
```
Find your namespace:
```bash
oc projects
```

2. **Service Account Token** (REQUIRED for LlamaStack):
```bash
NIM_SERVICE_ACCOUNT_TOKEN=<your-service-account-token>
```
Get your token:
```bash
# Replace with your actual service account name (typically: <inferenceservice-name>-sa)
# Example: oc create token my-model-sa -n my-namespace --duration=8760h
oc create token <service-account-name> -n <your-namespace> --duration=8760h
```

3. **Model External URL** (REQUIRED for fallback):
The external URL is typically auto-detected from the InferenceService, but you can verify:
```bash
oc get inferenceservice <your-inferenceservice-name> -n <your-namespace> -o jsonpath='{.status.url}'
```

**Optional Configuration:**
- `RUN_LOCALLY=false` - Set to `true` only if running locally with port-forwards
- `NDS_TOKEN=token` - NeMo Data Store token (default: "token")
- `DATASET_NAME=rag-tutorial-documents` - Dataset name for RAG documents
- `RAG_TOP_K=5` - Number of documents to retrieve
- `RAG_SIMILARITY_THRESHOLD=0.3` - Similarity threshold for retrieval

**Find your service names:**
```bash
# Chat NIM service (KServe InferenceService)
oc get inferenceservice -n <your-namespace>
oc get svc -n <your-namespace> | grep predictor

# Embedding NIM service
oc get svc -n <your-namespace> | grep embedqa
```

3. **Set Up Port-Forwards**

Run the improved port-forward script (monitors and reports issues):

```bash
./port-forward.sh
```

Or manually in separate terminals (more reliable):
```bash
# Replace <your-namespace> with your actual namespace
# Replace <your-chat-nim-service> with your actual Chat NIM service name (find with: oc get svc -n <namespace> | grep llama)

# Terminal 1
oc port-forward -n <your-namespace> svc/nemodatastore-sample 8001:8000

# Terminal 2
oc port-forward -n <your-namespace> svc/nemoentitystore-sample 8002:8000

# Terminal 3
oc port-forward -n <your-namespace> svc/nemoguardrails-sample 8005:8000

# Terminal 4 (Chat NIM - service name may vary)
oc port-forward -n <your-namespace> svc/<your-chat-nim-service> 8006:8000

# Terminal 5
oc port-forward -n <your-namespace> svc/nv-embedqa-1b-v2 8007:8000

# Terminal 6 (for LlamaStack)
oc port-forward -n <your-namespace> svc/llamastack 8321:8321
```

4. **Run the Notebook**

```bash
jupyter lab rag-tutorial.ipynb
```

## Configuration

The notebook uses `config.py` which automatically:
- Detects if running locally (port-forward) or in cluster
- Sets up service URLs accordingly
- Loads configuration from `env.donotcommit` file (git-ignored, secure)

**🔒 Security**: All sensitive values (tokens, API keys) are loaded from `env.donotcommit` file, which is git-ignored and will NOT be committed to version control.

### Service URLs

**Cluster Mode** (default):
- Data Store: `http://nemodatastore-sample.{namespace}.svc.cluster.local:8000`
- Entity Store: `http://nemoentitystore-sample.{namespace}.svc.cluster.local:8000`
- Guardrails: `http://nemoguardrails-sample.{namespace}.svc.cluster.local:8000`
- Chat NIM: `http://meta-llama3-1b-instruct.{namespace}.svc.cluster.local:8000`
- Embedding NIM: `http://nv-embedqa-1b-v2.{namespace}.svc.cluster.local:8000`
- LlamaStack: `http://llamastack.{namespace}.svc.cluster.local:8321`

**Local Mode** (with port-forwards):
- Data Store: `http://localhost:8001`
- Entity Store: `http://localhost:8002`
- Guardrails: `http://localhost:8005`
- Chat NIM: `http://localhost:8006`
- Embedding NIM: `http://localhost:8007`
- LlamaStack: `http://localhost:8321`

## RAG Workflow

### 1. Document Ingestion
- Upload documents (PDFs, text files, etc.) to NeMo Data Store
- Documents are stored in a namespace for organization

### 2. Embedding Generation
- Use NeMo Embedding NIM (`nv-embedqa-1b-v2`) to generate embeddings
- Each document chunk is converted to a vector representation

### 3. Vector Storage
- Store embeddings and metadata in NeMo Entity Store
- Entity Store provides vector similarity search capabilities

### 4. Query Processing
- User submits a query
- Query is embedded using the same embedding model
- Similarity search retrieves top-K most relevant documents

### 5. Response Generation
- Retrieved documents are used as context
- **LlamaStack client** generates a response using chat completions API (with fallback to direct NIM)
- Optional: Guardrails validate response safety

## Customization

### Adjusting Retrieval Parameters

```python
# In config.py or notebook
RAG_TOP_K = 5  # Number of documents to retrieve
RAG_SIMILARITY_THRESHOLD = 0.3  # Minimum similarity score
```

### Using Different Models

The notebook uses:
- **Chat Model**: `meta/llama-3.2-1b-instruct` (via NIM service)
- **Embedding Model**: `nv-embedqa-1b-v2` (via NIM service)

**Note**: The service name may differ from the model name. For example, the model `meta/llama-3.2-1b-instruct` might be deployed as service `meta-llama3-1b-instruct`. Find your service name:
```bash
oc get svc -n <your-namespace> | grep llama
```

To use different models, update the service names in `config.py` or set them in `env.donotcommit`.

### Adding Guardrails

Guardrails can be integrated to:
- Filter unsafe content
- Validate response quality
- Enforce compliance policies

## Troubleshooting

### Embedding NIM Not Available

If the embedding NIM service is not deployed:
1. Deploy it using the `nemo-instances` Helm chart with embedding NIM enabled
2. Or use fallback options (external API, HuggingFace embeddings)

### Documents Not Retrieving

- Verify documents were uploaded to Data Store
- Check embeddings were generated and stored in Entity Store
- Verify similarity threshold is not too high

### Service Connection Errors

- Verify all services are running: `oc get pods -n <your-namespace>`
- Check service URLs in `config.py` match your deployment
- Verify `env.donotcommit` file exists and has correct `NMS_NAMESPACE` value
- Ensure port-forwards are active (if running locally)
- **Port-forwards died?** They can be unreliable. Consider running the notebook in-cluster instead (Option A above)

### LlamaStack Connection Errors

If LlamaStack is failing with 500 errors or connection issues:

1. **Verify LlamaStack has Istio sidecar:**
```bash
oc get pod -n <your-namespace> -l app=nemo-llamastack -o jsonpath='{.items[0].spec.containers[*].name}'
# Should show: llamastack-ctr istio-proxy
```

2. **Verify service account token is set:**
```bash
# Check token is in env.donotcommit
grep NIM_SERVICE_ACCOUNT_TOKEN env.donotcommit

# Verify token is valid (should not be empty)
oc create token <service-account-name> -n <your-namespace> --duration=8760h
```

3. **Verify namespace is in Istio mesh:**
```bash
oc get servicemeshmember -n <your-namespace>
# Should show your namespace as a member
```

4. **Check LlamaStack logs:**
```bash
oc logs -n <your-namespace> -l app=nemo-llamastack --tail=100
```

5. **Verify KServe InferenceService is accessible:**
```bash
# Test from within the cluster (from a pod with Istio sidecar)
oc exec -n <your-namespace> <llamastack-pod> -- curl -s http://<predictor-service>.<namespace>.svc.cluster.local:80/v1/models
```

6. **Fallback works:** If LlamaStack fails, the notebook automatically falls back to direct NIM calls using the external HTTPS URL with the service account token.

### Port-Forward Issues

Port-forwards can be inconsistent because:
- They die when network connections drop
- They need restarting if pods restart
- Background processes can exit silently

**Solutions:**
1. **Best:** Run notebook in-cluster (Option A) - no port-forwards needed
2. **Alternative:** Run port-forwards in separate terminal windows (more visible)
3. **Monitor:** Use the improved `port-forward.sh` script which monitors and reports issues

## Version Compatibility

- **NeMo Data Store**: v25.08+
- **NeMo Entity Store**: v25.08+
- **NeMo Guardrails**: v25.08+
- **Chat NIM**: `meta/llama-3.2-1b-instruct:1.8.3` (service name may vary)
- **Embedding NIM**: `nvidia/llama-3.2-nv-embedqa-1b-v2` (via NIM service)

## LlamaStack Integration

This demo uses **LlamaStack** for chat completions, providing a unified API abstraction layer over NeMo microservices. The integration:

- **Uses LlamaStack client** for chat completions (with automatic fallback to direct NIM if LlamaStack is unavailable)
- **Uses direct NIM calls** for embeddings (as LlamaStack may not expose embeddings API directly)
- **Maintains backward compatibility** - works even if LlamaStack service is not deployed

### LlamaStack Benefits

- **Type safety**: Pydantic models instead of raw JSON
- **Unified API**: Single client for multiple NeMo services
- **Better error handling**: Typed exceptions
- **Simplified code**: Less boilerplate than direct REST calls

## Files

- `rag-tutorial.ipynb` - Main tutorial notebook
- `config.py` - Configuration file (auto-detects local vs cluster, includes LlamaStack URL)
- `requirements.txt` - Python dependencies (includes llama-stack-client)
- `port-forward.sh` - Port-forward script for local development
- `../../commands.md` - Quick command reference guide (concise version without detailed explanations)
- `env.donotcommit.example` - Template for environment configuration (copy to `env.donotcommit`)

## Documentation

- [NeMo Data Store](https://docs.nvidia.com/nemo/microservices/latest/datastore/overview.html)
- [NeMo Entity Store](https://docs.nvidia.com/nemo/microservices/latest/entity-store/overview.html)
- [NeMo Guardrails](https://docs.nvidia.com/nemo/microservices/latest/guardrails/overview.html)
- [NVIDIA NIM](https://developer.nvidia.com/docs/nemo-microservices/inference/overview.html)

