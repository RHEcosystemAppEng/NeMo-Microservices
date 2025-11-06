# NeMo Infrastructure Components Helm Chart

A Helm chart for deploying NVIDIA NeMo infrastructure components on OpenShift, including PostgreSQL databases, MLflow, Argo Workflows, Milvus, OpenTelemetry, MinIO, Jupyter Notebook, and Volcano Scheduler.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Components](#components)
   - [Datastore PostgreSQL](#datastore-postgresql)
   - [Entity Store PostgreSQL](#entity-store-postgresql)
   - [Customizer Components](#customizer-components)
   - [Guardrail PostgreSQL](#guardrail-postgresql)
   - [Evaluator Components](#evaluator-components)
   - [Jupyter Notebook](#jupyter-notebook)
   - [MinIO](#minio)
   - [Volcano Scheduler](#volcano-scheduler)
6. [Installation](#installation)
7. [Uninstallation](#uninstallation)
8. [Troubleshooting](#troubleshooting)
9. [OpenShift Specific Configuration](#openshift-specific-configuration)
10. [Multi-Tenant Safety](#multi-tenant-safety)

## Overview

This Helm chart deploys all infrastructure components required for NVIDIA NeMo microservices on OpenShift. It manages dependencies through Helm subcharts and provides OpenShift-specific configurations including Security Context Constraints (SCCs) and RBAC.

> ⚠️ **IMPORTANT: DEVELOPMENT ENVIRONMENT ONLY**
> 
> This Helm chart is configured for **development/testing environments only**. It uses hardcoded default passwords for ease of deployment. **DO NOT use these defaults in production**. For production deployments, all passwords must be moved to externally-managed Kubernetes Secrets. See [SECRETS-AUDIT.md](../SECRETS-AUDIT.md) for details.

### Key Features

- **Unified Deployment**: Single Helm command deploys all infrastructure components
- **Conditional Installation**: Enable/disable components via `values.yaml`
- **OpenShift Optimized**: Includes SCC configurations, RBAC, and OpenShift-specific settings
- **Namespace Scoped**: Components can be scoped to specific namespaces for multi-tenant safety
- **Persistent Storage**: Configurable PVCs for all stateful components
- **Development-Friendly**: Default passwords simplify local development (dev-only)

## Prerequisites

- OpenShift 4.x cluster
- Helm 3.x installed
- `oc` CLI configured with cluster access
- Sufficient cluster resources (CPU, memory, storage)
- Access to container registries (Docker Hub, NGC, etc.)
- **NGC API Key** for accessing NVIDIA Helm repository (required for NeMo Operator)
  ```bash
  # Add NGC Helm repository (requires authentication)
  helm repo add nvidia-nemo https://helm.ngc.nvidia.com/nvidia-nemo
  helm repo update
  ```

## Quick Start

### Basic Installation

```bash
# Add Helm repository (if using remote chart)
# helm repo add nemo-infra <repository-url>
# helm repo update

# Install with default values
helm install nemo-infra ./charts/nemo-infra \
  -n <namespace> \
  --create-namespace

# Install with Volcano enabled
helm install nemo-infra ./charts/nemo-infra \
  -n arhkp-nemo-helm \
  --create-namespace \
  --set install.volcano=true
```

### Verify Installation

```bash
# Check all pods are running
oc get pods -n <namespace>

# Check specific component
oc get pods -n <namespace> | grep postgresql
oc get pods -n <namespace> | grep volcano
```

## Configuration

### Main Configuration File

The main configuration is in `values.yaml`. Key sections:

- `namespace`: Namespace configuration
- `pvc`: Persistent volume claim settings
- `localPathProvisioner`: Local path provisioner for storage
- `install`: Component enable/disable flags

### Component Installation Flags

```yaml
install:
  datastore: true      # Datastore PostgreSQL
  entityStore: true    # Entity Store PostgreSQL
  customizer: true     # Customizer (PostgreSQL, MLflow, OpenTelemetry)
  guardrail: true      # Guardrail PostgreSQL
  evaluator: true      # Evaluator (PostgreSQL, Argo, Milvus, OpenTelemetry)
  jupyter: true        # Jupyter Notebook
  volcano: true        # Volcano Scheduler
```

### Customizing Values

```bash
# Install with custom values
helm install nemo-infra ./charts/nemo-infra \
  -n <namespace> \
  --set install.volcano=true \
  --set namespace.name=my-namespace \
  --set pvc.storageClass=gp3-csi
```

## Components

### Datastore PostgreSQL

**Purpose**: Database for NeMo Datastore microservice

**Configuration**:
- Chart: Bitnami PostgreSQL 16.0.0
- Default Storage: 1Gi
- Service: `nemo-infra-datastore-postgresql`

**Enable/Disable**:
```yaml
install:
  datastore: true
```

### Entity Store PostgreSQL

**Purpose**: Database for NeMo Entity Store microservice

**Configuration**:
- Chart: Bitnami PostgreSQL 16.0.0
- Default Storage: 1Gi
- Service: `nemo-infra-entity-store-postgresql`

**Enable/Disable**:
```yaml
install:
  entityStore: true
```

### Customizer Components

**Components**:
- PostgreSQL (database for Customizer)
- MLflow (model tracking and registry)
- OpenTelemetry Collector (observability)

**Configuration**:
```yaml
install:
  customizer: true
```

**Services**:
- `nemo-infra-customizer-postgresql`: PostgreSQL database
- `nemo-infra-customizer-mlflow-tracking`: MLflow tracking server
- `nemo-infra-customizer-opentelemetry`: OpenTelemetry collector

**MLflow Configuration**:
- Backend: PostgreSQL
- Artifacts: MinIO storage
- Default Storage: 8Gi

### Guardrail PostgreSQL

**Purpose**: Database for NeMo Guardrail microservice

**Configuration**:
- Chart: Bitnami PostgreSQL 16.0.0
- Default Storage: 1Gi
- Service: `nemo-infra-guardrail-postgresql`

**Enable/Disable**:
```yaml
install:
  guardrail: true
```

### Evaluator Components

**Components**:
- PostgreSQL (database for Evaluator)
- Argo Workflows (workflow orchestration)
- Milvus (vector database)
- OpenTelemetry Collector (observability)

**Configuration**:
```yaml
install:
  evaluator: true
```

**Services**:
- `nemo-infra-evaluator-postgresql`: PostgreSQL database
- `nemo-infra-argo-workflows-server`: Argo Workflows server
- `nemo-infra-argo-workflows-workflow-controller`: Argo controller
- `nemo-infra-evaluator-milvus`: Milvus vector database
- `nemo-infra-evaluator-opentelemetry`: OpenTelemetry collector

**Argo Workflows**:
- CRDs: Installed automatically (`crds.install: true`)
- Auth Mode: Server mode
- Single Namespace: Enabled

**Milvus**:
- Mode: Standalone
- Default Storage: 50Gi
- OpenShift SCC: `anyuid` (configured via RBAC)

### NeMo Operator

**Purpose**: Kubernetes operator for managing NeMo microservices and training jobs

**Configuration**:
```yaml
install:
  nemoOperator: true
```

**Details**:
- Chart: NVIDIA NeMo Operator v25.06 (exact from quickstart line 122)
- Repository: `https://helm.ngc.nvidia.com/nvidia-nemo` (requires NGC authentication)
- Image: `nvcr.io/nvidia/nemo-operator:v25.06`
- Resource Limits: 512Mi memory limit, 256Mi memory request (exact from quickstart lines 124-125)
- Post-install Hook: Automatically patches ServiceAccount with `ngc-secret` (matches quickstart line 129)
- Pod Restart: Automatically restarts operator pods after patching (matches quickstart line 132)
- CRDs: Installs NeMo Custom Resource Definitions (nemocustomizers, nemodatastores, etc.)

**Prerequisites**:
- NGC Helm repository must be added and authenticated (quickstart lines 118-119):
  ```bash
  helm repo add nvidia-nemo https://helm.ngc.nvidia.com/nvidia-nemo
  helm repo update
  ```
- **NGC image pull secret (`ngc-secret`) must exist in the namespace BEFORE installation** (quickstart lines 43-47):
  ```bash
  oc create secret docker-registry ngc-secret \
    --docker-server=nvcr.io \
    --docker-username='$oauthtoken' \
    --docker-password=$NGC_API_KEY \
    -n <namespace>
  ```
- Volcano scheduler must be installed (required dependency, quickstart Step 3)

**Installation Process** (matches quickstart Step 4 exactly):
1. Helm installs NeMo Operator subchart with resource limits (lines 122-126)
2. Post-install hook patches ServiceAccount with `ngc-secret` (line 129)
3. Post-install hook restarts operator pods to pick up the secret (line 132)

**Enable/Disable**:
```yaml
install:
  nemoOperator: true  # or false
```

### NIM Operator

**Purpose**: Kubernetes operator for managing NVIDIA NIM (NVIDIA Inference Microservices)

**Configuration**:
```yaml
install:
  nimOperator: true
```

**Details**:
- Chart: k8s-nim-operator v3.0.0 (local OpenShift-specific chart)
- Repository: Local chart from `deploy-on-openshift/deployments/helm/k8s-nim-operator`
- Image: `ghcr.io/nvidia/k8s-nim-operator:release-3.0` (exact from chart values.yaml)
- Resource Limits: 512Mi memory limit, 256Mi memory request (exact from quickstart lines 143-144)
- CRDs: Installs NIM Custom Resource Definitions (nimpipelines, nimcaches, nimservices, nimbuilds)

**Prerequisites**:
- **CRITICAL**: Uses local OpenShift-specific Helm chart (NOT the official NVIDIA repo chart)
  - The official NVIDIA Helm repository chart (`nvidia/k8s-nim-operator`) is NOT compatible with OpenShift
  - due to security context and permission differences (quickstart line 150)
  - Chart must be packaged: `cd deploy-on-openshift/deployments/helm/k8s-nim-operator && helm package . --destination ../../../../NeMo-Microservices/charts/nemo-infra/charts`
- NeMo Operator must be installed (required dependency)

**Installation Process** (matches quickstart Step 5 exactly):
1. Helm installs NIM Operator subchart with resource limits (lines 141-145)
2. No post-install steps required (unlike NeMo Operator)

**Enable/Disable**:
```yaml
install:
  nimOperator: true  # or false
```

### Jupyter Notebook

**Purpose**: Jupyter Notebook server for NeMo development and testing

**Configuration**:
```yaml
jupyter:
  enabled: true
  deploymentName: jupyter-notebook
  serviceName: jupyter-service
  serviceType: NodePort
  # nodePort: 30036  # Optional: Auto-assigned if not specified
```

**OpenShift Configuration**:
- SCC: `anyuid` (configured via RBAC)
- Service Type: NodePort (auto-assigned port)

**Custom Content**:
- Config: `notebookContent` (config.py)
- Notebook: `configContent` (e2e-notebook.ipynb)

### MinIO

**Purpose**: Object storage for MLflow artifacts and other data

**Configuration**:
- Default Storage: 50Gi
- Service: `nemo-infra-minio`
- Buckets: Configured via values

### Volcano Scheduler

**Purpose**: Advanced scheduler for Kubernetes workloads, required for NeMo Operator

**Configuration**:
```yaml
install:
  volcano: true
```

**Components**:
1. **Volcano Admission Webhook**: Validates and mutates resources
2. **Volcano Controllers**: Manages Volcano resources
3. **Volcano Scheduler**: Schedules pods using Volcano algorithms
4. **Volcano Init Job**: Initial setup job

**OpenShift Configuration**:
- SCC: `privileged` (required for hostPath volumes)
- Webhooks: Namespace-scoped for multi-tenant safety

**Resource Naming**:
- Resources use Helm release name prefix: `nemo-infra-*`
- Example: `nemo-infra-admission`, `nemo-infra-scheduler`, `nemo-infra-controllers`

**Services**:
- `nemo-infra-admission-service`: Admission webhook service

**Webhooks**:
- `volcano-admission-service-jobs-validate`
- `volcano-admission-service-pods-validate`
- `volcano-admission-service-queues-validate`

All webhooks are scoped to the deployment namespace via `namespaceSelector`.

## Installation

### Full Installation

```bash
# Navigate to chart directory
cd charts/nemo-infra

# Update dependencies
helm dependency update

# Install all components
helm install nemo-infra . \
  -n arhkp-nemo-helm \
  --create-namespace \
  --set install.volcano=true
```

### Partial Installation

```bash
# Install only specific components
helm install nemo-infra . \
  -n arhkp-nemo-helm \
  --create-namespace \
  --set install.datastore=true \
  --set install.entityStore=true \
  --set install.customizer=false \
  --set install.guardrail=false \
  --set install.evaluator=false \
  --set install.jupyter=false \
  --set install.volcano=false
```

### Upgrade Installation

```bash
# Upgrade existing installation
helm upgrade nemo-infra . \
  -n arhkp-nemo-helm \
  --set install.volcano=true
```

## Uninstallation

### Standard Uninstall

```bash
# Uninstall Helm release
helm uninstall nemo-infra -n arhkp-nemo-helm

# Clean up PVCs (optional)
oc delete pvc --all -n arhkp-nemo-helm

# Clean up webhooks (optional)
oc delete validatingwebhookconfigurations \
  volcano-admission-service-jobs-validate \
  volcano-admission-service-pods-validate \
  volcano-admission-service-queues-validate
```

### Full Cleanup

```bash
# Uninstall
helm uninstall nemo-infra -n arhkp-nemo-helm

# Delete PVCs
oc delete pvc --all -n arhkp-nemo-helm

# Delete remaining resources
oc delete all --all -n arhkp-nemo-helm
oc delete configmap,secret,serviceaccount,role,rolebinding --all -n arhkp-nemo-helm

# Delete cluster resources (if needed)
oc delete clusterrole,clusterrolebinding -l component=volcano
oc delete validatingwebhookconfigurations | grep volcano
```

## Troubleshooting

### Pods Not Starting

**Check pod status:**
```bash
oc get pods -n <namespace>
oc describe pod <pod-name> -n <namespace>
oc logs <pod-name> -n <namespace>
```

### Image Pull Errors

**Verify image pull secrets:**
```bash
oc get secrets -n <namespace> | grep pull
oc describe pod <pod-name> -n <namespace> | grep -A 5 "ImagePull"
```

**Common fixes:**
- Ensure image pull secrets are configured
- Check registry access
- Verify image tags exist

### Storage Issues

**Check PVC status:**
```bash
oc get pvc -n <namespace>
oc describe pvc <pvc-name> -n <namespace>
```

**Common fixes:**
- Verify storage class exists
- Check storage quota
- Ensure sufficient storage capacity

### Volcano Issues

**Check Volcano components:**
```bash
oc get pods -n <namespace> | grep volcano
oc get deployments -n <namespace> | grep volcano
oc get validatingwebhookconfigurations | grep volcano
```

**Common issues:**

1. **Scheduler pod failing:**
   - Verify `privileged` SCC is granted
   - Check service account: `nemo-infra-scheduler`
   - Command: `oc adm policy add-scc-to-user privileged system:serviceaccount:<namespace>:nemo-infra-scheduler`

2. **Admission pod failing:**
   - Check ClusterRole permissions
   - Verify service exists: `nemo-infra-admission-service`
   - Check webhook configuration

3. **Webhook errors:**
   - Verify webhooks are scoped to correct namespace
   - Check service endpoints
   - Verify certificates

### Argo Workflows Issues

**Check Argo components:**
```bash
oc get pods -n <namespace> | grep argo
oc get crd | grep workflow
```

**Common issues:**
- CRDs not installed: Ensure `evaluator-argo.crds.install: true`
- Controller not starting: Check service account permissions

### PostgreSQL Connection Issues

**Check PostgreSQL pods:**
```bash
oc get pods -n <namespace> | grep postgresql
oc logs <postgresql-pod> -n <namespace>
```

**Common fixes:**
- Verify service names match in connection strings
- Check authentication credentials
- Ensure pods are ready before connecting

## OpenShift Specific Configuration

### Security Context Constraints (SCCs)

**Configured SCCs:**

1. **anyuid** - Used by:
   - Jupyter Notebook
   - Milvus

2. **privileged** - Used by:
   - Volcano Scheduler (required for hostPath volumes)

**SCC Configuration:**
- Managed via RBAC Role/Binding in templates
- Jobs can also grant SCCs via `oc adm policy` commands

### RBAC Configuration

**Service Accounts:**
- Each component has its own service account
- Names follow pattern: `<release-name>-<component>`

**Roles and RoleBindings:**
- Namespace-scoped for SCC access
- Cluster-scoped for Volcano webhooks and CRDs

### Storage Configuration

**Storage Classes:**
- Default: `gp3-csi` (AWS EBS)
- Configurable via `values.yaml`:
  ```yaml
  pvc:
    storageClass: gp3-csi
  ```

**Local Path Provisioner:**
- Optional local storage provisioner
- Enable via `localPathProvisioner.enabled: true`

## Multi-Tenant Safety

### Volcano Webhook Scoping

Volcano webhooks are scoped to specific namespaces to prevent interference with other workloads.

**Configuration:**
```yaml
volcano:
  custom:
    webhooks_namespace_selector_expressions:
      - key: kubernetes.io/metadata.name
        operator: In
        values:
          - arhkp-nemo-helm  # Deployment namespace
          # Add additional namespaces if needed
```

**Default Behavior:**
- Webhooks only affect resources in specified namespaces
- Other namespaces are unaffected by Volcano webhooks

**Adding Additional Namespaces:**
```yaml
volcano:
  custom:
    webhooks_namespace_selector_expressions:
      - key: kubernetes.io/metadata.name
        operator: In
        values:
          - arhkp-nemo-helm
          - another-namespace
          - shared-namespace
```

### Resource Isolation

- Each component uses namespace-scoped resources
- PVCs are namespace-scoped
- Services are namespace-scoped
- Only webhooks and CRDs are cluster-scoped (with namespace selectors)

## Chart Structure

```
nemo-infra/
├── Chart.yaml              # Chart metadata and dependencies
├── values.yaml             # Default configuration values
├── Chart.lock              # Locked dependency versions
├── templates/
│   ├── _helpers.tpl        # Template helpers
│   ├── namespace.yaml      # Namespace resource
│   ├── jupyter/            # Jupyter Notebook templates
│   ├── evaluator/          # Evaluator component templates
│   └── volcano/            # Volcano-specific templates
│       ├── oc-rbac.yaml    # OpenShift RBAC configuration
│       ├── webhook-patch.yaml  # Webhook namespace scoping
│       └── clusterrole-patch.yaml  # ClusterRole patches
└── README.md              # This file
```

## Dependencies

This chart depends on the following Helm charts:

- **PostgreSQL** (Bitnami): 16.0.0
- **MLflow** (Bitnami): 1.0.6
- **OpenTelemetry Collector**: 0.93.3
- **Argo Workflows**: 0.40.11
- **Milvus**: 4.1.11
- **Volcano**: 1.9.0

## Version Information

- **Chart Version**: 1.0.0
- **App Version**: 25.06
- **Helm Version**: 3.x required

## Contributing

When contributing to this chart:

1. Update version in `Chart.yaml`
2. Update `values.yaml` with new configuration options
3. Add templates in appropriate directories
4. Update this README with new features
5. Test on OpenShift cluster before submitting

## License

See LICENSE file in the repository root.

## Support

For issues and questions:
- Check troubleshooting section
- Review OpenShift documentation
- Contact NVIDIA NeMo team

---

**Last Updated**: November 2025
**OpenShift Version**: 4.x
**Helm Version**: 3.x
