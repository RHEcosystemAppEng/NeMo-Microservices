# NVIDIA NeMo Microservices on OpenShift

Helm charts for deploying NVIDIA NeMo microservices infrastructure and demos on OpenShift.

## Prerequisites

- OpenShift 4.x cluster
- Helm 3.x
- `oc` CLI configured
- NGC API key (for pulling NVIDIA images)
- GPU nodes (for training/inference workloads)

## Charts

- **`deploy/nemo-infra`**: Infrastructure components (databases, MLflow, Argo, Milvus, Volcano, Operators)
- **`deploy/nemo-instances`**: Example NeMo microservices deployments

## Quick Start

### 1. Infrastructure Deployment

Deploy all infrastructure components (PostgreSQL, MLflow, Argo Workflows, Milvus, Volcano, Operators):

```bash
cd deploy/nemo-infra
helm install nemo-infra . -n <namespace> --create-namespace
```

📖 **Full documentation**: [deploy/nemo-infra/README.md](deploy/nemo-infra/README.md)

### 2. NeMo Instances Deployment

Deploy example NeMo microservices (Customizer, Datastore, Entity Store, Evaluator, Guardrail, NIM services):

```bash
cd deploy/nemo-instances
helm install nemo-instances . -n <namespace>
```

📖 **Full documentation**: [deploy/nemo-instances/README.md](deploy/nemo-instances/README.md)

