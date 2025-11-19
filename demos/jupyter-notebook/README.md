# nemo-data-flywheel-tutorials

Tutorials for NeMo Microservices (MS) Data Flywheel, including examples for using the NeMo MS Data Store, Entity Store, Customizer, Evaluator, Guardrails, and NVIDIA NIMs.

## 1. Steps to run the notebook

1. Update Notebook Config

   The `config.py` file automatically detects whether you're running from within the cluster or locally:
   
   - **Default (cluster mode):** If `RUN_LOCALLY` environment variable is not set, the notebook uses cluster-internal service URLs
   - **Localhost mode:** Set `RUN_LOCALLY=true` environment variable to use localhost URLs (requires port-forwards)
   
   For cluster execution, you may need to update the namespace in `config.py`:
   
   ```python
   NMS_NAMESPACE = "<your-namespace>"  # e.g., "arhkp-nemo-helm"
   HF_TOKEN = "<your-huggingface-token>"
   ```
   
   The config will automatically use cluster URLs like:
   - `http://nemodatastore-sample.<namespace>.svc.cluster.local:8000`
   - `http://nemoentitystore-sample.<namespace>.svc.cluster.local:8000`
   - etc.

**NOTE:** if you have are already gone through steps in the QuickStart guide, you can skip steps 2-4

2. **Install the NeMo Dependencies Ansible playbook** that deploys the Jupyter server with all required NeMo dependencies enabled in `values.yaml`.

``` yaml
install:
  customizer: yes
  datastore: yes
  entity_store: yes
  evaluator: yes
  jupyter: yes
```

3. **Deploy the NeMo Training Operator**

```bash
kubectl create ns nemo-operator
kubectl create secret -n nemo-operator docker-registry ngc-secret \
  --docker-server=nvcr.io \
  --docker-username='$oauthtoken' \
  --docker-password=<ngc-api-key>
```

```bash
helm fetch https://helm.ngc.nvidia.com/nvidia/nemo-microservices/charts/nemo-operator-25.4.0.tgz --username='$oauthtoken' --password=<YOUR NGC API KEY>
helm install nemo-operator-25.4.0.tgz -n nemo-operator --set imagePullSecrets[0].name=ngc-secret --set controllerManager.manager.scheduler=volcano
```

4. **Create Custom Resources (CRs) for all NeMo and NIM samples** from `config/samples/nemo/latest` folder.

```bash
kubectl apply -f config/samples/nemo/latest
```

5. Access your jupyter server

Once the Ansible playbook has completed, the Jupyter server will be running in your cluster.

To access the Jupyter notebook, use `kubectl port-forward` from your local machine and launch using http://localhost:8888. The token is "token"

```bash
kubectl port-forward svc/jupyter-service -n nemo 8888:8888
```
5. Access your notebook

Once you launch the Jupyter server, the e2e test notebook is under the work directory.

## 2. Running the Notebook from Localhost

You can also run the notebook locally on your machine and connect to the NeMo Microservices running in your cluster via port-forwarding.

### Prerequisites

- NeMo Microservices deployed in your cluster (see steps 2-4 above)
- Python 3.8+ with Jupyter installed locally
- `kubectl` or `oc` CLI configured to access your cluster

### Steps

1. **Set up port-forwards for all NeMo Microservices**

   Run these commands in separate terminal windows or as background processes to keep the port-forwards active:

   ```bash
   # Data Store (port 8001)
   kubectl port-forward -n <your-namespace> svc/nemodatastore-sample 8001:8000
   
   # Entity Store (port 8002)
   kubectl port-forward -n <your-namespace> svc/nemoentitystore-sample 8002:8000
   
   # Customizer (port 8003)
   kubectl port-forward -n <your-namespace> svc/nemocustomizer-sample 8003:8000
   
   # Evaluator (port 8004)
   kubectl port-forward -n <your-namespace> svc/nemoevaluator-sample 8004:8000
   
   # Guardrails (port 8005)
   kubectl port-forward -n <your-namespace> svc/nemoguardrails-sample 8005:8000
   
   # NIM (port 8006)
   kubectl port-forward -n <your-namespace> svc/meta-llama3-1b-instruct 8006:8000
   ```

   **Note:** Replace `<your-namespace>` with your actual namespace (e.g., `arhkp-nemo-helm`).

   **Tip:** To run port-forwards in the background, add `&` at the end of each command, or use a tool like `tmux` or `screen` to manage multiple port-forwards.

2. **Set environment variables**

   The `config.py` file defaults to cluster mode. You can set environment variables either:
   
   **Option A: Create a `.env` file** (recommended for IDE usage):
   
   Create a `.env` file in the `jupyter-notebook` directory:
   ```bash
   cd /path/to/NeMo-Microservices/demos/jupyter-notebook
   cat > .env << EOF
   HF_TOKEN=your-huggingface-token-here
   RUN_LOCALLY=true
   NMS_NAMESPACE=your-namespace
   EOF
   ```
   
   The `.env` file is automatically loaded by `config.py` (requires `python-dotenv`).
   
   **Option B: Set environment variables in shell:**
   
   To use localhost URLs, set the `RUN_LOCALLY` environment variable:

   ```bash
   export RUN_LOCALLY=true
   export NMS_NAMESPACE="<your-namespace>"  # e.g., "arhkp-nemo-helm"
   export HF_TOKEN="<your-huggingface-token>"
   ```

   Alternatively, you can set these when launching Jupyter:

   ```bash
   RUN_LOCALLY=true NMS_NAMESPACE="<your-namespace>" HF_TOKEN="<your-token>" jupyter lab
   ```

   When `RUN_LOCALLY=true`, the config will automatically use localhost URLs:
   - `http://localhost:8001` (Data Store)
   - `http://localhost:8002` (Entity Store)
   - `http://localhost:8003` (Customizer)
   - `http://localhost:8004` (Evaluator)
   - `http://localhost:8005` (Guardrails)
   - `http://localhost:8006` (NIM)

3. **Install required Python packages**

   ```bash
   pip install huggingface_hub transformers peft datasets trl jsonschema litellm jinja2 torch openai jupyterlab requests python-dotenv
   ```

   **Note:** `python-dotenv` is used to load environment variables from `.env` file (for IDE usage).

4. **Launch Jupyter locally**

   ```bash
   cd /path/to/NeMo-Microservices/demos/jupyter-notebook
   jupyter lab
   ```

5. **Open the notebook**

   Open `e2e-notebook.ipynb` in Jupyter Lab and run the cells.

### Important Notes

- **Configuration mode:** The `config.py` defaults to cluster mode (uses cluster-internal URLs). Set `RUN_LOCALLY=true` environment variable to use localhost URLs for local execution.
- **Keep port-forwards active:** When running locally, the port-forward connections must remain active while running the notebook. If a port-forward drops, restart it.
- **Evaluation jobs:** Evaluation jobs run inside the cluster and need cluster-internal URLs. The notebook uses `NIM_URL_CLUSTER` for evaluation targets, which always points to the cluster service name (not localhost), regardless of `RUN_LOCALLY` setting.
- **GPU memory:** If you encounter CUDA out of memory errors during evaluation, you may need to restart the NIM pod to free GPU memory:
  ```bash
  kubectl delete pod -n <your-namespace> <nim-pod-name>
  ```
