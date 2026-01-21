# NeMo Customizer Service Test

A simple notebook to test and verify the NeMo Customizer service is working correctly.

## Overview

This notebook performs basic connectivity and functionality tests for the NeMo Customizer service:

1. **Health Check**: Verifies the customizer service is running and healthy
2. **API Information**: Retrieves API version and capabilities
3. **Jobs Listing**: Lists existing customization jobs
4. **Dependencies**: Tests connectivity to required services (DataStore, Entity Store)

## Prerequisites

- ✅ NeMo Customizer service deployed and running
- ✅ NeMo Data Store service deployed and running
- ✅ NeMo Entity Store service deployed and running
- ✅ Access to the cluster namespace (running from Workbench/Notebook within cluster)

## Quick Start

### 1. Configure Environment

```bash
cd NeMo-Microservices/demos/customizer-test
cp env.donotcommit.example env.donotcommit
```

Edit `env.donotcommit` and set:
```bash
NMS_NAMESPACE=anemo-rhoai  # Your namespace
```

### 2. Run in Workbench/Notebook (Cluster Mode)

```bash
# Get Jupyter pod name
JUPYTER_POD=$(oc get pods -n $NAMESPACE -l app=jupyter-notebook -o jsonpath='{.items[0].metadata.name}')

# Copy files to pod
oc cp customizer-test.ipynb $JUPYTER_POD:/work -n $NAMESPACE
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
oc get pods -n anemo-rhoai | grep customizer | grep -v postgresql | grep -v mlflow

# Check DataStore
oc get pods -n anemo-rhoai | grep datastore | grep -v postgresql

# Check Entity Store
oc get pods -n anemo-rhoai | grep entitystore | grep -v postgresql
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

### Service Not Responding

If the customizer service is not responding:

```bash
# Check pod status
oc get pods -n anemo-rhoai | grep nemocustomizer-sample

# Check service
oc get svc nemocustomizer-sample -n anemo-rhoai

# Check logs
oc logs -n anemo-rhoai -l app.kubernetes.io/name=nemocustomizer-sample --tail=50
```

### Connection Errors

If you see connection errors:
- Verify you're running the notebook from within the cluster (Workbench/Notebook)
- Check the namespace matches your deployment: `oc get nemocustomizer -n anemo-rhoai`
- Verify service names match: `oc get svc -n anemo-rhoai | grep customizer`

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
