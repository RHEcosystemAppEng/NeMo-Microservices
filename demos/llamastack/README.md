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

LlamaStack is deployed using the Helm chart as part of the `nemo-instances` chart. This ensures consistency with the deployment approach used for all other NeMo microservices.

### Building the Image

The LlamaStack container image used in the deployment can be built using the following commands:

```bash
git clone https://github.com/meta-llama/llama-stack.git
cd llama-stack

podman build --platform=linux/amd64 \
  -f containers/Containerfile \
  --build-arg DISTRO_NAME=nvidia \
  --build-arg INSTALL_MODE=editable \
  --tag quay.io/ecosystem-appeng/llamastack-server-distribution:latest .

podman push quay.io/ecosystem-appeng/llamastack-server-distribution:latest
```

The image configuration in the Helm values (`deploy/nemo-instances/values.yaml`) references this image:

```yaml
llamastack:
  image:
    repository: quay.io/ecosystem-appeng/llamastack-server-distribution
    tag: "latest"
```

### Helm Deployment

LlamaStack is included in the `nemo-instances` Helm chart. To deploy or upgrade:

```bash
cd deploy/nemo-instances

# Deploy or upgrade with llamastack enabled
helm upgrade nemo-instances . \
  -n <namespace> \
  --set namespace.name=<namespace> \
  --set llamastack.enabled=true
```

The Helm chart will create:
- **ConfigMap**: Contains the LlamaStack configuration defining providers for various APIs (inference, safety, eval, post_training, etc.)
- **Deployment**: Deploys the LlamaStack container with environment variables pointing to your NeMo microservices
- **Service**: Creates a ClusterIP service to expose LlamaStack internally on port 8321

### Configuration

The deployment is configured via Helm values in `deploy/nemo-instances/values.yaml`. Key configuration includes:

- `NVIDIA_API_KEY`: Your NGC API key (from secret)
- `NVIDIA_BASE_URL`: NIM inference endpoint URL (automatically configured based on namespace)
- `NVIDIA_ENTITY_STORE_URL`: NeMo Entity Store URL (automatically configured)
- `NVIDIA_DATASETS_URL`: NeMo Data Store URL (automatically configured)
- `NVIDIA_CUSTOMIZER_URL`: NeMo Customizer URL (automatically configured)
- `GUARDRAILS_SERVICE_URL`: NeMo Guardrails URL (automatically configured)
- `NVIDIA_EVALUATOR_URL`: NeMo Evaluator URL (automatically configured)

All service URLs are automatically configured based on the namespace setting, ensuring proper connectivity to NeMo microservices.

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

After deployment, LlamaStack will be available at:
- **Internal**: `http://llamastack.<namespace>.svc.cluster.local:8321`
- **From within the same namespace**: `http://llamastack:8321`

You can interact with LlamaStack using:

```python
from llama_stack_client import LlamaStackClient

# Update the URL to match your deployment
client = LlamaStackClient(base_url="http://llamastack.<namespace>.svc.cluster.local:8321")
# Run inference, evaluations, safety checks, etc.
```

## Troubleshooting

- **Deployment Issues**: Check pod logs with `oc logs -f deployment/llamastack`
- **Service Connectivity**: Verify NeMo microservices are running and accessible
- **Model Loading**: Ensure base models are available in NIM
- **API Keys**: Confirm NGC and Hugging Face tokens are valid
