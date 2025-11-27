# Volcano Scheduler SCC Configuration

**Repository**: [RHEcosystemAppEng/NeMo-Microservices](https://github.com/RHEcosystemAppEng/NeMo-Microservices) (branch: `add-llamastack-deployment`)

## Configuration File

**File**: [deploy/nemo-infra/templates/volcano/oc-rbac.yaml](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/templates/volcano/oc-rbac.yaml)

## SCC Details

- **SCC Type**: `privileged`
- **Service Account**: `{RELEASE_NAME}-scheduler`

## Implementation

### Job Hook
- [Line 32](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/templates/volcano/oc-rbac.yaml#L32): Executes `oc adm policy add-scc-to-user privileged system:serviceaccount:{{ .Values.namespace.name }}:${RELEASE_NAME}-scheduler`
