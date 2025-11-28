# Custom LLM-as-a-Judge Tutorial

This tutorial demonstrates how to use NeMo Evaluator's Custom LLM-as-a-Judge feature to evaluate LLM outputs using another LLM as a judge.

## Overview

This example evaluates medical consultation summaries on two metrics:
- **Completeness**: How well the summary captures all critical information (1-5 scale)
- **Correctness**: How accurate the summary is without false information (1-5 scale)

The workflow:
1. Target model (your deployed NIM: meta/llama-3.2-1b-instruct) generates summaries from medical consultations
2. Judge model (your deployed NIM: meta/llama-3.2-1b-instruct) evaluates each summary on completeness and correctness
3. Results are aggregated and displayed

**Note**: This tutorial uses your deployed NIM endpoint for both judge and target models. No external API keys required!

## Prerequisites

### Deployed Services
- ✅ NeMo Evaluator (v25.06+)
- ✅ NeMo Data Store
- ✅ NeMo Entity Store
- ✅ LlamaStack (optional but recommended)

### Required Model
- ✅ **NIM Model Serving**: `meta/llama-3.2-1b-instruct` model deployed via NIM Model Serving
  - Service: Your NIM Model Serving InferenceService name (configured via `NIM_MODEL_SERVING_SERVICE` in `env.donotcommit`)
  - This model is used for both the **judge** (evaluator) and **target** (summary generator) models
  - The model must be accessible via the configured external URL or cluster-internal service
  - **How to find your service name**: `oc get inferenceservice -n <your-namespace>`
  - **How to find your external URL**: `oc get route -n <your-namespace> | grep <your-service-name>` or check your OpenShift console

### API Keys (Optional - Not Required)
- **No External API Key Required**: This tutorial uses your deployed NIM Model Serving endpoint (your InferenceService with `meta/llama-3.2-1b-instruct` model) for both judge and target models
- **Service Account Token Required**: You need to set `NIM_SERVICE_ACCOUNT_TOKEN` in `env.donotcommit` for authentication with the external NIM Model Serving URL
  - **How to get your token**: `oc get secret <service-account-name> -n <namespace> -o jsonpath='{.data.token}' | base64 -d`
- **OpenAI API Key**: Optional - only if you want to use OpenAI models instead (not used in this tutorial)
- **NVIDIA API Key**: Optional - only if you want to use NVIDIA API models instead (not used in this tutorial)

### Python Environment
- Python 3.8+
- Jupyter Lab

## Quick Start

### 1. Install Dependencies

```bash
cd NeMo-Microservices/demos/custom-llm-as-a-judge
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the template and create `env.donotcommit` file:

```bash
cp env.donotcommit.example env.donotcommit
# Edit env.donotcommit and add your NIM_SERVICE_ACCOUNT_TOKEN
```

Required configuration in `env.donotcommit`:

```bash
# Required: Your namespace
NMS_NAMESPACE=your-namespace

# NIM Model Serving Configuration
# Replace with your actual InferenceService name
NIM_MODEL_SERVING_SERVICE=your-nim-service-name
NIM_MODEL_SERVING_MODEL=meta/llama-3.2-1b-instruct
# Replace with your actual external URL (HTTPS)
# Format: https://<service-name>-<namespace>.apps.<cluster-domain>
NIM_MODEL_SERVING_URL_EXTERNAL=https://your-service-name-your-namespace.apps.your-cluster-domain.com
USE_NIM_MODEL_SERVING=true
USE_EXTERNAL_URL=true

# REQUIRED: Service Account Token for authentication
# Get from: oc get secret <service-account-name> -n <namespace> -o jsonpath='{.data.token}' | base64 -d
NIM_SERVICE_ACCOUNT_TOKEN=your-token-here

# Optional
RUN_LOCALLY=false  # Set to true for local development with port-forwards
DATASET_NAME=custom-llm-as-a-judge-eval-data
```

**How to find your values**:
- **Namespace**: Your OpenShift project/namespace name
- **Service Name**: `oc get inferenceservice -n <your-namespace>` - look for your NIM Model Serving InferenceService
- **External URL**: 
  - Option 1: `oc get route -n <your-namespace> | grep <your-service-name>`
  - Option 2: Check OpenShift console → Networking → Routes
  - Format: `https://<service-name>-<namespace>.apps.<cluster-domain>`
- **Service Account Token**: `oc get secret <service-account-name> -n <namespace> -o jsonpath='{.data.token}' | base64 -d`

**Note**: 
- The notebook uses NIM Model Serving (your configured service) for both judge and target models
- Model used: `meta/llama-3.2-1b-instruct` (deployed via NIM Model Serving)
- **Required**: `NIM_SERVICE_ACCOUNT_TOKEN` must be set in `env.donotcommit` for external URL authentication
- The `env.donotcommit` file is git-ignored and will NOT be committed to version control

### 3. Set Up Port-Forwards (if running locally)

If `RUN_LOCALLY=true`, run the port-forward script:

```bash
./port-forward.sh
```

Or manually (replace `<your-namespace>` with your actual namespace):
```bash
oc port-forward -n <your-namespace> svc/nemodatastore-sample 8001:8000 &
oc port-forward -n <your-namespace> svc/nemoentitystore-sample 8002:8000 &
oc port-forward -n <your-namespace> svc/nemoevaluator-sample 8004:8000 &
oc port-forward -n <your-namespace> svc/llamastack 8321:8321 &
```

### 4. Run the Notebook

```bash
jupyter lab llm-as-a-judge-tutorial.ipynb
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
- Evaluator: `http://nemoevaluator-sample.{namespace}.svc.cluster.local:8000`
- LlamaStack: `http://llamastack.{namespace}.svc.cluster.local:8321`

**Local Mode** (with port-forwards):
- Data Store: `http://localhost:8001`
- Entity Store: `http://localhost:8002`
- Evaluator: `http://localhost:8004`
- LlamaStack: `http://localhost:8321`

## Customization

### Judge Model

The notebook uses your deployed NIM Model Serving endpoint by default:
- **Service**: Your NIM Model Serving InferenceService (configured via `NIM_MODEL_SERVING_SERVICE` in `env.donotcommit`)
- **Model**: `meta/llama-3.2-1b-instruct`
- **Authentication**: Service Account Token (set in `env.donotcommit` as `NIM_SERVICE_ACCOUNT_TOKEN`)
- **URL**: External HTTPS URL (configured via `NIM_MODEL_SERVING_URL_EXTERNAL` in `env.donotcommit`)

### Target Model

The notebook uses the same NIM Model Serving endpoint for the target model:
- **Service**: Your NIM Model Serving InferenceService (configured via `NIM_MODEL_SERVING_SERVICE` in `env.donotcommit`)
- **Model**: `meta/llama-3.2-1b-instruct`
- **Authentication**: Service Account Token (set in `env.donotcommit` as `NIM_SERVICE_ACCOUNT_TOKEN`)
- **URL**: External HTTPS URL (configured via `NIM_MODEL_SERVING_URL_EXTERNAL` in `env.donotcommit`)

**Note**: If you want to use different models (OpenAI, NVIDIA API, or a different NIM service), you can modify the model configuration in the notebook cells. However, the default configuration works out of the box with your deployed NIM Model Serving endpoint.

### Adjusting Sample Size

For quick testing, the notebook uses `limit: 5` samples. To run full evaluation:

```python
"dataset": {
    "files_url": f"hf://datasets/{NMS_NAMESPACE}/{DATASET_NAME}/",
    "limit": 25  # Increase for full evaluation
}
```

### Adding More Metrics

You can add additional metrics to the evaluation configuration:

```python
"metrics": {
    "completeness": { ... },
    "correctness": { ... },
    "your_metric": {
        "type": "llm-judge",
        "params": {
            "model": judge_model_config,
            "template": { ... },
            "scores": { ... }
        }
    }
}
```

## Version Compatibility

- **NeMo Evaluator**: v25.06+ (tested with v25.06)
- **LLM-as-a-Judge Tool**: Included in Evaluator deployment
- **API Endpoints**: Standard NeMo Evaluator REST API

## Important: External NIM (Knative InferenceService) Limitation

**⚠️ Known Issue with Evaluator v25.06**: External NIM services deployed via Knative/KServe InferenceServices **do not work** with Custom LLM-as-a-Judge evaluation jobs.

### Why External NIM Doesn't Work

When using Knative InferenceServices (e.g., `anemo-rhoai-predictor-00002`), the Evaluator v25.06 has a bug that **strips the `/chat/completions` path** from URLs during job execution:

1. ✅ **Target creation works**: The evaluation target is stored correctly with the full URL (`/v1/chat/completions`)
2. ✅ **Job submission works**: The job is accepted and created successfully
3. ❌ **Job execution fails**: During execution, the Evaluator strips `/chat/completions` from the URL, resulting in:
   ```
   Error connecting to inference server at http://.../v1
   ```
   Instead of the correct: `http://.../v1/chat/completions`

### Solution: Use Standard NIM Service

This tutorial uses the **standard NIM service** (`meta-llama3-1b-instruct`) instead of Knative InferenceServices:

- ✅ **Standard NIM service**: Works correctly with Evaluator v25.06
- ✅ **No URL stripping**: Full paths are preserved during execution
- ✅ **Cluster-internal access**: Uses standard ClusterIP service on port 8000

### If You Need to Use External NIM

If you must use a Knative InferenceService, you have these options:

1. **Upgrade Evaluator**: Check if newer Evaluator versions (v25.08+) fix this issue
2. **Use External Endpoint**: If your NIM is accessible via external URL (not cluster-internal), you may be able to use that
3. **Wait for Fix**: This is a known Evaluator limitation that needs to be fixed in the Evaluator codebase

**Recommendation**: Use the standard NIM service pattern (as shown in this tutorial) for reliable evaluation jobs.

## Troubleshooting

### Job Submission Fails

- Verify Evaluator service is running: `oc get pods -n <your-namespace> | grep evaluator`
- Check Evaluator logs: `oc logs -n <your-namespace> -l app.kubernetes.io/name=nemo-evaluator --tail=100`
- Verify NIM endpoint is accessible: 
  - External URL: `curl -H "Authorization: Bearer <your-token>" <your-external-url>/v1/models`
  - Cluster-internal: `curl http://<your-service-name>-predictor.<your-namespace>.svc.cluster.local:80/v1/models`
- Verify the model `meta/llama-3.2-1b-instruct` is available in the service
- Check Argo Workflows connection: `oc get nemoevaluator nemoevaluator-sample -n <your-namespace> -o jsonpath='{.spec.argoWorkflows.endpoint}'`
- Verify `NIM_SERVICE_ACCOUNT_TOKEN` is set correctly in `env.donotcommit`

### Job Stuck in "pending" or "running"

- Check Argo Workflows: `oc get workflows -n <your-namespace>`
- Check evaluation job pods: `oc get pods -n <your-namespace> | grep eval`
- Verify GPU resources are available (if required)
- Check if NIM Model Serving endpoint is accessible from within the cluster

### Dataset Upload Fails

- Verify Data Store is accessible
- Check namespace exists: `curl {NDS_URL}/v1/datastore/namespaces/{namespace}`
- Verify file path is correct: `./data/doctor_consults_with_summaries.jsonl`

## Documentation

- [NeMo Evaluator Custom Evaluation](https://docs.nvidia.com/nemo/microservices/latest/evaluate/evaluation-custom.html#evaluation-with-llm-as-a-judge)
- [Evaluation Targets](https://docs.nvidia.com/nemo/microservices/latest/evaluate/evaluation-targets.html)

## LlamaStack Integration

This demo includes LlamaStack integration for a unified API experience. The notebook:

- ✅ Initializes LlamaStack client on startup
- ✅ Tests connectivity to LlamaStack service
- ✅ Provides graceful fallback if LlamaStack is unavailable

**Note**: While the evaluation jobs themselves use the Evaluator service (which calls models directly), LlamaStack is available for any future enhancements or direct model interactions.

### LlamaStack Service

- **Port**: 8321
- **Service Name**: `llamastack`
- **Client**: `llama-stack-client` (installed from GitHub main branch)

The notebook automatically detects if LlamaStack is available and initializes the client accordingly.

## Files

- `llm-as-a-judge-tutorial.ipynb` - Main tutorial notebook
- `config.py` - Configuration file (auto-detects local vs cluster)
- `requirements.txt` - Python dependencies
- `port-forward.sh` - Port-forward script for local development
- `data/doctor_consults_with_summaries.jsonl` - Sample dataset

