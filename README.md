# NVIDIA NeMo Microservices on OpenShift

Helm charts for deploying NVIDIA NeMo microservices infrastructure and samples on OpenShift.

## Prerequisites

- OpenShift 4.x cluster
- Helm 3.x
- `oc` CLI configured
- NGC API key (for pulling NVIDIA images)
- GPU nodes (for training/inference workloads)

## Charts

- **`charts/nemo-infra`**: Infrastructure components (databases, MLflow, Argo, Milvus, Volcano, Operators)
- **`charts/nemo-samples`**: Example NeMo microservices deployments

## Quick Start

### 1. Infrastructure Deployment

Deploy all infrastructure components (PostgreSQL, MLflow, Argo Workflows, Milvus, Volcano, Operators):

```bash
cd charts/nemo-infra
helm install nemo-infra . -n <namespace> --create-namespace
```

📖 **Full documentation**: [charts/nemo-infra/README.md](charts/nemo-infra/README.md)

### 2. Samples Deployment

Deploy example NeMo microservices (Customizer, Datastore, Entity Store, Evaluator, Guardrail, NIM services):

```bash
cd charts/nemo-samples
helm install nemo-samples . -n <namespace>
```

📖 **Full documentation**: [charts/nemo-samples/README.md](charts/nemo-samples/README.md)

