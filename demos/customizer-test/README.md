# NeMo Customizer Service Test

A simple notebook to test and verify the NeMo Customizer service is working correctly.

## End-to-end workflow (steps we followed)

We ran `customize-model.ipynb` first, used scripts to download the customized model, merged the adapter with the base model, uploaded the merged model to MinIO, redeployed SSR, then tested with `test-customized-model.ipynb`.

1. **Run `customize-model.ipynb`** (training)  
   In Workbench/Notebook: run all cells. Uploads training data, creates customization job, waits for completion. Note the customized model name (or job ID).

2. **Download customized model** (scripts, from your machine)  
   With port-forwards running (`./setup_port_forwards.sh`):
   ```bash
   python export_model_from_entity_store.py          # auto-finds last completed job; or --job-id <id>
   python download_model_from_datastore.py --model-info model_info.json --output-dir ./downloaded_model
   ```
   **Note:** Job ID from the Customizer API is case-sensitive (e.g. `cust-DTR3HNmLYwkPtdNEvoUrzS`). Get it from `curl -s http://localhost:8003/v1/customization/jobs` if using `--job-id`.

3. **Merge customized adapter with base model** (script)  
   Merge the downloaded adapter and base model into a full model:
   ```bash
   python merge_adapter_with_base.py --adapter-dir ./downloaded_model --output-dir ./merged_model
   ```

4. **Upload merged model to MinIO** (script)  
   With MinIO port-forward (e.g. from `./setup_port_forwards.sh`):
   ```bash
   MINIO_ENDPOINT=http://localhost:9000 python upload_model_to_minio.py --model-dir ./merged_model --target-path models/llama-3.2-1b-instruct-cust
   ```

5. **Redeploy SSR** (point InferenceService at the new MinIO path)  
   ```bash
   oc patch inferenceservice <inferenceservice-name> -n $NAMESPACE --type='json' -p='[{"op":"replace","path":"/spec/predictor/model/storage/path","value":"models/llama-3.2-1b-instruct-cust"}]'
   oc delete pod -n $NAMESPACE -l serving.kserve.io/inferenceservice=<inferenceservice-name>
   ```

6. **Test with `test-customized-model.ipynb`**  
   Run the notebook: it uses the same 3 Red Hat privacy prompts as the base model and saves responses to `customized_model_responses.json` / `.txt` for comparison with `base_model_responses.*` from `customize-model.ipynb` Step 12.

Download, merge, and upload are done via **scripts** (not the notebooks) because privileged `oc` or cluster access may not be available from the notebook environment.

## Overview

This demo performs connectivity and functionality tests for the NeMo Customizer service:

1. **Health Check**: Verifies the customizer service is running and healthy
2. **API Information**: Retrieves API version and capabilities
3. **Jobs Listing**: Lists existing customization jobs
4. **Dependencies**: Tests connectivity to required services (DataStore, Entity Store)

## Prerequisites

- ✅ NeMo Customizer service deployed and running
- ✅ NeMo Data Store service deployed and running
- ✅ NeMo Entity Store service deployed and running
- ✅ Access to the cluster namespace (running from Workbench/Notebook within cluster)
- ✅ Python dependencies (for export scripts):
  ```bash
  pip install requests python-dotenv huggingface_hub boto3
  ```

## Quick Start

### 0. Setup Port Forwards (For Local Development)

If running export scripts from your local machine, set up port-forwards first:

```bash
# Option 1: Use the setup script (recommended)
./setup_port_forwards.sh

# Option 2: Manual port-forwards
oc port-forward -n $NAMESPACE svc/nemodatastore-sample 8001:8000 &
oc port-forward -n $NAMESPACE svc/nemoentitystore-sample 8002:8000 &
oc port-forward -n $NAMESPACE svc/nemocustomizer-sample 8003:8000 &
```

Then set environment variables:
```bash
export DATASTORE_URL=http://localhost:8001
export ENTITY_STORE_URL=http://localhost:8002
export CUSTOMIZER_URL=http://localhost:8003
```

Or add to `env.donotcommit`:
```bash
DATASTORE_URL=http://localhost:8001
ENTITY_STORE_URL=http://localhost:8002
CUSTOMIZER_URL=http://localhost:8003
```

**Note:** Port-forwards must stay running while using the export scripts.

### 1. Configure Environment

```bash
cd NeMo-Microservices/demos/customizer-test
cp env.donotcommit.example env.donotcommit
```

Edit `env.donotcommit` and set:
```bash
NMS_NAMESPACE=your-namespace  # Set to your OpenShift project/namespace
```

### 2. Run in Workbench/Notebook (Cluster Mode)

```bash
# Get Jupyter pod name
JUPYTER_POD=$(oc get pods -n $NAMESPACE -l app=jupyter-notebook -o jsonpath='{.items[0].metadata.name}')

# Copy files to pod
oc cp customize-model.ipynb $JUPYTER_POD:/work -n $NAMESPACE
oc cp config.py $JUPYTER_POD:/work -n $NAMESPACE
oc cp env.donotcommit $JUPYTER_POD:/work -n $NAMESPACE

# Port-forward Jupyter
oc port-forward -n $NAMESPACE svc/jupyter-service 8888:8888
```

Access: http://localhost:8888 (token: `token`)

### 3. Verify Services

Before running the notebook, verify services are running:

```bash
# Check Customizer
oc get pods -n $NAMESPACE | grep customizer | grep -v postgresql | grep -v mlflow

# Check DataStore
oc get pods -n $NAMESPACE | grep datastore | grep -v postgresql

# Check Entity Store
oc get pods -n $NAMESPACE | grep entitystore | grep -v postgresql
```

## What the Notebook Tests

### 1. Service Health
- Tests `/health` endpoint
- Verifies service is responding

### 2. API Information
- Tests `/v1/info` endpoint
- Retrieves API version and capabilities

### 3. Jobs Listing
- Tests `/v1/customization/jobs` endpoint
- Lists existing customization jobs

### 4. Dependencies
- Tests DataStore connectivity (required for dataset operations)
- Tests Entity Store connectivity (required for model registration)

## Expected Results

If all tests pass, you should see:
- ✅ Customizer service is healthy!
- ✅ API Information retrieved successfully
- ✅ Jobs listing works (may show 0 jobs for fresh deployment)
- ✅ DataStore service is healthy!
- ✅ Entity Store service is healthy!

## Troubleshooting

### Model Download Issues

**Problem**: Download script reports "Repository appears to be empty" or only finds metadata files.

**Solution**: EntityHandler exports models with revision tags (e.g., `@1.0`). Make sure your `files_url` includes the revision:

```bash
# ✅ Correct - includes revision
python download_model_from_datastore.py --files-url "hf://$NAMESPACE/model-name@1.0" --output-dir ./downloaded_model

# ❌ Incorrect - missing revision
python download_model_from_datastore.py --files-url "hf://$NAMESPACE/model-name" --output-dir ./downloaded_model
```

If `model_info.json` has a `files_url` without revision, extract it from the `model_name` field:
```bash
# model_name: "$NAMESPACE/model-name@1.0"
# Extract @1.0 and append to files_url
python download_model_from_datastore.py --files-url "hf://$NAMESPACE/model-name@1.0" --output-dir ./downloaded_model
```

**Problem**: Model not found in DataStore.

**Solution**: Check EntityHandler logs to verify export completed:
```bash
oc logs -n anemo-rhoai <job-id>-entity-handler-1-<pod-suffix> | grep -i "upload\|export\|completed"
```

If EntityHandler failed, the model may not be available in DataStore; ensure the customization job completed and EntityHandler ran successfully before retrying the download.

### Service Not Responding

If the customizer service is not responding:

```bash
# Check pod status
oc get pods -n $NAMESPACE | grep nemocustomizer-sample

# Check service
oc get svc nemocustomizer-sample -n anemo-rhoai

# Check logs
oc logs -n anemo-rhoai -l app.kubernetes.io/name=nemocustomizer-sample --tail=50
```

### Connection Errors

If you see connection errors:
- Verify you're running the notebook from within the cluster (Workbench/Notebook)
- Check the namespace matches your deployment: `oc get nemocustomizer -n $NAMESPACE`
- Verify service names match: `oc get svc -n $NAMESPACE | grep customizer`

## Workflow Overview

This demo consists of two notebooks plus scripts:

1. **`customize-model.ipynb`** - Training Phase (Steps 1–17)
   - Customizes the model using Customizer service
   - Uploads training data to DataStore
   - Creates and monitors customization job
   - Outputs customized model name (or job ID)

2. **Scripts** (run from your machine with port-forwards): export → download → merge → upload to MinIO; then patch InferenceService and restart SSR pod (see [End-to-end workflow](#end-to-end-workflow-steps-we-follow) above).

3. **`test-customized-model.ipynb`** - Testing Phase
   - Tests the customized model (already deployed to MinIO and served by SSR)
   - Compares responses with base model

**Important**: EntityHandler automatically exports customized models to DataStore after training completes. The model files are stored with a revision tag (e.g., `@1.0`). The export and download scripts handle this; you must merge the adapter with the base model and upload the merged model to MinIO before testing.

## Complete Workflow

### Step 1: Run Training Notebook

Execute `customize-model.ipynb` to train/customize your model:

```bash
# In Jupyter Notebook, run all cells in customize-model.ipynb
# This will:
# - Upload training data
# - Create customization job
# - Wait for job completion
# - Output the customized model name
```

**Expected Output:**
- Customized model name (e.g., `$NAMESPACE/llama-3.2-1b-instruct-custom-1234567890-12345@1.0`)
- Job completion status
- Model automatically exported to DataStore by EntityHandler (with `@1.0` revision)
- Model metadata registered in Entity Store (if EntityHandler completed successfully)

### Step 2: Export Customized Model

After training completes, you need to export the model from Entity Store/DataStore, merge with base model, and deploy to MinIO.

**Use individual scripts (from your machine with port-forwards):**

#### 2.1 Get Customized Model Information

**Using Python Script:**
```bash
python export_model_from_entity_store.py --model-name "$NAMESPACE/llama-3.2-1b-instruct-custom-1234567890-12345@1.0"
```

This will:
- Query Entity Store for model information (or Customizer job if not in Entity Store)
- Extract `files_url` pointing to DataStore
- **Note**: If `files_url` doesn't include revision, construct it from `model_name` (which includes `@1.0`)
- Save model info to `model_info.json`

**Auto Mode (Recommended):**
```bash
# Automatically finds and exports the last completed job
python export_model_from_entity_store.py
```

**Or manually:**

From the training notebook output, note the customized model name. Then query Entity Store:

```python
# In a Python script or notebook cell
import requests
import os

NMS_NAMESPACE = os.getenv("NMS_NAMESPACE", "anemo-rhoai")
ENTITY_STORE_URL = f"http://nemoentitystore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
CUSTOMIZED_MODEL_NAME = "$NAMESPACE/llama-3.2-1b-instruct-custom-1234567890-12345@1.0"  # From training notebook

# Parse model name
if "@" in CUSTOMIZED_MODEL_NAME:
    model_namespace, model_name_version = CUSTOMIZED_MODEL_NAME.split("/", 1)
    model_name, model_version = model_name_version.split("@", 1)
else:
    if "/" in CUSTOMIZED_MODEL_NAME:
        model_namespace, model_name = CUSTOMIZED_MODEL_NAME.split("/", 1)
    else:
        model_namespace = NMS_NAMESPACE
        model_name = CUSTOMIZED_MODEL_NAME
    model_version = "1.0"

# Get model info from Entity Store
model_path = f"{model_namespace}/{model_name}"
response = requests.get(f"{ENTITY_STORE_URL}/v1/models/{model_path}", timeout=30)

if response.status_code == 200:
    model_info = response.json()
    files_url = model_info.get('artifact', {}).get('files_url')
    print(f"✅ Model found in Entity Store")
    print(f"   Files URL: {files_url}")
else:
    print(f"⚠️  Model not found: {response.status_code}")
```

#### 2.2 Download Model from DataStore

**Using Python Script:**
```bash
python download_model_from_datastore.py --model-info model_info.json --output-dir ./downloaded_model
```

Or specify files_url directly (include revision if present):
```bash
# With revision (recommended - EntityHandler exports models with @1.0 revision)
python download_model_from_datastore.py --files-url "hf://$NAMESPACE/llama-3.2-1b-instruct-custom-1234567890-12345@1.0" --output-dir ./downloaded_model

# Without revision (will try to download from default branch)
python download_model_from_datastore.py --files-url "hf://$NAMESPACE/model-name" --output-dir ./downloaded_model
```

**Important Notes:**
- EntityHandler automatically exports customized models to DataStore with a revision tag (e.g., `@1.0`)
- The download script automatically extracts and uses the revision from the `files_url`
- If `model_info.json` has a `files_url` without revision, you can construct it from the `model_name` field (which includes `@1.0`)

**Or manually:**

The `files_url` from Entity Store typically points to DataStore using the `hf://` format. EntityHandler exports models with revision tags (e.g., `@1.0`). Download using HuggingFace API:

```python
from huggingface_hub import HfApi, snapshot_download
import tempfile
import os

NMS_NAMESPACE = os.getenv("NMS_NAMESPACE", "anemo-rhoai")
DATASTORE_URL = f"http://nemodatastore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
NDS_TOKEN = os.getenv("NDS_TOKEN", "token")

# files_url format: hf://{namespace}/{repo_name}@1.0 (EntityHandler adds @1.0 revision)
# Or: hf://models/{namespace}/{repo_name}@1.0
files_url = "hf://$NAMESPACE/llama-3.2-1b-instruct-custom-1234567890-12345@1.0"  # From Step 2.1

# Parse files_url to extract repo info and revision
path = files_url.replace("hf://", "")
revision = None
if "@" in path:
    path, revision = path.rsplit("@", 1)

# Remove models/ or datasets/ prefix if present
if path.startswith("models/"):
    path = path.replace("models/", "")
elif path.startswith("datasets/"):
    path = path.replace("datasets/", "")

if "/" in path:
    repo_namespace, repo_name = path.split("/", 1)
else:
    repo_namespace = NMS_NAMESPACE
    repo_name = path

repo_id = f"{repo_namespace}/{repo_name}"

# Initialize HuggingFace API pointing to DataStore
hf_endpoint = f"{DATASTORE_URL}/v1/hf"
hf_token = NDS_TOKEN if NDS_TOKEN != "token" else None

# Download entire repository snapshot (recommended - handles all files)
temp_dir = tempfile.mkdtemp()
download_kwargs = {
    "repo_id": repo_id,
    "local_dir": temp_dir,
    "endpoint": hf_endpoint,
    "token": hf_token,
    "repo_type": "model"  # Customizer stores models as "model" type
}
if revision:
    download_kwargs["revision"] = revision
    print(f"📌 Downloading from revision: {revision}")

downloaded_path = snapshot_download(**download_kwargs)
print(f"\n✅ Downloaded model to: {downloaded_path}")

# Count downloaded files
import os
from pathlib import Path
files = list(Path(downloaded_path).rglob("*"))
model_files = [f for f in files if f.is_file() and '.cache' not in str(f)]
print(f"   Downloaded {len(model_files)} files")
```

#### 2.3 Upload Model to MinIO

Upload the **merged** model (output of `merge_adapter_with_base.py`), not the downloaded adapter.

**Using Python Script:**
```bash
# With MinIO port-forward (from setup_port_forwards.sh)
MINIO_ENDPOINT=http://localhost:9000 python upload_model_to_minio.py --model-dir ./merged_model --target-path models/llama-3.2-1b-instruct-cust

# Or use a different path (e.g. llama-3.2-1b-instruct-custom)
# MINIO_ENDPOINT=http://localhost:9000 python upload_model_to_minio.py --model-dir ./merged_model --target-path models/llama-3.2-1b-instruct-custom
```

**Or manually:**

Get MinIO credentials and upload the model:

```bash
# Get MinIO credentials
oc get secret minio-conn1 -n anemo-rhoai -o jsonpath='{.data}' | \
  jq -r 'to_entries | .[] | "\(.key): \(.value | @base64d)"'
```

Then upload using Python:

```python
import boto3
from botocore.client import Config
import os

# MinIO configuration (from secret)
MINIO_ENDPOINT = "http://minio-service.<namespace>.svc.cluster.local:9000"  # Update with your endpoint
MINIO_BUCKET = "your-bucket-name"  # From secret
MINIO_ACCESS_KEY = "your-access-key"  # From secret
MINIO_SECRET_KEY = "your-secret-key"  # From secret

# Target path in MinIO
TARGET_MINIO_PATH = "models/llama-3.2-1b-instruct-custom"  # Or update existing: "models/llama-3.2-1b-instruct"

# Create S3 client for MinIO
s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    verify=False
)

# Upload files
for local_file in downloaded_files:
    # Get relative path from temp_dir
    rel_path = os.path.relpath(local_file, temp_dir)
    s3_key = f"{TARGET_MINIO_PATH}/{rel_path}"
    
    try:
        s3_client.upload_file(local_file, MINIO_BUCKET, s3_key)
        print(f"✅ Uploaded: {s3_key}")
    except Exception as e:
        print(f"⚠️  Failed to upload {rel_path}: {e}")

print(f"\n✅ Model uploaded to MinIO at: {TARGET_MINIO_PATH}")
```

#### 2.4 Update InferenceService (Optional)

If updating an existing InferenceService to use the new model:

```bash
# Update InferenceService storage path
oc patch inferenceservice <inferenceservice-name> -n $NAMESPACE --type='json' -p='[
  {
    "op": "replace",
    "path": "/spec/predictor/model/storage/path",
    "value": "models/llama-3.2-1b-instruct-custom"
  }
]'

# Restart the InferenceService pod to load new model
oc delete pod -n $NAMESPACE -l serving.kserve.io/inferenceservice=<inferenceservice-name>
```

Or create a new InferenceService pointing to the custom model path.

### Step 3: Run Testing Notebook

After deploying the model to MinIO, execute `test-customized-model.ipynb`:

```bash
# In Jupyter Notebook, run all cells in test-customized-model.ipynb
# This will:
# - Verify model in MinIO
# - Test the customized model via InferenceService
# - Compare responses with base model
```

**Prerequisites for testing notebook:**
- Set `CUSTOMIZED_MODEL_NAME` in `env.donotcommit` (from Step 1 output)
- Set `INFERENCE_SERVICE_URL` in `env.donotcommit`
- Set `INFERENCE_SERVICE_NAME` in `env.donotcommit` (if applicable)

## Alternative: Using MinIO Console

If you have access to MinIO web console:

1. **Download from DataStore**: Use the scripts above to download and merge locally
2. **Upload via Console**: 
   - With port-forwards: run `./setup_port_forwards.sh`, then open **http://localhost:9001** (embedded MinIO console; login: minioadmin / minioadmin)
   - Navigate to bucket `models`, create or open the target path (e.g. `llama-3.2-1b-instruct-cust`)
   - Upload the **merged** model files from `./merged_model/`

## Alternative: Using MinIO Client (mc)

```bash
# Install mc (MinIO Client)
# Download from: https://min.io/download

# Configure mc
mc alias set myminio http://minio-service.<namespace>.svc.cluster.local:9000 ACCESS_KEY SECRET_KEY

# Upload downloaded model files
mc cp -r /path/to/downloaded/model/* myminio/your-bucket/models/llama-3.2-1b-instruct-custom/
```

## Next Steps

After verifying the customizer service works:

1. **Upload a Dataset**: Use DataStore API to upload training data
2. **Register a Model**: Use Entity Store API to register a base model
3. **Create Customization Job**: Use Customizer API to create a fine-tuning job

See the [reference notebook](https://github.com/NVIDIA/k8s-nim-operator/blob/69e19c94bb8dcf3003ae553e05303cecb0da1d24/test/e2e/jupyter-notebook/e2e-notebook.ipynb) for examples of creating customization jobs.

## Service URLs

When running from within the cluster (Workbench/Notebook):

- **Customizer**: `http://nemocustomizer-sample.{namespace}.svc.cluster.local:8000`
- **DataStore**: `http://nemodatastore-sample.{namespace}.svc.cluster.local:8000`
- **Entity Store**: `http://nemoentitystore-sample.{namespace}.svc.cluster.local:8000`

## References

- [NeMo Customizer API Documentation](https://docs.nvidia.com/nemo-microservices/)
- [Reference Notebook](https://github.com/NVIDIA/k8s-nim-operator/blob/69e19c94bb8dcf3003ae553e05303cecb0da1d24/test/e2e/jupyter-notebook/e2e-notebook.ipynb)
