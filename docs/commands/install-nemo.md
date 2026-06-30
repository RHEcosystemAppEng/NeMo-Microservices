---
description: Adaptive NeMo Microservices installation on OpenShift with cluster-aware conflict resolution
---

# Install NeMo Microservices

You are performing an adaptive installation of NeMo Microservices on an OpenShift cluster.
Unlike a static bash script, you inspect the cluster state first, identify conflicts and
incompatibilities, and adapt the installation steps accordingly.

## Hard rules

- NEVER print, echo, or display API keys, tokens, or secret values. Use `${VAR:0:10}...` for masked confirmation only.
- Always use `oc`, not `kubectl`.
- Always confirm with the user before executing destructive actions (deleting resources, uninstalling Helm releases, re-annotating SCCs).
- Always confirm the target cluster and namespace before proceeding with installation.
- Read all configuration from the `.env` file in the repository root. Never ask the user to type secrets.
- Do not modify `values.yaml` files beyond the namespace substitutions in Phases 5 and 6 unless the user explicitly approves.

---

## Phase 1: Pre-flight

Verify all prerequisites. If any check fails, stop and report what is missing.

1. **CLI tools**: Confirm `oc`, `helm`, and `jq` are installed and on PATH.
2. **Establish repo root**: Record the absolute path to the repository root as `REPO_ROOT`.
   All subsequent `.env` sourcing must use `source "$REPO_ROOT/.env"` to avoid breakage
   when the working directory changes (e.g. after `cd deploy/nemo-infra/`).
3. **OpenShift login**: Run `oc whoami` and `oc whoami --show-server`. Report the logged-in user and API server.
4. **`.env` file**: Source the `.env` at the repository root. Validate that all four required variables are set and non-empty:
   - `NAMESPACE`
   - `NGC_API_KEY`
   - `NVIDIA_API_KEY`
   - `HF_TOKEN`
5. **Chart directories**: Confirm `deploy/nemo-infra/values.yaml` and `deploy/nemo-instances/values.yaml` exist.
6. **User confirmation**: Display the target cluster URL and namespace. Ask the user to confirm before continuing.

---

## Phase 2: Cluster state discovery

Collect ALL of the following before deciding on any action. Do not start remediation yet.

### 2.1 Existing Helm releases

```bash
helm list -n $NAMESPACE --deployed --failed --pending --uninstalling
```

Record which nemo-related releases exist and their status (deployed / failed / pending-install).
Note: Do NOT use `-a` or `--all` — these flags are unavailable in some Helm 3 versions.

### 2.2 CRD ownership

Check whether Argo Workflows and Volcano CRDs already exist on the cluster, and who manages them:

```bash
oc get crd workflows.argoproj.io -o jsonpath='{.metadata.managedFields[*].manager}' 2>/dev/null
oc get crd jobs.batch.volcano.sh  -o jsonpath='{.metadata.managedFields[*].manager}' 2>/dev/null
```

**Why this matters:** If the CRDs exist and are managed by a field manager other than `helm`
(e.g. `platform.opendatahub.io` from OpenDataHub), then `helm install nemo-infra` will fail
with an SSA ownership conflict unless `--skip-crds` is passed. If the CRDs do not exist at all,
`--skip-crds` must NOT be used or the install will fail with missing CRDs.

### 2.3 Orphaned cluster-scoped resources

Search for resources left behind by previous failed installs:

```bash
oc get clusterroles -o json | jq -r '.items[] | select(.metadata.name | test("nemo-infra|volcano|nim-operator")) | .metadata.name'
oc get clusterrolebindings -o json | jq -r '.items[] | select(.metadata.name | test("nemo-infra|volcano|nim-operator")) | .metadata.name'
oc get validatingwebhookconfigurations -o json | jq -r '.items[] | select(.metadata.name | test("nemo-infra|volcano|nim-operator")) | .metadata.name'
oc get mutatingwebhookconfigurations -o json | jq -r '.items[] | select(.metadata.name | test("nemo-infra|volcano|nim-operator")) | .metadata.name'
oc get scc -o json | jq -r '.items[] | select(.metadata.name | test("nemo")) | .metadata.name'
```

**Why this matters:** Orphaned cluster-scoped resources carry a `before-first-apply` field
manager. Helm SSA cannot take ownership from this manager — patching managedFields does not
work. The only reliable fix is to delete and let Helm recreate them cleanly.
SCCs like `nemo-customizer-scc` can also be left behind and must be included in this scan.

### 2.4 SCC state

```bash
oc get scc nemo-customizer-scc -o jsonpath='{.metadata.annotations.meta\.helm\.sh/release-name}' 2>/dev/null
```

**Why this matters:** `nemo-customizer-scc` is defined in both the nemo-infra and nemo-instances
charts. If nemo-infra creates it first, its `meta.helm.sh/release-name` annotation points to
`nemo-infra`. When nemo-instances tries to install, Helm sees the SCC owned by a different
release and fails. The annotation must be updated to `nemo-instances` before that install.

### 2.5 Storage classes

```bash
oc get storageclasses -o custom-columns=NAME:.metadata.name,PROVISIONER:.provisioner,DEFAULT:.metadata.annotations.storageclass\\.kubernetes\\.io/is-default-class
```

Read the `storageClass` values from both `deploy/nemo-infra/values.yaml` and
`deploy/nemo-instances/values.yaml`. Check whether each referenced storage class actually
exists on the cluster.

### 2.6 GPU availability

```bash
oc get nodes -o json | jq -r '.items[] | select(.status.allocatable["nvidia.com/gpu"] != null and .status.allocatable["nvidia.com/gpu"] != "0") | "\(.metadata.name)\t\(.status.allocatable["nvidia.com/gpu"]) GPUs\t\([.spec.taints[]?.key] | join(","))"'
```

Report the total allocatable GPUs. NeMo requires at minimum 1 GPU for the chat model NIM.
If zero GPUs are allocatable, warn the user — the install will succeed but NIM pods will
remain Pending.

### 2.7 Namespace state

```bash
oc get namespace $NAMESPACE 2>/dev/null
oc get pods -n $NAMESPACE --no-headers 2>/dev/null | wc -l
```

### Present findings

Summarize ALL findings in a table:

| Check | Status | Detail | Action needed |
|-------|--------|--------|---------------|
| ...   | ...    | ...    | ...           |

Present the full remediation plan. Wait for the user to confirm before moving to Phase 3.

---

## Phase 3: Conflict resolution

Execute ONLY the remediations identified in Phase 2. Skip any sub-step that is not needed.

### 3.1 Failed Helm releases

If any nemo-related releases are in `failed` state, uninstall them:

```bash
helm uninstall <release-name> -n $NAMESPACE
sleep 5
```

### 3.2 Orphaned cluster-scoped resources

If Phase 2.3 found orphaned resources, delete them. List each resource name before deleting and
confirm with the user:

```bash
oc delete clusterrole <name> --ignore-not-found
oc delete clusterrolebinding <name> --ignore-not-found
oc delete validatingwebhookconfiguration <name> --ignore-not-found
oc delete mutatingwebhookconfiguration <name> --ignore-not-found
oc delete scc <name> --ignore-not-found
```

**Important:** After any `helm uninstall` of a failed release (Phase 3.1), re-run the
Phase 2.3 orphaned resource scan. Uninstalling a failed release often leaves behind *new*
orphaned cluster-scoped resources (e.g. from pre-install hooks) that must also be deleted
before retrying the install.

### 3.3 Storage class mismatch

If any referenced storage class does not exist on the cluster, display the available storage
classes and ask the user which one to use. Do NOT silently change values.yaml.

---

## Phase 4: Namespace and secrets

1. Create the namespace if it does not exist, or switch to it if it does:

```bash
oc get namespace "$NAMESPACE" 2>/dev/null && oc project "$NAMESPACE" || oc new-project "$NAMESPACE"
```

2. Recreate the required secrets (delete-then-create to ensure clean state):

```bash
oc delete secret nvcrimagepullsecret ngc-api nvidia-api hf-secret \
    -n "$NAMESPACE" --ignore-not-found=true

oc create secret docker-registry nvcrimagepullsecret \
    --docker-server=nvcr.io \
    --docker-username='$oauthtoken' \
    --docker-password="$NGC_API_KEY" \
    -n "$NAMESPACE"

oc create secret generic ngc-api \
    --from-literal=NGC_API_KEY="$NGC_API_KEY" \
    -n "$NAMESPACE"

oc create secret generic nvidia-api \
    --from-literal=NVIDIA_API_KEY="$NVIDIA_API_KEY" \
    -n "$NAMESPACE"

oc create secret generic hf-secret \
    --from-literal=HF_TOKEN="$HF_TOKEN" \
    -n "$NAMESPACE"
```

---

## Phase 5: Install nemo-infra

1. `cd` to `deploy/nemo-infra/`.

2. Patch the namespace in values.yaml:

```bash
sed -i.bak "/^namespace:/,/^  name:/ s/^  name: .*/  name: $NAMESPACE/" values.yaml && rm -f values.yaml.bak
```

**Why this matters:** The default `namespace.name` is `your-namespace`. If not patched,
pre-install hooks will fail with `namespaces "your-namespace" not found` and leave a
failed release that must be uninstalled before retrying.

3. Clean stale artifacts and update Helm dependencies:

```bash
rm -rf charts/*.tgz Chart.lock 2>/dev/null || true
helm dependency update
```

4. If Phase 2.3 found orphaned cluster-scoped resources, run the cleanup now (Phase 3.2)
   if it was not already done.

5. Build the `helm install` command:

```bash
helm install nemo-infra . -n "$NAMESPACE" --create-namespace -f values.yaml
```

Add `--skip-crds` ONLY if Phase 2.2 confirmed that CRDs exist and are managed by another
operator. If CRDs do not exist, do NOT skip them.

6. Run the install command.

7. **If the install fails**, the release stays in `failed` state and blocks retries with
   `cannot reuse a name that is still in use`. Recovery flow:

```bash
helm uninstall nemo-infra -n "$NAMESPACE"
```

Then re-run the Phase 2.3 orphaned resource scan — the failed install may have created
new orphaned ClusterRoles, ClusterRoleBindings, or webhooks from pre-install hooks.
Delete any new orphans (Phase 3.2), fix the root cause, and retry from step 5.

8. Wait for pods:

```bash
oc wait --for=condition=ready pod -l app.kubernetes.io/instance=nemo-infra \
    -n "$NAMESPACE" --timeout=300s
```

9. If the wait times out, diagnose:

```bash
oc get pods -n "$NAMESPACE" -l app.kubernetes.io/instance=nemo-infra -o wide
oc get events -n "$NAMESPACE" --sort-by='.lastTimestamp' --field-selector reason!=Pulled | tail -20
```

For any pod not in Running state, run `oc describe pod <name> -n $NAMESPACE` and
`oc logs <name> -n $NAMESPACE --tail=50`. Report root causes and ask the user how to proceed.

---

## Phase 6: Optional component selection

Before installing nemo-instances, ask the user which optional components to deploy.

The core services (customizer, datastore, entitystore, evaluator, guardrail, chat model NIM)
are always deployed. The following are optional:

| Component | Default | GPU cost | Description |
|-----------|---------|----------|-------------|
| Gateway | disabled | 0 | NeMo Gateway — unified API endpoint for all NeMo services |
| LlamaStack | disabled | 0 | LlamaStack integration layer |
| Embedding Model | disabled | 1 GPU | NIM embedding model (`nvidia/nv-embedqa-e5-v5`) for RAG workflows |
| Retriever Model | disabled | 1 GPU | NIM retriever model (`nvidia/nv-rerankqa-mistral-4b-v3`) for RAG workflows |

Present the table above along with the number of available GPUs (from Phase 2.6) and ask
the user to select which optional components to enable. Use a multi-select question.

Record the selections — they will be passed as `--set` flags in Phase 7 step 5.

---

## Phase 7: Install nemo-instances

1. `cd` to `deploy/nemo-instances/`.

2. Patch the namespace in values.yaml:

```bash
sed -i.bak "/^namespace:/,/^  name:/ s/^  name: .*/  name: $NAMESPACE/" values.yaml && rm -f values.yaml.bak
```

3. Clean stale artifacts and update Helm dependencies:

```bash
rm -rf charts/*.tgz Chart.lock 2>/dev/null || true
helm dependency update
```

4. **SCC ownership transfer** — check if `nemo-customizer-scc` exists. If it does and is
   owned by `nemo-infra` (or was just created by Phase 5), re-annotate it for nemo-instances.
   If it does not exist, skip this step — nemo-instances will create it directly.

```bash
if oc get scc nemo-customizer-scc &>/dev/null; then
  oc annotate scc nemo-customizer-scc \
      meta.helm.sh/release-name=nemo-instances \
      meta.helm.sh/release-namespace="$NAMESPACE" \
      --overwrite
fi
```

5. Install nemo-instances. Build the `--set` flags based on the user's selections from Phase 6:

   - Gateway: `--set gateway.enabled=true` or `--set gateway.enabled=false`
   - LlamaStack: `--set llamastack.enabled=true` or `--set llamastack.enabled=false`
   - Embedding Model: `--set deployEmbeddingModel=true` or omit (defaults to false)
   - Retriever Model: `--set deployRetrieverModel=true` or omit (defaults to false)

```bash
helm install nemo-instances . -n "$NAMESPACE" \
    -f values.yaml \
    --set gateway.enabled=<true|false> \
    --set llamastack.enabled=<true|false> \
    --set deployEmbeddingModel=<true|false> \
    --set deployRetrieverModel=<true|false>
```

6. Wait for services to start (models take time to download and load):

```bash
sleep 30
oc get pods -n "$NAMESPACE" | grep -E "nemo(datastore|entitystore|customizer|evaluator|guardrail|gateway)|llama3-1b|embedqa"
```

7. If any pods are failing, diagnose with `oc describe pod` and `oc logs --tail=50`.
   Common issues to check:
   - **ImagePullBackOff**: NGC credentials invalid or image tag wrong
   - **Pending**: No GPU nodes available, or PVC cannot be provisioned (wrong storage class)
   - **CrashLoopBackOff**: Check logs for misconfigured environment variables or missing secrets
   - **Init container failures**: Check init container logs separately with `oc logs <pod> -c <init-container-name>`

---

## Phase 8: Verification

Run a comprehensive check and present the results.

1. **Helm releases:**
```bash
helm list -n "$NAMESPACE"
```

2. **Custom resources:**
```bash
oc get nemodatastore,nemoentitystore,nemocustomizer,nemoevaluator,nemoguardrail,nimcache,nimpipeline -n "$NAMESPACE"
```

3. **Services:**
```bash
oc get svc -n "$NAMESPACE" | grep -E "nemo|llama|embedqa"
```

4. **Pod health:**
```bash
oc get pods -n "$NAMESPACE"
```

5. **Unhealthy pods** (anything not Running or Completed):
```bash
oc get pods -n "$NAMESPACE" --no-headers | grep -v -E "Running|Completed"
```

For each unhealthy pod, inspect logs and events and report the root cause.

Present a final summary table:

| Component | Status | Notes |
|-----------|--------|-------|
| nemo-infra (Helm) | ... | ... |
| nemo-instances (Helm) | ... | ... |
| datastore | ... | ... |
| entitystore | ... | ... |
| customizer | ... | ... |
| evaluator | ... | ... |
| guardrails | ... | ... |
| chat model NIM | ... | ... |
| gateway | ... | ... | *(only if enabled in Phase 6)* |
| llamastack | ... | ... | *(only if enabled in Phase 6)* |
| embedding model NIM | ... | ... | *(only if enabled in Phase 6)* |
| retriever model NIM | ... | ... | *(only if enabled in Phase 6)* |

Only include rows for optional components that were enabled in Phase 6.

If everything is healthy, display the service URLs (cluster-internal).

Core services:
- Chat Model: `http://meta-llama3-1b-instruct.$NAMESPACE.svc.cluster.local:8000`
- Data Store: `http://nemodatastore-sample.$NAMESPACE.svc.cluster.local:8000`
- Entity Store: `http://nemoentitystore-sample.$NAMESPACE.svc.cluster.local:8000`
- Customizer: `http://nemocustomizer-sample.$NAMESPACE.svc.cluster.local:8000`
- Evaluator: `http://nemoevaluator-sample.$NAMESPACE.svc.cluster.local:8000`
- Guardrails: `http://nemoguardrails-sample.$NAMESPACE.svc.cluster.local:8000`

Optional services (only if enabled):
- Gateway: `http://nemo-gateway.$NAMESPACE.svc.cluster.local`
