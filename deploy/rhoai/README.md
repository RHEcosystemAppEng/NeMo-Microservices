# RHOAI LlamaStack (copilot-llama-stack)

Deploy LlamaStack on Red Hat OpenShift AI (RHOAI) so demos (e.g. RAG) can use the RHOAI-hosted inference endpoint via a unified LlamaStack API.

**Version note:** RHOAI 3.2 uses **Llama Stack server 0.3.5+rhai0**. Use a **0.3.x-compatible** client (e.g. Python `llama-stack-client>=0.3,<0.4`); newer clients (0.5.x) will get a 426 version mismatch from the server.

If the notebook gets **401 Unauthorized** when calling LlamaStack, the server may require client authentication. Set `LLAMASTACK_API_KEY` in `env.donotcommit` to the same predictor service account token used in the `copilot-llama-stack-api-key` secret (e.g. `oc create token redhataillama-31-8b-instruct-sa -n $NAMESPACE --duration=8760h`), then re-run the notebook config cell.

## 1. Enable the LlamaStack operator on RHOAI

The LlamaStack operator must be **enabled** in the cluster by setting its component to **Managed** on the **DataScienceCluster** (DSC) custom resource. This is a one-time cluster-level change.

**Do the following only if `llamastackoperator` is not already set to Managed.** On many OpenShift AI 3.x installs it is enabled by default.

**Check current state:**

```bash
oc get datasciencecluster -A
oc get datasciencecluster default-dsc -o jsonpath='{.spec.components.llamastackoperator.managementState}'
# If this prints "Managed", skip to step 2. If it prints nothing or "Removed"/"Unmanaged", continue below.
```

If it is not already **Managed**, use one of the options below.

### Option A: Web Console

1. Open **Operators** → **Installed Operators** → **Red Hat OpenShift AI** (or navigate to your DataScienceCluster).
2. Open the **DataScienceCluster** instance (e.g. `default-dsc`) → **YAML** tab.
3. Under `spec.components`, add or set:

   ```yaml
   spec:
     components:
       llamastackoperator:
         managementState: Managed
   ```

4. Save.

### Option B: CLI

```bash
# See your DSC name (often default-dsc)
oc get datasciencecluster

# Enable LlamaStack operator (replace <name> with your DSC name, e.g. default-dsc)
oc patch datasciencecluster <name> --type=merge -p '{"spec":{"components":{"llamastackoperator":{"managementState":"Managed"}}}}'
```

**Verify the operator is running:**

```bash
oc get pods -n redhat-ods-applications -l app.kubernetes.io/name=llama-stack-operator
```

## 2. Create the API key secret

LlamaStack needs a token to call your KServe InferenceService. Use the predictor's service account token:

```bash
export NAMESPACE=your-namespace   # set to your OpenShift project/namespace

# Create token (use the SA for your InferenceService, e.g. redhataillama-31-8b-instruct-sa)
oc create token redhataillama-31-8b-instruct-sa -n $NAMESPACE --duration=8760h
# Copy the printed token, then:

oc create secret generic copilot-llama-stack-api-key -n $NAMESPACE --from-literal=api_key='YOUR_TOKEN'
```

See [llamastack-api-key-secret.yaml](llamastack-api-key-secret.yaml) for details.

## 3. Apply LlamaStack distribution

```bash
oc apply -f deploy/rhoai/copilot-llama-stack.yaml -n $NAMESPACE
```

Replace `your-namespace` in the YAML files with your namespace, or pass `-n $NAMESPACE` when applying.

## 4. Verify

```bash
oc get llamastackdistribution -n $NAMESPACE
oc get pods -n $NAMESPACE | grep llama
oc get svc -n $NAMESPACE | grep copilot-llama-stack
```

Demos (e.g. [RAG with RHOAI LlamaStack](../../demos/rag/README.md#rhoai-llamastack-variant)) can then set `LLAMASTACK_URL` to `http://copilot-llama-stack-service.<namespace>.svc.cluster.local:8321` and use the RHOAI model id (e.g. `vllm-inference/redhataillama-31-8b-instruct`).
