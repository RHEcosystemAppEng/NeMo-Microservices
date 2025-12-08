# Testing LlamaStack Dataset Registration with Data Store

This document explains how to test the LlamaStack dataset registration functionality with Data Store.

## Important Discovery

**LlamaStack's `client.beta.datasets.register()` requires files to be uploaded to Data Store FIRST.**

The registration API does NOT create the dataset - it only registers an existing dataset that already has files in Data Store.

## Test Script

A test script is provided: `test_datastore_llamastack.py`

### Prerequisites

1. **Port-forward Data Store and LlamaStack:**
   ```bash
   # Terminal 1: Port-forward Data Store
   oc port-forward -n <namespace> svc/nemodatastore-sample 8000:8000
   
   # Terminal 2: Port-forward LlamaStack
   oc port-forward -n <namespace> svc/llamastack 8321:8321
   ```

2. **Install dependencies:**
   ```bash
   pip install huggingface_hub llama-stack-client python-dotenv requests
   ```

3. **Set environment variables:**
   ```bash
   export NMS_NAMESPACE=your-namespace
   export DATASET_NAME=rag-tutorial-test
   export NDS_TOKEN=token
   export USE_PORT_FORWARD=true  # Set to false if running from within cluster
   ```

### Running the Test

```bash
cd demos/rag
python test_datastore_llamastack.py
```

### What the Test Does

1. **Tests Data Store connectivity** - Verifies Data Store is reachable
2. **Creates/verifies namespace** - Ensures namespace exists in Data Store
3. **Uploads sample file** - Uploads a test file to Data Store using HuggingFace API
4. **Tests LlamaStack connectivity** - Verifies LlamaStack is reachable
5. **Registers dataset with LlamaStack** - Tests the registration API
6. **Verifies dataset** - Confirms dataset exists in Data Store

### Expected Results

- ✅ All tests should pass if files are uploaded successfully
- ❌ Registration will fail if files are NOT uploaded first

## Updated RAG Demo Flow

The RAG demo has been updated to:

1. **Upload files to Data Store first** using HuggingFace API
2. **Then register with LlamaStack** (only if files were uploaded)
3. **Then register in Entity Store** (only if files were uploaded)

If file upload fails or `huggingface_hub` is not installed, the demo falls back to in-memory documents and skips LlamaStack/Entity Store registration.

## Key Learnings

1. **LlamaStack registration is NOT a file upload mechanism** - it only registers existing datasets
2. **Files must be uploaded first** using HuggingFace API or Data Store REST API
3. **The `hf://datasets/` URI format** references Data Store's HuggingFace-compatible API endpoint
4. **Entity Store registration** is separate and also requires the dataset to exist in Data Store first

## Troubleshooting

### Error: "Dataset not found" when registering with LlamaStack

**Cause:** Files were not uploaded to Data Store before registration.

**Solution:** Upload files to Data Store first using HuggingFace API:
```python
from huggingface_hub import HfApi
hf_api = HfApi(endpoint=f"{NDS_URL}/v1/hf", token=NDS_TOKEN)
hf_api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
hf_api.upload_file(path_or_fileobj=file_path, path_in_repo="file.json", 
                  repo_id=repo_id, repo_type="dataset")
```

### Error: "huggingface_hub not installed"

**Solution:** Install the package:
```bash
pip install huggingface_hub
```

### Error: Connection refused on port-forward

**Solution:** Make sure port-forward is active:
```bash
oc port-forward -n <namespace> svc/nemodatastore-sample 8000:8000
oc port-forward -n <namespace> svc/llamastack 8321:8321
```


