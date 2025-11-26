# (Required) NeMo Microservices URLs
# Auto-detect if running locally (via port-forward) or in cluster
import os
from pathlib import Path

# Load environment variables from .env file if it exists (for IDE usage)
# Uses python-dotenv library - install with: pip install python-dotenv
try:
    from dotenv import load_dotenv
    # Load .env file from the same directory as this config file
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path, override=False)  # override=False: don't overwrite existing env vars
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
# IMPORTANT: Use the standard NIM service (like e2e-notebook) instead of Knative InferenceService
# The e2e-notebook works because it uses meta-llama3-1b-instruct service on port 8000
# This avoids the URL stripping issue with Knative services
# 
# Option 1: Use standard NIM service (RECOMMENDED - matches e2e-notebook pattern)
# NOTE: If your model (meta/llama-2-7b-chat) is in the Knative service, you may need to use that instead
# Check which service has your model: oc exec -n <namespace> <evaluator-pod> -- curl http://<service>/v1/models
STANDARD_NIM_SERVICE = os.getenv("STANDARD_NIM_SERVICE", "meta-llama3-1b-instruct")
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

