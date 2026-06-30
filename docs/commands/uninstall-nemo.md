---
description: Uninstall NeMo Microservices from OpenShift, including orphaned cluster-scoped resources
---

# Uninstall NeMo Microservices

You are performing a complete uninstall of NeMo Microservices from an OpenShift cluster.
This removes Helm releases, custom resources, namespace-scoped resources, orphaned
cluster-scoped resources, and optionally the namespace itself.

## Hard rules

- NEVER print, echo, or display API keys, tokens, or secret values.
- Always use `oc`, not `kubectl`.
- Always confirm the target cluster and namespace before proceeding.
- Always confirm before deleting the namespace (Phase 5) — the user may want to keep it.
- Read `NAMESPACE` from the `.env` file in the repository root.

---

## Phase 1: Pre-flight

1. **CLI tools**: Confirm `oc`, `helm`, and `jq` are installed and on PATH.
2. **Establish repo root**: Record the absolute path to the repository root as `REPO_ROOT`.
   All subsequent `.env` sourcing must use `source "$REPO_ROOT/.env"`.
3. **OpenShift login**: Run `oc whoami` and `oc whoami --show-server`. Report the logged-in
   user and API server.
4. **`.env` file**: Source the `.env` at the repository root. Validate that `NAMESPACE` is
   set and non-empty.
5. **Namespace exists**: Confirm the namespace exists on the cluster. If it does not exist,
   skip to Phase 4 (cluster-scoped cleanup only) — orphaned resources may still exist even
   if the namespace is gone.
6. **User confirmation**: Display the target cluster URL and namespace. Show current Helm
   releases and pod count:

```bash
helm list -n $NAMESPACE --deployed --failed --pending --uninstalling
oc get pods -n $NAMESPACE --no-headers 2>/dev/null | wc -l
```

Ask the user to confirm before continuing.

---

## Phase 2: Helm release uninstall

Uninstall Helm releases in reverse install order (nemo-instances first, then nemo-infra).

1. **Uninstall nemo-instances** (if it exists):

```bash
helm uninstall nemo-instances -n $NAMESPACE --timeout 60s
```

2. **If nemo-instances hangs** (pre-delete hooks or finalizers can block for minutes),
   retry with `--no-hooks`:

```bash
helm uninstall nemo-instances -n $NAMESPACE --no-hooks
```

If it is still stuck in `uninstalling` state after this, proceed to Phase 3 — the
resource-level cleanup will force-remove what Helm could not.

3. **Uninstall nemo-infra** (if it exists):

```bash
helm uninstall nemo-infra -n $NAMESPACE --no-hooks
```

Use `--no-hooks` by default for nemo-infra — its hooks are not needed during teardown
and avoiding them prevents the same hang.

4. Wait briefly for Helm-managed resources to begin terminating:

```bash
sleep 5
```

---

## Phase 3: Namespace-scoped resource cleanup

Clean up resources that Helm may have left behind (finalizers, stuck CRs, etc.).
Skip this phase if the namespace does not exist.

### 3.1 Webhooks that block deletion

Delete webhooks first — they can block resource deletion:

```bash
oc delete validatingwebhookconfiguration k8s-nim-operator-validating-webhook-configuration --ignore-not-found
oc delete mutatingwebhookconfiguration k8s-nim-operator-mutating-webhook-configuration --ignore-not-found
```

### 3.2 Custom resources

Delete all NeMo custom resources. Use `--wait=false` to avoid blocking on finalizers:

```bash
for cr in nemotrainingjobs nimservice nimcache nimpipeline nemodatastore nemocustomizer nemoentitystore nemoguardrails nemoevaluator; do
  oc delete $cr --all -n $NAMESPACE --wait=false 2>/dev/null
done
```

### 3.3 Remove finalizers from stuck custom resources

If any custom resources are stuck in `Terminating`, remove their finalizers:

```bash
for crd in nemotrainingjobs nimservice nimcache nimpipeline nemodatastore nemocustomizer nemoentitystore nemoguardrails nemoevaluator; do
  for resource in $(oc get $crd -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
    oc patch $crd $resource -n $NAMESPACE -p '{"metadata":{"finalizers":null}}' --type=merge 2>/dev/null || true
  done
done
```

### 3.4 Workloads

```bash
oc delete deployment --all -n $NAMESPACE --wait=false
oc delete statefulsets --all -n $NAMESPACE --wait=false
oc delete job --all -n $NAMESPACE --wait=false
```

### 3.5 Pods

Force-delete all remaining pods to release PVC locks:

```bash
oc delete pod --all -n $NAMESPACE --force --grace-period=0
sleep 5
```

### 3.6 PVCs

Delete PVCs now that pods are gone. Remove finalizers from any that are stuck:

```bash
oc delete pvc --all -n $NAMESPACE --wait=false
sleep 3
for pvc in $(oc get pvc -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
  oc patch pvc $pvc -n $NAMESPACE -p '{"metadata":{"finalizers":null}}' --type=merge 2>/dev/null || true
done
```

### 3.7 Remaining resources

```bash
oc delete service --all -n $NAMESPACE
oc delete configmap --all -n $NAMESPACE
oc delete secret --all -n $NAMESPACE
```

### 3.8 Verify namespace is clean

```bash
oc get all -n $NAMESPACE 2>/dev/null
```

Report any resources still remaining.

---

## Phase 4: Cluster-scoped resource cleanup

These resources live outside the namespace and are left behind by Helm uninstalls.
They MUST be cleaned up or future installs will fail with SSA ownership conflicts.

**Important:** Resources whose names match `nim-operator-certified.v*` may be managed by the
cluster-wide OLM NIM operator subscription, not by our Helm install. Before deleting them,
check if a NIM operator CSV exists on the cluster:

```bash
oc get csv --all-namespaces 2>/dev/null | grep -c nim-operator-certified
```

If the count is non-zero, the OLM operator is installed cluster-wide and those resources
will be recreated immediately after deletion. **Skip them** — they are not our orphans.

### 4.1 ClusterRoles and ClusterRoleBindings

Scan and delete:

```bash
echo "=== ClusterRoles ==="
oc get clusterroles -o json | jq -r '.items[] | select(.metadata.name | test("nemo-infra|volcano|nim-operator")) | .metadata.name'

echo "=== ClusterRoleBindings ==="
oc get clusterrolebindings -o json | jq -r '.items[] | select(.metadata.name | test("nemo-infra|volcano|nim-operator")) | .metadata.name'
```

Delete each one found (excluding OLM-managed `nim-operator-certified.v*` resources — see above):

```bash
oc delete clusterrole <name> --ignore-not-found
oc delete clusterrolebinding <name> --ignore-not-found
```

### 4.2 Webhook configurations

```bash
echo "=== ValidatingWebhooks ==="
oc get validatingwebhookconfigurations -o json | jq -r '.items[] | select(.metadata.name | test("nemo-infra|volcano|nim-operator")) | .metadata.name'

echo "=== MutatingWebhooks ==="
oc get mutatingwebhookconfigurations -o json | jq -r '.items[] | select(.metadata.name | test("nemo-infra|volcano|nim-operator")) | .metadata.name'
```

Delete each one found:

```bash
oc delete validatingwebhookconfiguration <name> --ignore-not-found
oc delete mutatingwebhookconfiguration <name> --ignore-not-found
```

### 4.3 SecurityContextConstraints

```bash
oc get scc -o json | jq -r '.items[] | select(.metadata.name | test("nemo")) | .metadata.name'
```

Delete each one found:

```bash
oc delete scc <name> --ignore-not-found
```

### 4.4 Verify no orphans remain

Re-run all four scans. If anything still shows up that is not OLM-managed, delete it and
scan again.

**Note:** If the nemo-instances Helm release was stuck in `uninstalling` state during
Phase 2, it may still be finalizing in the background and recreating cluster-scoped
resources as it processes. Re-run the scan 2-3 times with a short pause between each
until the results stabilize. Only resources that persist after the Helm release is fully
gone are true orphans.

---

## Phase 5: Namespace deletion (optional)

Ask the user whether to delete the namespace.

If yes:

```bash
oc delete project $NAMESPACE --wait=false
sleep 5
```

If the namespace gets stuck in `Terminating`:

```bash
if oc get namespace $NAMESPACE 2>/dev/null; then
  oc patch namespace $NAMESPACE -p '{"metadata":{"finalizers":null}}' --type=merge 2>/dev/null || true
fi
```

---

## Phase 6: Final verification

Present a summary table:

| Area | Status | Detail |
|------|--------|--------|
| Helm releases | ... | nemo-infra, nemo-instances |
| Custom resources | ... | All NeMo CRs deleted |
| Pods / workloads | ... | None remaining |
| PVCs | ... | All deleted |
| ClusterRoles | ... | Orphans removed |
| ClusterRoleBindings | ... | Orphans removed |
| Webhooks | ... | Orphans removed |
| SCCs | ... | Orphans removed |
| Namespace | ... | Deleted / Kept |

Report the final state. If anything remains, list it explicitly.
