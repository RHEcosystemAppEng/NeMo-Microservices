# Security Context Constraints (SCC) References

This document lists all locations where Security Context Constraints (SCCs) are defined, used, or granted in the NeMo Microservices codebase.

**Repository**: [RHEcosystemAppEng/NeMo-Microservices](https://github.com/RHEcosystemAppEng/NeMo-Microservices) (branch: `add-llamastack-deployment`)

## RBAC Files (SCC Grants via Role/RoleBinding)

### Jupyter Notebook
- **GitHub Link**: [deploy/nemo-infra/templates/jupyter/ocp-rbac.yaml](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/templates/jupyter/ocp-rbac.yaml)
- **SCC**: `anyuid`
- **Service Account**: `jupyter`
- **Method**: RBAC Role/RoleBinding
- **Key Lines**: 
  - [Line 14](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/templates/jupyter/ocp-rbac.yaml#L14): `resourceNames: ['anyuid']`

### Milvus (Evaluator Component)
- **GitHub Link**: [deploy/nemo-infra/templates/evaluator/milvus-oc-rbac.yaml](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/templates/evaluator/milvus-oc-rbac.yaml)
- **SCC**: `anyuid`
- **Service Account**: `milvus`
- **Method**: RBAC Role/RoleBinding
- **Key Lines**: 
  - [Line 25](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/templates/evaluator/milvus-oc-rbac.yaml#L25): `resourceNames: ['anyuid']`

### Volcano Scheduler
- **GitHub Link**: [deploy/nemo-infra/templates/volcano/oc-rbac.yaml](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/templates/volcano/oc-rbac.yaml)
- **SCC**: `privileged`
- **Service Account**: `{RELEASE_NAME}-scheduler`
- **Method**: 
  - Job hook using `oc adm policy add-scc-to-user` command
  - Alternative RBAC Role/RoleBinding (backup method)
- **Key Lines**: 
  - [Line 3](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/templates/volcano/oc-rbac.yaml#L3): Comment with command reference
  - [Line 32](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/templates/volcano/oc-rbac.yaml#L32): `oc adm policy add-scc-to-user privileged` command
  - [Line 57](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/templates/volcano/oc-rbac.yaml#L57): `resourceNames: ['privileged']`

## Deployment Annotations

### LlamaStack
- **GitHub Link**: [deploy/nemo-instances/templates/llamastack/deployment.yaml](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-instances/templates/llamastack/deployment.yaml)
- **SCC**: `nonroot`
- **Annotation**: `openshift.io/scc: "nonroot"`
- **Key Lines**: 
  - [Line 10](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-instances/templates/llamastack/deployment.yaml#L10): Deployment annotation
  - [Line 32](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-instances/templates/llamastack/deployment.yaml#L32): Pod template annotation

### Jupyter Notebook
- **GitHub Link**: [deploy/nemo-infra/templates/jupyter/deployment.yaml](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/templates/jupyter/deployment.yaml)
- **SCC**: `anyuid`
- **Annotation**: `openshift.io/scc: anyuid`
- **Key Lines**: 
  - [Line 20](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/templates/jupyter/deployment.yaml#L20): `openshift.io/scc: anyuid`

### NIMService (via Values)
- **GitHub Link**: [deploy/nemo-infra/values.yaml](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/values.yaml#L323)
- **SCC**: `anyuid`
- **Annotation**: `openshift.io/required-scc: anyuid`
- **Context**: NIMService pod metadata annotations
- **Key Lines**: 
  - [Line 323](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/values.yaml#L323): `openshift.io/required-scc: anyuid`

## Documentation References

### Infrastructure README
- **GitHub Link**: [deploy/nemo-infra/README.md](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/README.md#L269)
- **Content**: Command reference for granting privileged SCC to Volcano scheduler
- **Command**: `oc adm policy add-scc-to-user privileged system:serviceaccount:<namespace>:nemo-infra-scheduler`
- **Key Lines**: 
  - [Line 269](https://github.com/RHEcosystemAppEng/NeMo-Microservices/blob/add-llamastack-deployment/deploy/nemo-infra/README.md#L269): Command reference

## Summary by SCC Type

### `nonroot` SCC
- LlamaStack (deployment annotation)

### `anyuid` SCC
- Jupyter Notebook (RBAC + deployment annotation)
- Milvus (RBAC)
- NIMService (via values.yaml configuration)

### `privileged` SCC
- Volcano Scheduler (Job hook + RBAC backup)

## Notes

1. **Annotation Types**:
   - `openshift.io/scc`: Direct SCC assignment (used in deployments)
   - `openshift.io/required-scc`: Required SCC hint (used in controllers)

2. **Grant Methods**:
   - **RBAC**: Role/RoleBinding (preferred, declarative)
   - **Command**: `oc adm policy add-scc-to-user` (used for Volcano, requires cluster-admin)
   - **Annotation**: Direct annotation on pod/deployment (OpenShift auto-grants)

3. **SCC Configuration**:
   - SCCs are configured via RBAC (Role/RoleBinding), deployment annotations, or values.yaml
   - The NIMService SCC is configured in values.yaml and applied to NIMService pods

