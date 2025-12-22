# Deploying NeMo Microservices with Custom Models

This guide shows the key changes needed to deploy NeMo Microservices with a custom model (like IBM Granite) instead of the default Meta Llama models.

## Overview

The standard NeMo deployment uses Meta Llama models from NGC. To use a custom model from a different registry, you need to:

1. **Deploy a custom NIM** with the model from your chosen registry
2. **Configure NeMo Customizer** to recognize the new model
3. **Update model references** in notebooks and configuration files

### Supported Model Registries

NIM supports models from multiple registries:

- **HuggingFace Hub** (`hf://`) - Open-source models (shown in this guide)
- **NVIDIA NGC** (`ngc://`) - NVIDIA-optimized models (default)
- **Local filesystem** (`file://`) - Pre-downloaded models
- **HTTP/S endpoints** (`http://`, `https://`) - Custom model servers
- **S3-compatible storage** (`s3://`) - Cloud storage backends

**Note:** This guide uses HuggingFace as an example, but the same principles apply to other registries. Simply adjust the `NIM_MODEL_NAME` URI scheme and authentication method accordingly.

This has been tested with:
- **IBM Granite 3.1 1B Instruct** from HuggingFace (`hf://ibm-granite/granite-3.1-1b-a400m-instruct`)

While this procedure was tested with IBM Granite from HuggingFace, it should work with any model from any supported registry **except quantized models** (see limitations below).

## Important: Model Format Limitations

### ✅ Supported Model Formats
- **BF16 (bfloat16)** - Preferred
- **FP16 (float16)** - Supported
- **FP32 (float32)** - Supported

### ❌ Unsupported Model Formats (Cannot be Fine-Tuned)
- **FP8** (compressed-tensors)
- **INT8/INT4** (standard quantization)
- **GPTQ** quantized models
- **AWQ** quantized models
- Any other quantized formats

### Why Quantized Models Can't Be Fine-Tuned with NeMo

**Technical Reasons:**

1. **Weight Updates Require Full Precision**
   - Fine-tuning adjusts model weights through gradient descent
   - Gradients are small floating-point numbers
   - 8-bit precision loses too much information during backpropagation
   - Results in training instability and poor convergence

2. **LoRA (Low-Rank Adaptation) Limitations**
   - LoRA adds small "adapter" matrices to frozen base model weights
   - The base model weights need to be accessible in their original format
   - Quantized weights are "baked in" - can't separate them for LoRA

3. **NeMo's Architecture Assumptions**
   - NeMo Customizer expects models in standard formats (BF16/FP16/FP32)
   - Doesn't support compressed/quantized formats for training

**Important:** While you can deploy quantized models in NIM for inference-only use cases, you cannot fine-tune them with NeMo Customizer. Choose unquantized model variants from HuggingFace.

## Prerequisites

In addition to the standard NeMo deployment prerequisites:

### For HuggingFace Models (as shown in this guide):
- **HuggingFace Token**: Create a token at [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
- **Model Access**: For gated models, accept the license on HuggingFace
- **Model Format**: Ensure the model is NOT quantized (check model card on HuggingFace)

### For Other Model Registries:
- **NGC Models**: NVIDIA NGC API key (already configured in standard deployment)
- **Local/HTTP Models**: Ensure model files are accessible from the cluster
- **S3 Models**: Configure S3 credentials and bucket access
- **Model Format**: Regardless of registry, ensure models are in BF16/FP16/FP32 format (not quantized)

## Key Changes from Standard Deployment

### 1. Create Model Registry Credentials Secret (if required)

**NEW REQUIREMENT** - Only needed for registries requiring authentication:

**For HuggingFace models:**
```bash
oc create secret generic hf-token \
  --from-literal=HF_TOKEN="your-huggingface-token" \
  -n your-namespace
```

**For other registries:**
- **NGC models**: Use existing `ngc-secret` and `ngc-api-secret` (already configured)
- **S3 models**: Create secret with AWS credentials
- **Local/HTTP models**: May not require authentication

### 2. Deploy Custom Model NIM (Instead of Default Llama Model)

**REPLACES**: The default `meta-llama3-1b-instruct` NIMPipeline in `nemo-instances` chart

Create a NIMPipeline configuration for your custom model. The key difference is the `NIM_MODEL_NAME` environment variable, which uses a URI scheme to specify the model registry:

- **HuggingFace**: `hf://namespace/model-name`
- **NGC**: `ngc://namespace/model-name:version`
- **Local**: `file:///path/to/model`
- **HTTP**: `http://model-server.com/model`
- **S3**: `s3://bucket-name/path/to/model`

**Example: HuggingFace Model (IBM Granite)**

```yaml
# Example: granite-3.1-1b-hf.yaml
apiVersion: apps.nvidia.com/v1alpha1
kind: NIMPipeline
metadata:
  name: granite-pipeline
  namespace: your-namespace
spec:
  services:
    - name: granite-3-1-1b-instruct
      enabled: true
      spec:
        env:
          # ============================================
          # KEY CHANGE: HuggingFace model configuration
          # ============================================
          - name: HF_TOKEN
            valueFrom:
              secretKeyRef:
                name: hf-token
                key: HF_TOKEN
          - name: NIM_MODEL_NAME
            value: "hf://ibm-granite/granite-3.1-1b-a400m-instruct"
          - name: NIM_SERVED_MODEL_NAME
            value: "granite-3.1-1b-instruct"

          # ============================================
          # CRITICAL: Enable dynamic LoRA loading
          # ============================================
          - name: NIM_PEFT_SOURCE
            value: http://nemoentitystore-sample.your-namespace.svc.cluster.local:8000
          - name: NIM_PEFT_REFRESH_INTERVAL
            value: "180"
          - name: NIM_MAX_CPU_LORAS
            value: "16"
          - name: NIM_MAX_GPU_LORAS
            value: "8"
          - name: NIM_ENABLE_CUSTOMIZATION
            value: "true"
          - name: NIM_CUSTOMIZATION_ENABLED_MODELS
            value: "granite-3.1-1b-instruct"

        # Use multi-LLM NIM container (supports HuggingFace)
        image:
          repository: nvcr.io/nim/nvidia/llm-nim
          tag: latest
          pullPolicy: Always
          pullSecrets:
          - ngc-secret

        authSecret: ngc-api-secret

        storage:
          pvc:
            create: true
            storageClass: "gp3-csi"
            size: "50Gi"

        resources:
          limits:
            nvidia.com/gpu: 1

        # IMPORTANT: Allow sufficient time for model download
        startupProbe:
          httpGet:
            path: /v1/health/ready
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          failureThreshold: 180  # 30 min (180 * 10s)

        expose:
          service:
            type: ClusterIP
            port: 8000
```

**Apply the custom NIM:**

```bash
oc apply -f granite-3.1-1b-hf.yaml
```

### 3. Patch NeMo Data Store for HuggingFace Proxy

**NEW CONFIGURATION** - Enables dataset downloads from HuggingFace:

```bash
oc patch nemodatastore nemodatastore-sample -n your-namespace --type='json' -p='[
  {
    "op": "add",
    "path": "/spec/env",
    "value": [
      {
        "name": "HF_TOKEN",
        "valueFrom": {
          "secretKeyRef": {
            "name": "hf-token",
            "key": "HF_TOKEN"
          }
        }
      },
      {
        "name": "HF_ENDPOINT",
        "value": "https://huggingface.co"
      }
    ]
  }
]'
```

### 4. Update NeMo Customizer Model Configuration

**CRITICAL CHANGE** - Define your custom model for fine-tuning:

```bash
# Patch the nemo-model-config ConfigMap
oc patch configmap nemo-model-config -n your-namespace --type='json' -p='[
  {
    "op": "replace",
    "path": "/data/customizationTargets",
    "value": "overrideExistingTargets: true\ntargets:\n  # Disable default Meta models\n  meta/llama-3.1-8b-instruct@2.0:\n    enabled: false\n  meta/llama-3.2-1b-instruct@2.0:\n    enabled: false\n  # Add IBM Granite model\n  ibm-granite/granite-3.1-1b-instruct@1.0:\n    base_model: ibm-granite/granite-3.1-1b-instruct\n    enabled: true\n    model_path: granite-3.1-1b-instruct\n    model_uri: hf://ibm-granite/granite-3.1-1b-a400m-instruct\n    name: granite-3.1-1b-instruct@1.0\n    namespace: ibm-granite\n    num_parameters: 1300000000\n    precision: bf16-mixed\n"
  },
  {
    "op": "add",
    "path": "/data/customizationConfigTemplates",
    "value": "overrideExistingTemplates: false\ntemplates:\n  ibm-granite/granite-3.1-1b-instruct@v1.0.0+A100:\n    max_seq_length: 4096\n    name: granite-3.1-1b-instruct@v1.0.0+A100\n    namespace: ibm-granite\n    prompt_template: \"{prompt} {completion}\"\n    target: ibm-granite/granite-3.1-1b-instruct@1.0\n    training_options:\n    - finetuning_type: lora\n      micro_batch_size: 1\n      num_gpus: 1\n      num_nodes: 1\n      tensor_parallel_size: 1\n      training_type: sft\n"
  }
]'

# Restart NemoCustomizer to pick up new config
oc rollout restart deployment -l app.kubernetes.io/name=nemocustomizer -n your-namespace
```

**Key Fields to Adjust for Different Models:**

| Field | Description | Granite 3.1 1B Value |
|-------|-------------|----------------------|
| `namespace` | Model vendor/organization | `ibm-granite` |
| `name` | Model identifier with version | `granite-3.1-1b-instruct@1.0` |
| `model_uri` | HuggingFace model path | `hf://ibm-granite/granite-3.1-1b-a400m-instruct` |
| `num_parameters` | Model size in parameters | `1300000000` (1.3B) |
| `max_seq_length` | Maximum context length | `4096` |
| `micro_batch_size` | Training batch size per GPU | `1` |
| `precision` | Must be bf16-mixed, fp16, or fp32 | `bf16-mixed` |

### 5. Configure Customizer Datastore (Two-Phase Approach)

**NEW REQUIREMENT** - Handle model download from HuggingFace:

**Phase 1: Point to HuggingFace for model download**

```bash
oc patch nemocustomizer nemocustomizer-sample -n your-namespace --type='merge' -p='
{
  "spec": {
    "datastore": {
      "endpoint": "https://huggingface.co"
    },
    "modelDownloadJobs": {
      "hfSecret": {
        "name": "hf-token",
        "key": "HF_TOKEN"
      }
    }
  }
}'

# Wait for model download job to complete
# Monitor: oc get jobs -n your-namespace | grep model-downloader
```

**Phase 2: Switch back to NeMo Data Store for datasets**

```bash
oc patch nemocustomizer nemocustomizer-sample -n your-namespace --type='merge' -p='
{
  "spec": {
    "datastore": {
      "endpoint": "http://nemodatastore-sample.your-namespace.svc.cluster.local:8000"
    }
  }
}'
```

### 6. Update NeMo Evaluator Model Reference

**CHANGE** - Point to your custom model instead of default:

```bash
oc patch nemoevaluator nemoevaluator-sample -n your-namespace --type='json' -p='[
  {
    "op": "add",
    "path": "/spec/env",
    "value": [
      {
        "name": "NIM_PROXY_URL",
        "value": "http://granite-3-1-1b-instruct.your-namespace.svc.cluster.local:8000/v1"
      }
    ]
  }
]'
```

### 7. Update Notebook Configuration

**CHANGES REQUIRED** in `Llama_Stack_NVIDIA_E2E_Flow.ipynb` or similar:

```python
# In config.py or notebook cells:

# CHANGE: Base model identifier
BASE_MODEL = "granite-3.1-1b-instruct"  # Instead of "meta/llama-3.2-1b-instruct"

# CHANGE: Model registration in Entity Store
response = requests.post(
    f"{ENTITY_STORE_URL}/v1/models",
    json={
        "name": "granite-3.1-1b-instruct",
        "namespace": "ibm-granite",  # Change from "meta"
        "description": "IBM Granite 3.1 1B Instruct model",
        "spec": {
            "num_parameters": 1300000000,  # Change from 1000000000
            "context_size": 4096,
            "is_chat": True
        },
        "artifact": {
            "files_url": "nim://ibm-granite/granite-3.1-1b-instruct"  # Change path
        }
    }
)

# CHANGE: API endpoint configuration
requests.patch(
    f"{ENTITY_STORE_URL}/v1/models/ibm-granite/granite-3.1-1b-instruct",  # Change path
    json={
        "api_endpoint": {
            "url": "http://granite-3-1-1b-instruct.namespace.svc.cluster.local:8000/v1",
            "model_id": "granite-3.1-1b-instruct",
            "format": "nim"
        }
    }
)

# CHANGE: Fine-tuning model reference
response = client.alpha.post_training.supervised_fine_tune(
    model="ibm-granite/granite-3.1-1b-instruct@v1.0.0+A100",  # Use your config template name
    training_config={
        "n_epochs": 2,
        "data_config": {
            "batch_size": 16,  # Adjust for model size
            "dataset_id": "sample-squad-test",
        },
        "optimizer_config": {
            "lr": 0.0001,
        }
    },
    algorithm_config={
        "type": "LoRA",
        "adapter_dim": 16,
        "rank": 8,
        # ... rest of config
    }
)

# CHANGE: Inference calls
response = client.chat.completions.create(
    messages=[{"role": "user", "content": prompt}],
    model="nvidia/granite-3.1-1b-instruct",  # Change model ID
    max_tokens=20,
    temperature=0.7
)

# CHANGE: Evaluation calls
response = client.alpha.eval.run_eval(
    benchmark_id=benchmark_id,
    benchmark_config={
        "eval_candidate": {
            "type": "model",
            "model": "ibm-granite/granite-3.1-1b-instruct",  # Change model reference
            "sampling_params": {}
        }
    }
)
```

## Quick Reference: IBM Granite 3.1 1B Settings

```yaml
# NIMPipeline
NIM_MODEL_NAME: "hf://ibm-granite/granite-3.1-1b-a400m-instruct"
NIM_SERVED_MODEL_NAME: "granite-3.1-1b-instruct"
storage.pvc.size: "50Gi"
resources.limits.nvidia.com/gpu: 1

# Customizer Config
namespace: ibm-granite
num_parameters: 1300000000
micro_batch_size: 1
max_seq_length: 4096
precision: bf16-mixed  # IMPORTANT: Not quantized!
```

## Service URLs After Deployment

**CHANGE**: Service names will be different:

| Service | Standard Deployment | IBM Granite Deployment |
|---------|---------------------|------------------------|
| Chat Model NIM | `meta-llama3-1b-instruct` | `granite-3-1-1b-instruct` |
| Other Services | *(unchanged)* | *(unchanged)* |

Updated service URL:
```
http://granite-3-1-1b-instruct.your-namespace.svc.cluster.local:8000
```

## Expected Results

After deployment, you should see:

```bash
# Custom model pod running
oc get pods -n your-namespace | grep granite-3-1-1b-instruct
# granite-3-1-1b-instruct-xyz   1/1   Running

# Model available in NIM
curl http://granite-3-1-1b-instruct:8000/v1/models
# Returns: {"data": [{"id": "granite-3.1-1b-instruct", ...}]}

# Model registered in Customizer
oc get configmap nemo-model-config -o yaml | grep granite
# Shows your custom model configuration
```

## Troubleshooting

### Model not downloading

```bash
# Check model downloader job
oc get jobs | grep model-downloader

# View logs
oc logs job/model-downloader-ibm-granite-granite-3-1-1b-instruct-1-0 --tail=50

# Common fix: Verify HF_TOKEN secret
oc get secret hf-token -o jsonpath='{.data.HF_TOKEN}' | base64 -d
```

### Model is quantized and fine-tuning fails

```
Error: Model format not supported for training

Solution: Check the HuggingFace model card
- Look for variants without "GPTQ", "AWQ", "INT4", "INT8", "FP8" in the name
- Choose the base model or explicitly labeled "fp16" or "bf16" versions
- Example: Use "ibm-granite/granite-3.1-1b-a400m-instruct"
  NOT "ibm-granite/granite-3.1-1b-a400m-instruct-GPTQ"
```

### Fine-tuning fails with OOM (Out of Memory)

```yaml
# Batch size is already minimal at 1, consider:
# - Using gradient accumulation
# - Reducing sequence length
# - Using smaller LoRA rank
```

### NIM not loading LoRA adapters

```bash
# Verify NIM_PEFT_SOURCE is set correctly
oc get deployment granite-3-1-1b-instruct -o yaml | grep NIM_PEFT_SOURCE

# Should point to Entity Store:
# http://nemoentitystore-sample.your-namespace.svc.cluster.local:8000
```

## Complete Example Script

See the reference implementation:
```
/Users/hacohen/Desktop/repos/install-NeMo-on-OpenShift/deploy_microservices_HF_llm.sh
```

This script automates all the changes listed above.

## Next Steps

1. Deploy IBM Granite model using the changes above
2. Verify model is accessible via NIM endpoint
3. Update notebook with new model references
4. Run end-to-end workflow (dataset upload → fine-tune → evaluate)
5. Compare results with baseline metrics

Expected performance with IBM Granite 3.1 1B:
- **Base Model BLEU**: ~7
- **Fine-Tuned Model BLEU**: ~24 (3-4x improvement)
- **Accuracy Improvement**: +20%
