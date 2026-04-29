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
   - NIM (NVIDIA Inference Microservice) — deployed via **NIMPipeline** (not KServe InferenceService)

2. **Hugging Face Token** with access to required model repositories

3. **NVIDIA NGC API Key** for accessing NVIDIA services

## Building the Image

The LlamaStack container image must be built from the **v0.3.5 tag** of `meta-llama/llama-stack`. Do **NOT** build from `main` — the `main` branch has been rebranded to "OGX" and has removed the `eval`, `post_training`, `datasetio`, and `scoring` APIs that this demo requires.

```bash
git clone https://github.com/meta-llama/llama-stack.git
cd llama-stack
git checkout v0.3.5

podman build --platform=linux/amd64 \
  -f containers/Containerfile \
  --build-arg DISTRO_NAME=nvidia \
  --build-arg INSTALL_MODE=editable \
  --tag quay.io/ecosystem-appeng/llamastack-server-distribution:latest .

podman push quay.io/ecosystem-appeng/llamastack-server-distribution:latest
```

### Why v0.3.5?

| API | v0.3.5 nvidia distribution | `main` (v0.7.2+) |
|---|---|---|
| inference | `remote::nvidia` | `remote::nvidia` |
| post_training (customizer) | `remote::nvidia` | **REMOVED** |
| datasetio | `remote::nvidia` | **REMOVED** |
| eval | `remote::nvidia` | **REMOVED** |
| safety (guardrails) | `remote::nvidia` | `remote::nvidia` |
| scoring | `inline::basic` | **REMOVED** |
| agents | `inline::meta-reference` | **REMOVED** (replaced by `responses`) |

Additional breaking changes on `main`:
- Package renamed from `llama-stack` to `ogx`, CLI changed from `llama` to `ogx`
- Config schema changes: `url` -> `base_url`, `image_name` -> `distro_name`
- Incompatible with the RHOAI LlamaStack operator (which expects the `llama` CLI)

### Client Version

The notebook client must match the server version:

```
pip install "llama-stack-client>=0.3,<0.4"
```

Do **NOT** use `pip install --upgrade git+https://github.com/meta-llama/llama-stack-client-python.git@main` — that pulls the OGX-rebranded client (0.7.x) which is incompatible.

## RHOAI Default vs Custom NeMo Image

The RHOAI LlamaStack operator ships with a built-in distribution called `rh-dev`. This is **not sufficient** for this demo. Understanding the difference is critical:

| | RHOAI `rh-dev` (default) | Custom NeMo image (required for this demo) |
|---|---|---|
| **Image** | `registry.redhat.io/rhoai/odh-llama-stack-core-rhel9` (auto-resolved) | `quay.io/ecosystem-appeng/llamastack-server-distribution:latest` |
| **Inference** | `remote::vllm` | `remote::nvidia` |
| **Fine-tuning** | Not available | `remote::nvidia` (NeMo Customizer) |
| **Datasets** | Not available | `remote::nvidia` (NeMo Datastore / Entity Store) |
| **Evaluation** | `remote::trustyai_lmeval` (TrustyAI) | `remote::nvidia` (NeMo Evaluator) |
| **Safety** | `remote::trustyai_fms` (TrustyAI) | `remote::nvidia` (NeMo Guardrails) |
| **Scoring** | Not available | `inline::basic` |
| **Agents** | Not available | `inline::meta-reference` |
| **Use case** | Inference-only with KServe/vLLM | Full E2E workflow with NeMo Microservices |

The `rh-dev` distribution is designed for simple inference scenarios using KServe InferenceServices. It does not include NeMo-specific providers (customizer, datastore, evaluator, guardrails). Since this demo uses LlamaStack as a unified API to **all** NeMo services, the custom image with the `nvidia` distribution is required.

When using the RHOAI operator (Option B below), we use the `distribution.image` field to override the default `rh-dev` image with our custom NeMo image, getting operator lifecycle management with full NeMo functionality.

## Deployment

There are two deployment methods depending on your environment.

### Option A: Helm Chart (nemo-instances)

Use this when deploying LlamaStack as part of the NeMo Microservices Helm chart. This creates a standalone Deployment+Service without requiring the RHOAI LlamaStack operator.

```bash
cd deploy/nemo-instances

helm upgrade nemo-instances . \
  -n <namespace> \
  --set namespace.name=<namespace> \
  --set llamastack.enabled=true \
  --set llamastack.inferenceServiceName=<your-inferenceservice-name>
```

The Helm chart creates:
- **ConfigMap**: LlamaStack configuration with all NeMo providers (inference, safety, eval, post_training, datasetio, etc.)
- **Deployment**: LlamaStack container with environment variables pointing to NeMo microservices
- **Service**: ClusterIP service on port 8321

After deployment, LlamaStack is available at:
```
http://llamastack.<namespace>.svc.cluster.local:8321
```

### Option B: RHOAI LlamaStack Operator (RHOAI 3.x)

Use this when running on Red Hat OpenShift AI 3.x with the LlamaStack operator enabled. This deploys the custom NeMo image through the RHOAI operator, getting automatic lifecycle management, health checks, and service creation.

#### Step 1: Verify the LlamaStack operator is active

```bash
oc get datasciencecluster default-dsc -o jsonpath='{.spec.components.llamastackoperator.managementState}'
# Should print "Managed"
```

If not enabled:
```bash
oc patch datasciencecluster default-dsc --type=merge \
  -p '{"spec":{"components":{"llamastackoperator":{"managementState":"Managed"}}}}'
```

Verify the operator is running:
```bash
oc get pods -n redhat-ods-applications -l app.kubernetes.io/name=llama-stack-operator
```

#### Step 2: Create the ConfigMap

The ConfigMap key **must** be `config.yaml` — the operator hardcodes `LLAMA_STACK_CONFIG=/etc/llama-stack/config.yaml`.

```bash
cat <<'EOF' | oc apply -n $NAMESPACE -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: llamastack-nemo-config
data:
  config.yaml: |
    version: 2
    image_name: nvidia
    apis:
      - agents
      - datasetio
      - eval
      - files
      - inference
      - post_training
      - safety
      - scoring
      - tool_runtime
      - vector_io
    providers:
      inference:
        - provider_id: nvidia
          provider_type: remote::nvidia
          config:
            url: ${env.NVIDIA_BASE_URL}
            api_key: ${env.NVIDIA_API_KEY}
            append_api_version: ${env.NVIDIA_APPEND_API_VERSION:=True}
      vector_io:
        - provider_id: faiss
          provider_type: inline::faiss
          config:
            persistence:
              backend: meta-reference
              namespace: default
      safety:
        - provider_id: nvidia
          provider_type: remote::nvidia
          config:
            guardrails_service_url: ${env.GUARDRAILS_SERVICE_URL}
            config_id: ${env.NVIDIA_GUARDRAILS_CONFIG_ID}
            model: ${env.SAFETY_MODEL}
      agents:
        - provider_id: meta-reference
          provider_type: inline::meta-reference
          config:
            persistence:
              agent_state:
                backend: meta-reference
                namespace: default
                table_name: agent_state
              responses:
                backend: meta-reference-sql
                namespace: default
                table_name: agent_responses
      eval:
        - provider_id: nvidia
          provider_type: remote::nvidia
          config:
            evaluator_url: ${env.NVIDIA_EVALUATOR_URL}
      post_training:
        - provider_id: nvidia
          provider_type: remote::nvidia
          config:
            api_key: ${env.NVIDIA_API_KEY:=}
            dataset_namespace: ${env.NVIDIA_DATASET_NAMESPACE}
            project_id: ${env.NVIDIA_PROJECT_ID}
            customizer_url: ${env.NVIDIA_CUSTOMIZER_URL}
      datasetio:
        - provider_id: nvidia
          provider_type: remote::nvidia
          config:
            api_key: ${env.NVIDIA_API_KEY:=}
            dataset_namespace: ${env.NVIDIA_DATASET_NAMESPACE}
            project_id: ${env.NVIDIA_PROJECT_ID}
            datasets_url: ${env.NVIDIA_ENTITY_STORE_URL}
        - provider_id: localfs
          provider_type: inline::localfs
          config:
            kvstore:
              backend: meta-reference
              namespace: default
              table_name: datasets
      files:
        - provider_id: localfs
          provider_type: inline::localfs
          config:
            storage_dir: /tmp/files
            metadata_store:
              backend: meta-reference-sql
              namespace: default
              table_name: files
      scoring:
        - provider_id: basic
          provider_type: inline::basic
      tool_runtime:
        - provider_id: rag-runtime
          provider_type: inline::rag-runtime
    storage:
      backends:
        meta-reference:
          type: kv_sqlite
          db_path: /tmp/storage_store.db
        meta-reference-sql:
          type: sql_sqlite
          db_path: /tmp/sql_storage_store.db
      stores:
        metadata:
          backend: meta-reference
          namespace: default
        conversations:
          backend: meta-reference-sql
          namespace: default
          table_name: conversations
        inference:
          backend: meta-reference-sql
          namespace: default
          table_name: inference
        prompts:
          backend: meta-reference
          namespace: default
    models:
      - metadata: {}
        model_id: ${env.INFERENCE_MODEL}
        provider_id: nvidia
        model_type: llm
      - metadata: {}
        model_id: ${env.SAFETY_MODEL}
        provider_id: nvidia
        model_type: llm
    shields:
      - shield_id: demo-self-check-input-output
        provider_id: nvidia
        provider_shield_id: demo-self-check-input-output
        params:
          model: ${env.SAFETY_MODEL}
    vector_dbs: []
    datasets: []
    scoring_fns: []
    benchmarks: []
    tool_groups:
      - toolgroup_id: builtin::rag
        provider_id: rag-runtime
    server:
      port: 8321
EOF
```

#### Step 3: Create the LlamaStackDistribution CR

Replace the env var values with your namespace and NeMo service names.

```bash
cat <<'EOF' | oc apply -n $NAMESPACE -f -
apiVersion: llamastack.io/v1alpha1
kind: LlamaStackDistribution
metadata:
  name: llamastack
spec:
  replicas: 1
  server:
    distribution:
      image: "quay.io/ecosystem-appeng/llamastack-server-distribution:latest"
    userConfig:
      configMapName: llamastack-nemo-config
    containerSpec:
      name: llama-stack
      port: 8321
      resources:
        limits:
          cpu: "1"
          memory: 1Gi
        requests:
          cpu: 500m
          memory: 512Mi
      env:
        - name: NVIDIA_BASE_URL
          value: "http://meta-llama3-1b-instruct.<namespace>.svc.cluster.local:8000"
        - name: NVIDIA_API_KEY
          valueFrom:
            secretKeyRef:
              name: ngc-api
              key: NGC_API_KEY
        - name: INFERENCE_MODEL
          value: "meta/llama-3.2-1b-instruct"
        - name: SAFETY_MODEL
          value: "meta/llama-3.2-1b-instruct"
        - name: NVIDIA_DATASETS_URL
          value: "http://nemodatastore-sample.<namespace>.svc.cluster.local:8000"
        - name: NVIDIA_ENTITY_STORE_URL
          value: "http://nemoentitystore-sample.<namespace>.svc.cluster.local:8000"
        - name: NVIDIA_CUSTOMIZER_URL
          value: "http://nemocustomizer-sample.<namespace>.svc.cluster.local:8000"
        - name: NVIDIA_EVALUATOR_URL
          value: "http://nemoevaluator-sample.<namespace>.svc.cluster.local:8000"
        - name: GUARDRAILS_SERVICE_URL
          value: "http://nemoguardrails-sample.<namespace>.svc.cluster.local:8000"
        - name: NVIDIA_GUARDRAILS_CONFIG_ID
          value: "demo-self-check-input-output"
        - name: NVIDIA_DATASET_NAMESPACE
          value: "nvidia-e2e-tutorial"
        - name: NVIDIA_PROJECT_ID
          value: "llamastack-project"
        - name: NVIDIA_OUTPUT_MODEL_DIR
          value: "nvidia-e2e-tutorial/test-messages-model@v1"
        - name: NVIDIA_APPEND_API_VERSION
          value: "True"
EOF
```

#### Step 4: Verify

```bash
oc get llamastackdistribution -n $NAMESPACE
oc get pods -n $NAMESPACE | grep llama
oc logs -f deployment/llamastack -n $NAMESPACE
```

The service will be available at:
```
http://llamastack-service.<namespace>.svc.cluster.local:8321
```

#### Step 5: Fix NetworkPolicy (required for notebook access)

The LLS operator creates a restrictive `NetworkPolicy` that only allows traffic from pods with label `app.kubernetes.io/part-of=llama-stack`. Your notebook pod must have this label to connect:

```bash
oc label pod <notebook-pod-name> app.kubernetes.io/part-of=llama-stack -n $NAMESPACE
```

This label is ephemeral (lost on pod restart). For a permanent fix, add the label to the Notebook CR's pod template. The operator actively reconciles the NetworkPolicy, so deleting or patching it gets reverted.

### Operator vs Helm Comparison

| | Helm (Option A) | RHOAI Operator (Option B) |
|---|---|---|
| **Requires** | nemo-instances Helm chart | RHOAI 3.x with LlamaStack operator |
| **Service name** | `llamastack` | `llamastack-service` |
| **Lifecycle** | Manual (Helm upgrade) | Operator-managed (auto-restart, health checks) |
| **NetworkPolicy** | None | Auto-created (restrictive, requires pod labeling) |
| **Config location** | `/app/my-run.yaml` | `/etc/llama-stack/config.yaml` |
| **ConfigMap key** | `run.yaml` | `config.yaml` (must match) |

## Configuration

### config.py

Update `config.py` with your deployment URLs. The `NMS_NAMESPACE` environment variable controls the namespace used for service URLs:

```bash
export NMS_NAMESPACE=<your-namespace>
```

If using the **RHOAI operator** (Option B), update `LLAMASTACK_URL` in `config.py` to use the operator's service name:

```python
LLAMASTACK_URL = f"http://llamastack-service.{_NMS_NAMESPACE}.svc.cluster.local:8321"
```

### Environment Variables

The custom NeMo image requires the following environment variables (set automatically by the Helm chart or the operator CR):

| Variable | Description |
|---|---|
| `NVIDIA_BASE_URL` | NIM inference endpoint |
| `NVIDIA_API_KEY` | NGC API key |
| `NVIDIA_DATASETS_URL` | NeMo Datastore URL |
| `NVIDIA_ENTITY_STORE_URL` | NeMo Entity Store URL |
| `NVIDIA_CUSTOMIZER_URL` | NeMo Customizer URL |
| `NVIDIA_EVALUATOR_URL` | NeMo Evaluator URL |
| `GUARDRAILS_SERVICE_URL` | NeMo Guardrails URL |
| `NVIDIA_GUARDRAILS_CONFIG_ID` | Guardrails config ID |
| `NVIDIA_DATASET_NAMESPACE` | Dataset namespace |
| `NVIDIA_PROJECT_ID` | Entity Store project ID |
| `NVIDIA_OUTPUT_MODEL_DIR` | Output directory for fine-tuned models |
| `INFERENCE_MODEL` | Model identifier (e.g., `meta/llama-3.2-1b-instruct`) |
| `SAFETY_MODEL` | Safety model identifier |

## End-to-End Test

The `Llamastack_NVIDIA_E2E_Flow_RHOAI.ipynb` notebook provides a comprehensive end-to-end test.

### Test Workflow

1. **Setup and Configuration**: Configure URLs and initialize LlamaStack client
2. **Dataset Preparation**: Upload sample SQuAD dataset for fine-tuning
3. **Model Registration**: Register base model in Entity Store
4. **Inference Testing**: Test inference on the base model
5. **Evaluation**: Run evaluation on base model using sample datasets
6. **Model Customization**: Create fine-tuning job using NeMo Customizer (requires NeMo Operator)
7. **Evaluate Customized Model**: Compare metrics between base and fine-tuned models
8. **Safety / Guardrails**: Test content safety using NeMo Guardrails

### Sample Data

- **`sample_squad_data/`**: Stanford Question Answering Dataset (SQuAD) for fine-tuning
- **`sample_content_safety_test_data/`**: Content safety test cases for guardrails evaluation
- **`sample_squad_messages/`**: Message format datasets for chat-based evaluation

### Expected Results

- Base model BLEU score: ~3
- Customized model BLEU score: ~5-15

## Important: RHOAI InferenceService Limitation

### E2E Workflow Compatibility

NeMo Microservices enables a complete workflow:
1. **Evaluate the base model** 
2. **Fine-tune the model** (using Customizer)
3. **Evaluate the fine-tuned model** (Issue when using InferenceService)
4. **Apply guardrails**

### The Problem with RHOAI-Deployed Models

**Step 3 (Evaluating Fine-Tuned Models) fails when using RHOAI InferenceService.**

- RHOAI deploys models as `InferenceService` (KServe/ModelMesh)
- NeMo NIM deployed via `NIMPipeline` supports dynamic LoRA adapter loading
- `InferenceService` **cannot** dynamically load LoRA adapters from Entity Store

### Solution

For the complete E2E workflow, deploy models using **NIMPipeline** (not RHOAI InferenceService):
- See [Deploying Custom model.md](./Deploying%20Custom%20model.md) for instructions
- NIMPipeline supports dynamic LoRA loading via `NIM_PEFT_SOURCE` environment variable

## Troubleshooting

- **Deployment Issues**: Check pod logs with `oc logs -f deployment/llamastack`
- **Service Connectivity**: Verify NeMo microservices are running and accessible
- **Model Loading**: Ensure base models are available in NIM
- **API Keys**: Confirm NGC and Hugging Face tokens are valid
- **Fine-Tuned Model Evaluation Fails**: Verify model is deployed via NIMPipeline, not RHOAI InferenceService
- **ConnectTimeout from notebook**: The LLS operator creates a restrictive NetworkPolicy — label your notebook pod with `app.kubernetes.io/part-of=llama-stack`
- **Config file not found (operator)**: Ensure the ConfigMap key is `config.yaml`, not `run.yaml`
- **Client version mismatch**: Use `llama-stack-client>=0.3,<0.4` — do not install from `@main`
