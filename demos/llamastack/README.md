# LlamaStack NVIDIA E2E Demo

This demo showcases an end-to-end workflow for fine-tuning, inference, and evaluation using NVIDIA NeMo Microservices and LlamaStack. It demonstrates how to integrate various AI capabilities through the LlamaStack API.

## Overview

The demo is based on the [official LlamaStack NVIDIA E2E Flow notebook](https://github.com/llamastack/llama-stack/blob/main/docs/notebooks/nvidia/beginner_e2e/Llama_Stack_NVIDIA_E2E_Flow.ipynb) and includes:

- **Model Fine-tuning**: Customizing pre-trained models with domain-specific data
- **Inference**: Running inference on base and customized models
- **Evaluation**: Comparing model performance metrics before and after fine-tuning
- **Safety Checks**: Implementing guardrails for content safety
- **Dataset Management**: Uploading and managing training datasets

## Prerequisites

Before deploying LlamaStack, ensure you have:

1. **NeMo Microservices Platform** running with the following components:
   - NeMo Data Store (NDS)
   - NeMo Entity Store
   - NeMo Customizer
   - NeMo Evaluator
   - NeMo Guardrails
   - NIM (NVIDIA Inference Microservice)

2. **Hugging Face Token** with access to required model repositories

3. **NVIDIA NGC API Key** for accessing NVIDIA services

## Deployment

### Automated Deployment

Use the provided deployment script to deploy LlamaStack to your Kubernetes/OpenShift cluster:

```bash
cd demos/llamastack/deploy

# Deploy with your NeMo namespace (required)
NEMO_NAMESPACE=your-nemo-namespace ./deploy_llamastack.sh

# Or deploy to specific namespace with your NeMo namespace
NAMESPACE=your-llamastack-namespace NEMO_NAMESPACE=your-nemo-namespace ./deploy_llamastack.sh
```

### Understanding the Namespace Variables

- **`NEMO_NAMESPACE`** (Required): The Kubernetes namespace where your NeMo microservices are running (Data Store, Entity Store, Customizer, Evaluator, Guardrails, NIM)
- **`NAMESPACE`** (Optional): The Kubernetes namespace where LlamaStack components will be deployed. Defaults to `default` if not specified.

**Example Scenario:**
```bash
# If NeMo services are in "production-nemo" namespace
# And you want LlamaStack in "development-ai" namespace
NAMESPACE=development-ai NEMO_NAMESPACE=production-nemo ./deploy_llamastack.sh
```

This allows you to run LlamaStack in different environments while connecting to the same NeMo backend services.

This script will:

1. **Apply Kubernetes Resources**:
   - `configmap.yaml`: Contains the LlamaStack configuration defining providers for various APIs (inference, safety, eval, post_training, etc.)
   - `deployment.yaml`: Deploys the LlamaStack container with environment variables pointing to your NeMo microservices
   - `service.yaml`: Creates a ClusterIP service to expose LlamaStack internally on port 8321

2. **Wait for Deployment**: The script waits up to 300 seconds for the deployment to become available

3. **Verify Deployment**: Shows the running LlamaStack pods

The deployment configures LlamaStack with the NVIDIA provider integration, connecting it to your NeMo microservices infrastructure.

### Namespace Considerations

- **Service Components** (ConfigMap, Deployment, Service): Should be deployed in the same namespace as your NeMo microservices
- **Route** (Optional): May need to be deployed in a different namespace for external access, depending on your cluster configuration
- **Environment Variables**: Update the URLs in `deployment.yaml` to match your actual NeMo microservice endpoints and namespaces

### Manual Deployment

If you prefer manual deployment, specify your target namespace:

```bash
# Set your target namespace
NAMESPACE=your-namespace

# Apply configuration resources
oc apply -f configmap.yaml -n $NAMESPACE
oc apply -f service.yaml -n $NAMESPACE
oc apply -f deployment.yaml -n $NAMESPACE

# Wait for deployment to be ready
oc wait --for=condition=available deployment/llamastack --timeout=300s -n $NAMESPACE

# Optional: Create external route in the same or different namespace
# Note: Route may need to be deployed in a different namespace for external access
oc apply -f route.yaml -n $NAMESPACE
```

### Configuration

**IMPORTANT**: You must specify your NeMo namespace when deploying. The deployment script will automatically update all service URLs to use your specified namespace.

The deployment uses several environment variables configured in `deployment.yaml`:

- `NVIDIA_API_KEY`: Your NGC API key (from secret)
- `NVIDIA_BASE_URL`: NIM inference endpoint URL
- `NVIDIA_ENTITY_STORE_URL`: NeMo Entity Store URL
- `NVIDIA_DATASETS_URL`: NeMo Data Store URL
- `NVIDIA_CUSTOMIZER_URL`: NeMo Customizer URL
- `GUARDRAILS_SERVICE_URL`: NeMo Guardrails URL
- `NVIDIA_EVALUATOR_URL`: NeMo Evaluator URL

## End-to-End Test

The `Llama_Stack_NVIDIA_E2E_Flow.ipynb` notebook provides a comprehensive end-to-end test of the LlamaStack API integration with NeMo microservices.

### Test Workflow

1. **Setup and Configuration**:
   - Configure URLs for all NeMo microservices in `config.py`
   - Set Hugging Face token for dataset access
   - Initialize LlamaStack client

2. **Dataset Preparation**:
   - Upload sample SQuAD dataset for fine-tuning
   - Prepare training, validation, and testing data splits

3. **Model Registration**:
   - Register base model (`meta/llama-3.2-1b-instruct`) in Entity Store
   - Configure model metadata and artifacts

4. **Inference Testing**:
   - Test inference on the base model
   - Verify model responses and performance

5. **Model Customization**:
   - Create fine-tuning job using NeMo Customizer
   - Monitor job progress and wait for completion
   - Register customized model in NIM

6. **Evaluation**:
   - Run evaluation on base model using sample datasets
   - Evaluate customized model performance
   - Compare metrics between base and fine-tuned models


### Sample Data

The demo includes sample datasets:

- **`sample_squad_data/`**: Stanford Question Answering Dataset (SQuAD) for fine-tuning
- **`sample_content_safety_test_data/`**: Content safety test cases for guardrails evaluation
- **`sample_squad_messages/`**: Message format datasets for chat-based evaluation

### Key API Endpoints Tested

The notebook exercises these LlamaStack APIs:

- **Inference API**: Model completions and chat
- **Post Training API**: Model customization jobs
- **Eval API**: Model evaluation and benchmarking
- **Safety API**: Content safety and guardrails
- **Dataset IO API**: Dataset upload and management

### Expected Results

- Base model BLEU score: ~3
- Customized model BLEU score: ~5-15

## Usage

After deployment, LlamaStack will be available at `http://llamastack:8321` (internal) or via the configured route (external).

You can interact with LlamaStack using:

```python
from llama_stack_client import LlamaStackClient

client = LlamaStackClient(base_url="http://localhost:8321")
# Run inference, evaluations, safety checks, etc.
```

## Troubleshooting

- **Deployment Issues**: Check pod logs with `oc logs -f deployment/llamastack`
- **Service Connectivity**: Verify NeMo microservices are running and accessible
- **Model Loading**: Ensure base models are available in NIM
- **API Keys**: Confirm NGC and Hugging Face tokens are valid
