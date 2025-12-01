# (Required) NeMo Microservices URLs
# Auto-detect if running locally (via port-forward) or in cluster
import os
from pathlib import Path

# Load environment variables from env.donotcommit or .env file if it exists (for IDE usage)
# Uses python-dotenv library - install with: pip install python-dotenv
# Priority: env.donotcommit > .env (for backward compatibility)
try:
    from dotenv import load_dotenv
    config_dir = Path(__file__).parent
    # Try env.donotcommit first (preferred), then .env as fallback
    env_donotcommit = config_dir / "env.donotcommit"
    env_file = config_dir / ".env"
    if env_donotcommit.exists():
        load_dotenv(env_donotcommit, override=False)  # override=False: don't overwrite existing env vars
    elif env_file.exists():
        load_dotenv(env_file, override=False)  # override=False: don't overwrite existing env vars
except ImportError:
    # python-dotenv not installed - skip .env loading (will use system env vars only)
    pass

# Namespace for cluster services
NMS_NAMESPACE = os.getenv("NMS_NAMESPACE", "anemo-rhoai")

# Determine if running locally or in cluster
# If RUN_LOCALLY env var is explicitly set, use it
# If absent, default to cluster mode (False)
RUN_LOCALLY_ENV = os.getenv("RUN_LOCALLY")
if RUN_LOCALLY_ENV is not None:
    RUN_LOCALLY = RUN_LOCALLY_ENV.lower() == "true"
else:
    # Default to cluster mode when RUN_LOCALLY is not set
    RUN_LOCALLY = False

# External NIM service variables (always defined for compatibility)
# These are used for Knative InferenceService (not recommended due to URL stripping issues)
EXTERNAL_NIM_SERVICE = os.getenv("EXTERNAL_NIM_SERVICE", "anemo-rhoai-predictor-00002")
EXTERNAL_NIM_NAMESPACE = os.getenv("EXTERNAL_NIM_NAMESPACE", NMS_NAMESPACE)
EXTERNAL_NIM_PORT = os.getenv("EXTERNAL_NIM_PORT", "80")

if RUN_LOCALLY:
    # Localhost URLs (for port-forwarding from local machine)
    NDS_URL = "http://localhost:8001"  # Data Store
    ENTITY_STORE_URL = "http://localhost:8002"  # Entity Store
    EVALUATOR_URL = "http://localhost:8004"  # Evaluator
    NIM_URL = "http://localhost:8006"  # NIM (optional, for target model)
    LLAMASTACK_URL = "http://localhost:8321"  # LlamaStack Server
else:
    # Cluster-internal URLs (for running from within cluster)
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
# NIM Model Serving Configuration (NEW - for llama-3.2-1b-instruct via NIM Model Serving)
# Uses KServe/Knative InferenceService deployed via Helm chart
NIM_MODEL_SERVING_SERVICE = os.getenv("NIM_MODEL_SERVING_SERVICE", "anemo-rhoai-model2")
NIM_MODEL_SERVING_MODEL = os.getenv("NIM_MODEL_SERVING_MODEL", "meta/llama-3.2-1b-instruct")

# Option 1: Use external URL (may work around Evaluator URL stripping bug)
NIM_MODEL_SERVING_URL_EXTERNAL = os.getenv("NIM_MODEL_SERVING_URL_EXTERNAL", "https://anemo-rhoai-model2-anemo-rhoai.apps.ai-dev05.kni.syseng.devcluster.openshift.com")

# Option 2: Use cluster-internal URL (has URL stripping bug in Evaluator)
# Knative services use port 80 (HTTP) and predictor service name
# For anemo-rhoai-model2, the service is anemo-rhoai-model2-predictor-00001
NIM_MODEL_SERVING_URL_CLUSTER = f"http://{NIM_MODEL_SERVING_SERVICE}-predictor-00001.{NMS_NAMESPACE}.svc.cluster.local:80"

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

# Optional: Service account token for authentication (if required)
# This token is used for cluster-internal authentication
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

