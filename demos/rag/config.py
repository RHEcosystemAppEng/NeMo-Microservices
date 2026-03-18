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

# Namespace for cluster services (set in env.donotcommit or environment)
NMS_NAMESPACE = os.getenv("NMS_NAMESPACE", "anemo-rhoai")

# Cluster-internal URLs (for running from within cluster Workbench/Notebook)
NDS_URL = f"http://nemodatastore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
ENTITY_STORE_URL = f"http://nemoentitystore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
GUARDRAILS_URL = f"http://nemoguardrails-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
# Note: Service name may differ from model name
# For KServe InferenceService, set via env or env.donotcommit (no default to avoid hard-coded URLs).
# Get URL: oc get inferenceservice <name> -n $NAMESPACE -o jsonpath='{.status.url}'
# Or for cluster-internal: http://<inferenceservice>-predictor.<namespace>.svc.cluster.local:80
# When not set, validate_config() will raise so the notebook fails fast with a clear error.
NIM_CHAT_URL = os.getenv("NIM_CHAT_URL", "")
NIM_EMBEDDING_URL = f"http://nv-embedqa-1b-v2.{NMS_NAMESPACE}.svc.cluster.local:8000"
# LlamaStack: override via LLAMASTACK_URL for RHOAI (e.g. copilot-llama-stack-service)
LLAMASTACK_URL = os.getenv("LLAMASTACK_URL", f"http://llamastack.{NMS_NAMESPACE}.svc.cluster.local:8321")
# Chat model id for LlamaStack (e.g. nvidia/meta/llama-3.2-1b-instruct or vllm-inference/redhataillama-31-8b-instruct)
LLAMASTACK_CHAT_MODEL = os.getenv("LLAMASTACK_CHAT_MODEL", "nvidia/meta/llama-3.2-1b-instruct")
# Optional: API key for LlamaStack client. Leave unset for RHOAI copilot-llama-stack (no client auth).
LLAMASTACK_API_KEY = os.getenv("LLAMASTACK_API_KEY", "")

# Cluster-internal NIM URLs (always use cluster service names)
# These are used for operations that run inside the cluster
# Note: For KServe InferenceService, use the predictor service name (without revision number)
# Find your service: oc get inferenceservice <name> -n <namespace> -o jsonpath='{.status.components.predictor.address.url}'
NIM_CHAT_URL_CLUSTER = os.getenv("NIM_CHAT_URL_CLUSTER", NIM_CHAT_URL if NIM_CHAT_URL else "")
NIM_EMBEDDING_URL_CLUSTER = f"http://nv-embedqa-1b-v2.{NMS_NAMESPACE}.svc.cluster.local:8000"

# (Optional) NeMo Data Store token
NDS_TOKEN = os.getenv("NDS_TOKEN", "token")

# (Optional) Use a dedicated namespace and dataset name for tutorial assets
DATASET_NAME = os.getenv("DATASET_NAME", "rag-tutorial-documents")

# (Optional) API Keys - should be set via environment variables
# Only needed if using external APIs as fallback
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")  # For build.nvidia.com / integrate.api.nvidia.com

# (Optional) Hugging Face Token (if needed for dataset downloads or fallback embeddings)
HF_TOKEN = os.getenv("HF_TOKEN", "")

# (Optional) NIM Service Account Token for authenticating with NIM model services
# This is a Kubernetes service account token (JWT) used to authenticate with NIM endpoints
# Get your token: oc create token <inferenceservice>-sa -n $NAMESPACE
NIM_SERVICE_ACCOUNT_TOKEN = os.getenv("NIM_SERVICE_ACCOUNT_TOKEN", "")

# (Optional) RAG Configuration
# Number of documents to retrieve
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
# Similarity threshold for retrieval
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3"))


def validate_config() -> None:
    """
    Validate that all required environment/config values are set for the RAG demo.
    Call this at the start of the notebook (e.g. right after importing config) to fail fast
    with a clear error if something is missing.

    Raises:
        ValueError: With a message listing all missing required variables and how to set them.
    """
    missing = []

    url = (NIM_CHAT_URL or "").strip()
    if not url:
        missing.append(
            "NIM_CHAT_URL must be set. Set it in env.donotcommit (or environment). "
            "Get URL: oc get inferenceservice <name> -n $NAMESPACE -o jsonpath='{.status.url}' "
            "Or cluster-internal: http://<inferenceservice>-predictor.<namespace>.svc.cluster.local:80"
        )
    elif not (url.startswith("http://") or url.startswith("https://")):
        missing.append(
            "NIM_CHAT_URL must be a valid URL (http:// or https://). "
            f"Current value: {url[:50]}..."
        )

    if missing:
        header = (
            "Configuration validation failed. The following required settings are missing or invalid:\n\n"
            "  • " + "\n  • ".join(missing)
            + "\n\nCopy env.donotcommit.example to env.donotcommit and fill in your values."
        )
        raise ValueError(header)

