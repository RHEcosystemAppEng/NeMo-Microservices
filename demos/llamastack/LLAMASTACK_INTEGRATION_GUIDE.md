# LlamaStack Integration with NeMo Microservices

## Overview

This guide explains how LlamaStack integrates with NeMo Microservices across the four notebooks in the e2e-test workflow, and compares it conceptually with the direct NeMo approach from the e2e-notebook.ipynb.

---

## Table of Contents

1. [What is LlamaStack?](#what-is-llamastack)
2. [LlamaStack Integration Across Notebooks](#llamastack-integration-across-notebooks)
   - [1. Data Preparation](#1-data-preparation-1_data_prepipynb)
   - [2. Fine-tuning & Inference](#2-fine-tuning--inference-2_finetune_inferenceipynb)
   - [3. Model Evaluation](#3-model-evaluation-3_model_evaluationipynb)
   - [4. Safety Guardrails](#4-safety-guardrails-4_adding_safety_guardrailsipynb)
3. [Conceptual Differences: LlamaStack vs Direct NeMo](#conceptual-differences-llamastack-vs-direct-nemo)
4. [When to Use Each Approach](#when-to-use-each-approach)

---

## What is LlamaStack?

**LlamaStack** is a unified abstraction layer that provides:

- **Provider-agnostic APIs**: Work with multiple backends (NVIDIA, Meta, Together, etc.) through a single interface
- **Standardized data types**: Consistent Python objects for models, datasets, benchmarks, and configurations
- **Client library**: `LlamaStackAsLibraryClient` for programmatic access
- **Resource management**: Centralized registration and tracking of models, datasets, shields
- **Type safety**: Pydantic models ensure correct API usage

In the NeMo integration, LlamaStack acts as a **wrapper** around NeMo Microservices, providing a cleaner, more Pythonic interface to the underlying REST APIs.

---

## LlamaStack Integration Across Notebooks

### 1. Data Preparation (`1_data_prep.ipynb`)

#### LlamaStack Approach

```python
# Initialize client
from llama_stack.core.library_client import LlamaStackAsLibraryClient
client = LlamaStackAsLibraryClient("nvidia")
client.initialize()

# Register dataset using LlamaStack API
response = client.datasets.register(
    purpose="post-training/messages",
    dataset_id=DATASET_NAME,
    source={
        "type": "uri",
        "uri": f"hf://datasets/{repo_id}"
    },
    metadata={
        "format": "json",
        "description": "Tool calling xLAM dataset",
        "provider_id": "nvidia"
    }
)
```

**Key Features:**
- Uses `client.datasets.register()` instead of direct REST calls
- Returns typed Python objects (`DatasetRegisterResponse`)
- Automatic validation of parameters
- Integrated with LlamaStack's resource tracking

#### Direct NeMo Approach

```python
# Direct REST API call
resp = requests.post(
    url=f"{ENTITY_STORE_URL}/v1/datasets",
    json={
        "name": DATASET_NAME,
        "namespace": NMS_NAMESPACE,
        "description": "Tool calling xLAM dataset",
        "files_url": f"hf://datasets/{NMS_NAMESPACE}/{DATASET_NAME}",
        "project": "tool_calling",
    },
)
```

**Key Features:**
- Direct HTTP requests to Entity Store
- Manual JSON construction
- Manual error handling
- No type safety

#### Conceptual Difference

| Aspect | LlamaStack | Direct NeMo |
|--------|-----------|-------------|
| **Abstraction** | High-level Python API | Low-level REST API |
| **Type Safety** | Pydantic models | Raw JSON dicts |
| **Error Handling** | Built-in validation | Manual checking |
| **Portability** | Provider-agnostic | NeMo-specific |

---

### 2. Fine-tuning & Inference (`2_finetune_inference.ipynb`)

#### LlamaStack Approach

```python
from llama_stack.core.datatypes import Api
from llama_stack.apis.post_training import (
    TrainingConfig, DataConfig, OptimizerConfig, LoraFinetuningConfig
)

# Access post_training provider
post_training = client.async_client.impls[Api.post_training]

# Create structured config objects
training_config = TrainingConfig(
    n_epochs=2,
    data_config=DataConfig(
        batch_size=16,
        dataset_id=DATASET_NAME,
        shuffle=True
    ),
    optimizer_config=OptimizerConfig(
        optimizer_type=OptimizerType.adamw,
        lr=0.0001
    )
)

algorithm_config = LoraFinetuningConfig(
    lora_attn_modules=[],
    apply_lora_to_mlp=True,
    rank=8,
    alpha=16
)

# Start training job
res = await post_training.supervised_fine_tune(
    job_uuid=f"finetune-{unique_suffix}",
    model="meta/llama-3.2-1b-instruct@v1.0.0+A100",
    training_config=training_config,
    algorithm_config=algorithm_config
)
```

**Key Features:**
- Strongly-typed configuration objects
- Async/await support
- Automatic parameter validation
- Structured response objects

#### Direct NeMo Approach

```python
# Direct REST API call with manual JSON construction
training_params = {
    "name": "llama-3.2-1b-xlam-ft",
    "output_model": f"{NMS_NAMESPACE}/llama-3.2-1b-xlam-run1",
    "config": f"{BASE_MODEL}@{BASE_MODEL_VERSION}",
    "dataset": {"name": DATASET_NAME, "namespace": NMS_NAMESPACE},
    "hyperparameters": {
        "training_type": "sft",
        "finetuning_type": "lora",
        "epochs": 1,
        "batch_size": 8,
        "learning_rate": 0.0001,
        "lora": {
            "adapter_dim": 32,
            "adapter_dropout": 0.1
        }
    }
}

resp = requests.post(
    f"{CUSTOMIZER_URL}/v1/customization/jobs",
    json=training_params
)
```

**Key Features:**
- Manual JSON construction
- Synchronous HTTP requests
- No parameter validation
- Raw dictionary responses

#### Conceptual Difference

| Aspect | LlamaStack | Direct NeMo |
|--------|-----------|-------------|
| **Configuration** | Type-safe config objects | Raw JSON dictionaries |
| **Validation** | Compile-time + runtime | Runtime only (server-side) |
| **IDE Support** | Full autocomplete | No autocomplete |
| **Async Support** | Native async/await | Manual async handling |
| **Model Updates** | Auto-sync with routing table | Manual model discovery |

---

### 3. Model Evaluation (`3_model_evaluation.ipynb`)

#### LlamaStack Approach

```python
from llama_stack.apis.eval import BenchmarkConfig, ModelCandidate, SamplingParams

# Register benchmark
response = client.benchmarks.register(
    benchmark_id=benchmark_id,
    dataset_id=repo_id,
    scoring_functions=[],
    metadata=simple_tool_calling_eval_config
)

# Access eval provider
eval_impl = client.async_client.impls[Api.eval]

# Create eval job with typed config
benchmark_config = BenchmarkConfig(
    eval_candidate=ModelCandidate(
        type="model",
        model=BASE_MODEL,
        sampling_params=SamplingParams()
    )
)

response = await eval_impl.run_eval(
    benchmark_id=benchmark_id,
    benchmark_config=benchmark_config
)

# Get results
job_results = await eval_impl.job_result(
    benchmark_id=benchmark_id,
    job_id=job_id
)
```

**Key Features:**
- Benchmark registration through client
- Typed config objects (`BenchmarkConfig`, `ModelCandidate`)
- Async job management
- Structured result objects

#### Direct NeMo Approach

```python
# Create evaluation target manually
data = {
    "type": "model",
    "name": "llama-3-1b-instruct",
    "model": {
        "api_endpoint": {
            "url": f"{NIM_URL}/v1/completions",
            "model_id": f"{BASE_MODEL}"
        }
    }
}
res = requests.post(
    f"{EVALUATOR_URL}/v1/evaluation/targets",
    json=data
)

# Start eval job
res = requests.post(
    f"{EVALUATOR_URL}/v1/evaluation/jobs",
    json={
        "config": simple_tool_calling_eval_config,
        "target": "default/llama-3-1b-instruct"
    }
)

# Poll for results
res = requests.get(
    f"{EVALUATOR_URL}/v1/evaluation/jobs/{job_id}/results"
)
```

**Key Features:**
- Manual target creation
- Raw JSON configs
- Manual polling
- Dictionary-based results

#### Conceptual Difference

| Aspect | LlamaStack | Direct NeMo |
|--------|-----------|-------------|
| **Benchmark Setup** | Declarative registration | Imperative REST calls |
| **Target Management** | Implicit (in config) | Explicit creation |
| **Job Tracking** | Built-in async helpers | Manual polling loops |
| **Result Parsing** | Structured objects | Raw JSON parsing |

---

### 4. Safety Guardrails (`4_adding_safety_guardrails.ipynb`)

#### LlamaStack Approach

```python
# Initialize client with guardrails config
os.environ["NVIDIA_GUARDRAILS_CONFIG_ID"] = "demo-self-check-input-output"

client = LlamaStackAsLibraryClient("nvidia")
client.initialize()

# The provider configuration automatically includes safety:
# providers:
#   safety:
#   - provider_id: nvidia
#     provider_type: remote::nvidia
#     config:
#       guardrails_service_url: ${env.GUARDRAILS_SERVICE_URL}
#       config_id: ${env.NVIDIA_GUARDRAILS_CONFIG_ID}

# Guardrails are transparently applied through LlamaStack's safety layer
```

**Key Features:**
- Configuration through environment variables
- Provider abstraction (could swap to different guardrails service)
- Centralized safety configuration
- Transparent application to inference calls

#### Direct NeMo Approach

```python
# Create guardrails config directly
headers = {"Accept": "application/json", "Content-Type": "application/json"}
data = {
    "name": "demo-self-check-input-output",
    "namespace": "default",
    "description": "demo streaming self-check",
    "data": {
        "prompts": [...],
        "rails": {
            "input": {"flows": ["self check input"]},
            "output": {"flows": ["self check output"]}
        }
    }
}
response = requests.post(
    f"{GUARDRAILS_URL}/v1/guardrail/configs",
    headers=headers,
    json=data
)

# Use guardrails in inference
data = {
    "model": "meta/llama-3.2-1b-instruct",
    "messages": [{"role": "user", "content": "query"}],
    "guardrails": {"config_id": "demo-self-check-input-output"}
}
response = requests.post(
    f"{GUARDRAILS_URL}/v1/guardrail/chat/completions",
    headers=headers,
    json=data
)
```

**Key Features:**
- Direct guardrails configuration
- Explicit config attachment to inference
- Full control over config structure
- Service-specific endpoints

#### Conceptual Difference

| Aspect | LlamaStack | Direct NeMo |
|--------|-----------|-------------|
| **Config Management** | Environment-based | Explicit REST creation |
| **Application** | Provider layer (transparent) | Explicit per-request |
| **Flexibility** | Provider-swappable | Service-specific |
| **Integration** | Unified with inference | Separate guardrails endpoints |

---

## Conceptual Differences: LlamaStack vs Direct NeMo

### Philosophy

**LlamaStack (Platform-Oriented)**
- **Goal**: Provide a unified platform for AI development
- **Focus**: Developer experience, portability, abstraction
- **Trade-off**: Some loss of fine-grained control
- **Best for**: Multi-provider environments, rapid prototyping, production applications

**Direct NeMo (Service-Oriented)**
- **Goal**: Direct access to NeMo capabilities
- **Focus**: Full control, NeMo-specific features, transparency
- **Trade-off**: More verbose, service-specific code
- **Best for**: NeMo-specific deployments, deep customization, debugging

### Key Architectural Differences

| Dimension | LlamaStack | Direct NeMo |
|-----------|-----------|-------------|
| **Abstraction Level** | High (Python API) | Low (REST API) |
| **Type Safety** | Strong (Pydantic models) | Weak (JSON dicts) |
| **Error Handling** | Centralized, typed exceptions | Manual HTTP error checking |
| **Async Support** | Native async/await | Manual async handling |
| **Provider Flexibility** | Swappable providers | Locked to NeMo |
| **Code Verbosity** | Concise, declarative | Verbose, imperative |
| **IDE Support** | Full autocomplete | Limited autocomplete |
| **Configuration** | Centralized YAML + env vars | Distributed across calls |

### Integration Patterns

**LlamaStack Pattern**
```
User Code → LlamaStack Client → Provider Layer → NeMo REST APIs
```
- Single initialization
- Unified interface
- Provider abstraction
- Resource tracking

**Direct NeMo Pattern**
```
User Code → HTTP Client → NeMo REST APIs
```
- Per-request setup
- Service-specific code
- Direct communication
- Manual tracking

---

## When to Use Each Approach

### Use LlamaStack When:

1. **Multi-Provider Support**: You might switch between NVIDIA, Meta, or other providers
2. **Type Safety**: You want compile-time checks and IDE autocomplete
3. **Rapid Development**: You need to prototype quickly with less boilerplate
4. **Production Apps**: You're building applications that need stable APIs
5. **Team Collaboration**: Multiple developers need consistent interfaces
6. **Resource Management**: You need centralized tracking of models, datasets, benchmarks

### Use Direct NeMo When:

1. **NeMo-Specific Features**: You need features not exposed through LlamaStack
2. **Deep Debugging**: You need to inspect raw HTTP requests/responses
3. **Fine-Grained Control**: You need precise control over every parameter
4. **Learning**: You're learning NeMo Microservices internals
5. **Custom Workflows**: Your workflow doesn't fit LlamaStack's abstractions
6. **Simple Scripts**: Single-use scripts where setup overhead isn't justified

---

## Summary

**LlamaStack** provides a **unified, type-safe, provider-agnostic abstraction layer** over NeMo Microservices. It trades some fine-grained control for:
- Better developer experience
- Portability across providers
- Type safety and IDE support
- Centralized configuration
- Less boilerplate code

**Direct NeMo** provides **full, transparent access** to all NeMo capabilities through REST APIs. It trades verbosity and manual management for:
- Complete control
- Direct access to all features
- Transparency in communication
- Easier debugging
- Service-specific optimizations

Both approaches ultimately accomplish the same tasks—the choice depends on your development priorities, team requirements, and deployment environment.
