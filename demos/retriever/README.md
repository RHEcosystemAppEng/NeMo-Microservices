# NeMo Retriever Tutorial

This tutorial demonstrates how to use NVIDIA NeMo Retriever for text reranking to improve RAG (Retrieval-Augmented Generation) pipeline quality.

> **Quick Start**: For a concise command reference for infrastructure, instances, and demos, see [../../commands.md](../../commands.md).

## Overview

NeMo Retriever is a text reranking service that improves retrieval quality by reranking candidate documents based on their relevance to a query. This tutorial demonstrates:

1. **Text Reranking**: Use NeMo Retriever to rerank search results
2. **RAG Integration**: Improve RAG pipeline by reranking retrieved documents
3. **API Usage**: How to call the retriever API endpoint
4. **Performance Comparison**: Compare retrieval results with and without reranking

## Prerequisites

### Deployed Services
- ✅ **NeMo Retriever NIM**: `nv-rerankqa-1b-v2` service deployed (via `nemo-instances` Helm chart)
- ✅ **NeMo Entity Store** (optional, for RAG integration): `nemoentitystore-sample` service
- ✅ **Embedding NIM** (optional, for RAG integration): `nv-embedqa-1b-v2` service

**Verify retriever service is deployed:**
```bash
oc get svc -n <your-namespace> | grep rerankqa
oc get pods -n <your-namespace> | grep rerankqa
oc get nimcache nv-rerankqa-1b-v2 -n <your-namespace>
oc get nimpipeline retriever-rerankqa-pipeline -n <your-namespace>
```

### Required Configuration

#### 1. Service Account Token (Optional)

If your retriever service requires authentication, you may need a service account token:

```bash
# Get your service account token (if needed)
oc create token <service-account-name> -n <your-namespace> --duration=8760h
```

### Python Environment
- Python 3.8+
- Jupyter Lab
- `requests`, `numpy`, `python-dotenv` (installed automatically in notebook)

## Quick Start

### Run in Workbench/Notebook (Cluster Mode)

The notebook runs in a Workbench/Notebook within the cluster and uses cluster-internal service URLs.

1. **Copy the notebook to the Workbench/Notebook pod:**

```bash
# Replace <your-namespace> with your actual namespace (find with: oc projects)
NAMESPACE=<your-namespace>

# Get the Workbench/Notebook pod name
JUPYTER_POD=$(oc get pods -n $NAMESPACE -l app=jupyter-notebook -o jsonpath='{.items[0].metadata.name}')

# Copy the retriever demo files to the pod
oc cp demos/retriever/retriever-tutorial.ipynb $JUPYTER_POD:/work -n $NAMESPACE
oc cp demos/retriever/config.py $JUPYTER_POD:/work -n $NAMESPACE
oc cp demos/retriever/requirements.txt $JUPYTER_POD:/work -n $NAMESPACE
oc cp demos/retriever/env.donotcommit.example $JUPYTER_POD:/work -n $NAMESPACE
```

2. **Access Workbench/Notebook in the cluster:**

```bash
# Port-forward Workbench/Notebook
# Replace <your-namespace> with your actual namespace
oc port-forward -n <your-namespace> svc/jupyter-service 8888:8888
```

3. **Open Workbench/Notebook in browser:** http://localhost:8888 (token: `token`)

4. **Configure Environment**

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

**Optional Configuration:**
- `RETRIEVER_TOP_K=10` - Number of documents to rerank
- `RETRIEVER_TOP_N=5` - Number of top results to return after reranking
- `NIM_SERVICE_ACCOUNT_TOKEN=<token>` - Service account token if needed

## Configuration

The notebook uses `config.py` which:
- Sets up cluster-internal service URLs automatically
- Loads configuration from `env.donotcommit` file (git-ignored, secure)

**🔒 Security**: All sensitive values (tokens, API keys) are loaded from `env.donotcommit` file, which is git-ignored and will NOT be committed to version control.

### Service URLs

**Cluster Mode** (Workbench/Notebook within cluster):
- Retriever NIM: `http://nv-rerankqa-1b-v2.{namespace}.svc.cluster.local:8000`
- Entity Store: `http://nemoentitystore-sample.{namespace}.svc.cluster.local:8000` (optional)
- Embedding NIM: `http://nv-embedqa-1b-v2.{namespace}.svc.cluster.local:8000` (optional)

## Retriever API Usage

### Basic Reranking

The retriever API endpoint is `/v1/rerank`:

```python
import requests

retriever_url = "http://nv-rerankqa-1b-v2.<namespace>.svc.cluster.local:8000/v1/rerank"

payload = {
    "model": "nvidia/nv-rerankqa-1b-v2",
    "query": "What is machine learning?",
    "documents": [
        "Machine learning is a subset of AI...",
        "The weather today is sunny...",
        # ... more documents
    ],
    "top_n": 5  # Number of top results to return
}

response = requests.post(retriever_url, json=payload)
result = response.json()

# Result contains reranked documents with relevance scores
for item in result["results"]:
    score = item["relevance_score"]
    index = item["index"]
    document = documents[index]
    print(f"Score: {score:.4f} - {document}")
```

### RAG Pipeline Integration

1. **Initial Retrieval**: Use embedding model to get candidate documents
2. **Reranking**: Use retriever to rerank candidates by relevance
3. **Context Generation**: Use top reranked documents as context for LLM

```python
# Step 1: Get initial candidates using embeddings
query_embedding = get_embeddings([query], embedding_url)[0]
doc_embeddings = get_embeddings(documents, embedding_url)
similarities = [cosine_similarity(query_embedding, doc_emb) for doc_emb in doc_embeddings]
top_k_indices = np.argsort(similarities)[-10:][::-1]
candidates = [documents[i] for i in top_k_indices]

# Step 2: Rerank candidates
rerank_result = requests.post(retriever_url, json={
    "model": "nvidia/nv-rerankqa-1b-v2",
    "query": query,
    "documents": candidates,
    "top_n": 5
}).json()

# Step 3: Use top reranked documents as context
top_docs = [candidates[item["index"]] for item in rerank_result["results"]]
context = "\n\n".join(top_docs)
```

## Customization

### Adjusting Reranking Parameters

```python
# In config.py or notebook
RETRIEVER_TOP_K = 10  # Number of documents to rerank
RETRIEVER_TOP_N = 5   # Number of top results to return
```

### Using Different Models

The notebook uses:
- **Retriever Model**: `nvidia/nv-rerankqa-1b-v2` (via NIM service)

**Note**: The service name may differ from the model name. Find your service name:
```bash
oc get svc -n <your-namespace> | grep rerankqa
```

## Troubleshooting

### Retriever Service Not Available

If the retriever service is not deployed:
1. Deploy it using the `nemo-instances` Helm chart with retriever NIM enabled
2. Verify deployment:
   ```bash
   oc get nimcache nv-rerankqa-1b-v2 -n <namespace>
   oc get nimpipeline retriever-rerankqa-pipeline -n <namespace>
   oc get pods -n <namespace> | grep rerankqa
   ```

### API Connection Errors

- Verify service is running: `oc get pods -n <namespace> | grep rerankqa`
- Check service URL in `config.py` matches your deployment
- Verify `env.donotcommit` file exists and has correct `NMS_NAMESPACE` value
- Ensure you're running the notebook in a Workbench/Notebook within the cluster

### Invalid API Response

- Verify API endpoint is `/v1/rerank` (check NeMo Retriever documentation for latest endpoint)
- Check request payload format matches API specification
- Verify model name in payload: `"nvidia/nv-rerankqa-1b-v2"`

## Version Compatibility

- **NeMo Retriever NIM**: `nv-rerankqa-1b-v2:1.3.1` (via NIM service)
- **Embedding NIM** (optional): `nvidia/llama-3.2-nv-embedqa-1b-v2` (via NIM service)

## Files

- `retriever-tutorial.ipynb` - Main tutorial notebook
- `config.py` - Configuration file (cluster mode, includes retriever URL)
- `requirements.txt` - Python dependencies
- `env.donotcommit.example` - Template for environment configuration (copy to `env.donotcommit`)

## Documentation

- [NeMo Retriever](https://docs.nvidia.com/nemo/retriever/latest/)
- [NVIDIA NIM](https://developer.nvidia.com/docs/nemo-microservices/inference/overview.html)
