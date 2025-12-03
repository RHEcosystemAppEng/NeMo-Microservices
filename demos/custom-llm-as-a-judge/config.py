# (Required) NeMo Microservices URLs
# Cluster mode only - runs in Workbench/Notebook within the cluster
import os
from pathlib import Path

# Load environment variables from env.donotcommit file if it exists (for IDE usage)
# Uses python-dotenv library - install with: pip install python-dotenv
# 🔒 SECURITY: Never hardcode secrets in config files!
# All sensitive values (tokens, API keys) should be in env.donotcommit file
try:
    from dotenv import load_dotenv
    # Load env.donotcommit file first (preferred)
    env_donotcommit_path = Path(__file__).parent / "env.donotcommit"
    if env_donotcommit_path.exists():
        load_dotenv(env_donotcommit_path, override=False)
    # Then load .env as a fallback (for backward compatibility)
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)  # override=False: don't overwrite existing env vars
except ImportError:
    # python-dotenv not installed - skip .env loading (will use system env vars only)
    pass

# Namespace for cluster services
# Default is provided for convenience, but should be set in env.donotcommit file
NMS_NAMESPACE = os.getenv("NMS_NAMESPACE", "anemo-rhoai")

# External NIM service variables (always defined for compatibility)
# These are used for Knative InferenceService (not recommended due to URL stripping issues)
EXTERNAL_NIM_SERVICE = os.getenv("EXTERNAL_NIM_SERVICE", "anemo-rhoai-predictor-00002")
EXTERNAL_NIM_NAMESPACE = os.getenv("EXTERNAL_NIM_NAMESPACE", NMS_NAMESPACE)
EXTERNAL_NIM_PORT = os.getenv("EXTERNAL_NIM_PORT", "80")

# Cluster-internal URLs (for running from within cluster Workbench/Notebook)
NDS_URL = f"http://nemodatastore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
ENTITY_STORE_URL = f"http://nemoentitystore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
EVALUATOR_URL = f"http://nemoevaluator-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
# External NIM service (if using external NIM - not recommended, use STANDARD_NIM_SERVICE instead)
NIM_URL = f"http://{EXTERNAL_NIM_SERVICE}.{EXTERNAL_NIM_NAMESPACE}.svc.cluster.local:{EXTERNAL_NIM_PORT}"
LLAMASTACK_URL = f"http://llamastack.{NMS_NAMESPACE}.svc.cluster.local:8321"  # LlamaStack Server

# For evaluation jobs, use NEMO_URL which points to Evaluator
# The notebook uses NEMO_URL for Evaluator endpoints
NEMO_URL = EVALUATOR_URL

# Cluster-internal NIM URL (for evaluation jobs running inside the cluster)
# Always use cluster service name, regardless of where notebook runs
# Evaluation jobs execute in-cluster and need cluster URLs
# This is separate from NIM_URL because evaluation jobs can't use localhost
# 
# NIM Model Serving Configuration (for llama-3.2-1b-instruct via KServe InferenceService)
# Uses KServe InferenceService deployed via Helm chart
# Note: Service name may differ from model name
# For KServe InferenceService, use the external URL from the InferenceService status
# Find your URL: oc get inferenceservice <name> -n <namespace> -o jsonpath='{.status.url}'
NIM_MODEL_SERVING_SERVICE = os.getenv("NIM_MODEL_SERVING_SERVICE", "anemo-rhoai-model")
NIM_MODEL_SERVING_MODEL = os.getenv("NIM_MODEL_SERVING_MODEL", "meta/llama-3.2-1b-instruct")

# External URL (recommended - may work around Evaluator URL stripping bug)
# This is the HTTPS URL from the InferenceService status
NIM_MODEL_SERVING_URL_EXTERNAL = os.getenv("NIM_MODEL_SERVING_URL_EXTERNAL", "https://anemo-rhoai-model-anemo-rhoai.apps.ai-dev05.kni.syseng.devcluster.openshift.com")

# Cluster-internal URL (has URL stripping bug in Evaluator v25.06/v25.08)
# ⚠️  WARNING: Evaluator strips /chat/completions from cluster-internal Knative service URLs
# Using external URL (HTTPS) may work around this issue
# For cluster-internal access, use the predictor service name
# Find your service: oc get inferenceservice <name> -n <namespace> -o jsonpath='{.status.components.predictor.address.url}'
NIM_MODEL_SERVING_URL_CLUSTER = f"http://{NIM_MODEL_SERVING_SERVICE}-predictor.{NMS_NAMESPACE}.svc.cluster.local:80"

# Legacy: Standard NIM service (DEPRECATED - kept for backward compatibility)
# The e2e-notebook works because it uses meta-llama3-1b-instruct service on port 8000
# This avoids the URL stripping issue with Knative services
STANDARD_NIM_SERVICE = os.getenv("STANDARD_NIM_SERVICE", "meta-llama3-1b-instruct")
NIM_URL_CLUSTER = f"http://{STANDARD_NIM_SERVICE}.{NMS_NAMESPACE}.svc.cluster.local:8000"

# Default to NIM Model Serving (can override via env var)
# ⚠️  WARNING: NIM Model Serving (Knative) has URL stripping issues with Evaluator v25.06/v25.08
# The Evaluator strips /chat/completions from Knative service URLs during job execution
# Using external URL may work around this issue
USE_NIM_MODEL_SERVING = os.getenv("USE_NIM_MODEL_SERVING", "true").lower() == "true"
USE_EXTERNAL_URL = os.getenv("USE_EXTERNAL_URL", "true").lower() == "true"  # Use external URL to avoid URL stripping

# Set the active NIM URL based on configuration
if USE_NIM_MODEL_SERVING:
    ACTIVE_NIM_SERVICE = NIM_MODEL_SERVING_SERVICE
    ACTIVE_NIM_MODEL = NIM_MODEL_SERVING_MODEL
    # Use external URL if enabled (may work around Evaluator bug)
    if USE_EXTERNAL_URL:
        NIM_URL_CLUSTER = NIM_MODEL_SERVING_URL_EXTERNAL
    else:
        NIM_URL_CLUSTER = NIM_MODEL_SERVING_URL_CLUSTER
else:
    ACTIVE_NIM_SERVICE = STANDARD_NIM_SERVICE
    ACTIVE_NIM_MODEL = "meta/llama-3.2-1b-instruct"
    NIM_URL_CLUSTER = f"http://{STANDARD_NIM_SERVICE}.{NMS_NAMESPACE}.svc.cluster.local:8000"

# Alternative: If your model is in Knative InferenceService, use this instead (but has URL stripping issues)
# KNATIVE_NIM_SERVICE = os.getenv("KNATIVE_NIM_SERVICE", "anemo-rhoai-predictor-00002")
# NIM_URL_CLUSTER = f"http://{KNATIVE_NIM_SERVICE}.{NMS_NAMESPACE}.svc.cluster.local:80"

# Option 2: Use Knative InferenceService (if standard service not available)
# This is what was causing the URL stripping issue
# EXTERNAL_NIM_SERVICE = os.getenv("EXTERNAL_NIM_SERVICE", "anemo-rhoai-predictor-00002")
# EXTERNAL_NIM_NAMESPACE = os.getenv("EXTERNAL_NIM_NAMESPACE", NMS_NAMESPACE)
# NIM_URL_CLUSTER = f"http://{EXTERNAL_NIM_SERVICE}.{EXTERNAL_NIM_NAMESPACE}.svc.cluster.local:80"

# (Optional) NIM Service Account Token for authenticating with NIM model services
# This is a Kubernetes service account token (JWT) used to authenticate with NIM endpoints
# Get your token: oc create token anemo-rhoai-model-sa -n anemo-rhoai
NIM_SERVICE_ACCOUNT_TOKEN = os.getenv("NIM_SERVICE_ACCOUNT_TOKEN", "")

# (Optional) NeMo Data Store token
NDS_TOKEN = os.getenv("NDS_TOKEN", "token")

# (Optional) Use a dedicated namespace and dataset name for tutorial assets
DATASET_NAME = os.getenv("DATASET_NAME", "custom-llm-as-a-judge-eval-data")

# (Optional) API Keys - should be set via environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")  # For build.nvidia.com / integrate.api.nvidia.com

# (Optional) Hugging Face Token (if needed for dataset downloads)
HF_TOKEN = os.getenv("HF_TOKEN", "")

