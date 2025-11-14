# RAG (Retrieval-Augmented Generation) Tutorial

This tutorial demonstrates how to build a RAG pipeline using NVIDIA NeMo Microservices on OpenShift.

## Overview

This example implements a complete RAG workflow:
1. **Document Ingestion**: Upload documents to NeMo Data Store
2. **Embedding Generation**: Create embeddings using NeMo Embedding NIM
3. **Vector Storage**: Store embeddings in NeMo Entity Store
4. **Query Processing**: Retrieve relevant documents based on user queries
5. **Response Generation**: Generate answers using NeMo Chat NIM with retrieved context
6. **Optional Guardrails**: Apply safety guardrails to responses

## Prerequisites

### Deployed Services
- ✅ NeMo Data Store (v25.08+)
- ✅ NeMo Entity Store (v25.08+)
- ✅ NeMo Guardrails (v25.08+) - Optional but recommended
- ✅ Chat NIM: `meta-llama3-1b-instruct` service
- ✅ Embedding NIM: `nv-embedqa-e5-v5` service

### Python Environment
- Python 3.8+
- Jupyter Lab

## Quick Start

### Option A: Run in Cluster (Recommended - Most Reliable)

Running the notebook inside the cluster is more reliable than port-forwards:

1. **Copy the notebook to the cluster Jupyter pod:**

```bash
# Get the Jupyter pod name
JUPYTER_POD=$(oc get pods -n anemo-rhoai -l app=jupyter-notebook -o jsonpath='{.items[0].metadata.name}')

# Copy the RAG demo files to the pod
oc cp demos/rag/rag-tutorial.ipynb $JUPYTER_POD:/work -n anemo-rhoai
oc cp demos/rag/config.py $JUPYTER_POD:/work -n anemo-rhoai
oc cp demos/rag/requirements.txt $JUPYTER_POD:/work -n anemo-rhoai
```

2. **Access Jupyter in the cluster:**

```bash
# Port-forward Jupyter (one port-forward is more reliable than five)
oc port-forward -n anemo-rhoai svc/jupyter-service 8888:8888
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

Create a `.env` file (or set environment variables):

```bash
# Required
NMS_NAMESPACE=anemo-rhoai

# Optional
RUN_LOCALLY=true  # Set to true for local development with port-forwards
DATASET_NAME=rag-tutorial-documents
NDS_TOKEN=token
```

3. **Set Up Port-Forwards**

Run the improved port-forward script (monitors and reports issues):

```bash
./port-forward.sh
```

Or manually in separate terminals (more reliable):
```bash
# Terminal 1
oc port-forward -n anemo-rhoai svc/nemodatastore-sample 8001:8000

# Terminal 2
oc port-forward -n anemo-rhoai svc/nemoentitystore-sample 8002:8000

# Terminal 3
oc port-forward -n anemo-rhoai svc/nemoguardrails-sample 8005:8000

# Terminal 4
oc port-forward -n anemo-rhoai svc/meta-llama3-1b-instruct 8006:8000

# Terminal 5
oc port-forward -n anemo-rhoai svc/nv-embedqa-e5-v5 8007:8000
```

4. **Run the Notebook**

```bash
jupyter lab rag-tutorial.ipynb
```

## Configuration

The notebook uses `config.py` which automatically:
- Detects if running locally (port-forward) or in cluster
- Sets up service URLs accordingly
- Loads API keys from environment variables

### Service URLs

**Cluster Mode** (default):
- Data Store: `http://nemodatastore-sample.{namespace}.svc.cluster.local:8000`
- Entity Store: `http://nemoentitystore-sample.{namespace}.svc.cluster.local:8000`
- Guardrails: `http://nemoguardrails-sample.{namespace}.svc.cluster.local:8000`
- Chat NIM: `http://meta-llama3-1b-instruct.{namespace}.svc.cluster.local:8000`
- Embedding NIM: `http://nv-embedqa-e5-v5.{namespace}.svc.cluster.local:8000`

**Local Mode** (with port-forwards):
- Data Store: `http://localhost:8001`
- Entity Store: `http://localhost:8002`
- Guardrails: `http://localhost:8005`
- Chat NIM: `http://localhost:8006`
- Embedding NIM: `http://localhost:8007`

## RAG Workflow

### 1. Document Ingestion
- Upload documents (PDFs, text files, etc.) to NeMo Data Store
- Documents are stored in a namespace for organization

### 2. Embedding Generation
- Use NeMo Embedding NIM (`nv-embedqa-e5-v5`) to generate embeddings
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
- Chat NIM generates a response based on query + context
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
- **Chat Model**: `meta-llama3-1b-instruct` (via NIM service)
- **Embedding Model**: `nv-embedqa-e5-v5` (via NIM service)

To use different models, update the service names in `config.py`.

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

- Verify all services are running: `oc get pods -n <namespace>`
- Check service URLs in `config.py` match your deployment
- Ensure port-forwards are active (if running locally)
- **Port-forwards died?** They can be unreliable. Consider running the notebook in-cluster instead (Option A above)

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
- **Chat NIM**: meta/llama-3.2-1b-instruct:1.8.3
- **Embedding NIM**: nvidia/nv-embedqa-e5-v5:1.0.1

## Files

- `rag-tutorial.ipynb` - Main tutorial notebook
- `config.py` - Configuration file (auto-detects local vs cluster)
- `requirements.txt` - Python dependencies
- `port-forward.sh` - Port-forward script for local development

## Documentation

- [NeMo Data Store](https://docs.nvidia.com/nemo/microservices/latest/datastore/overview.html)
- [NeMo Entity Store](https://docs.nvidia.com/nemo/microservices/latest/entity-store/overview.html)
- [NeMo Guardrails](https://docs.nvidia.com/nemo/microservices/latest/guardrails/overview.html)
- [NVIDIA NIM](https://developer.nvidia.com/docs/nemo-microservices/inference/overview.html)

