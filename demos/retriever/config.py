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

# Cluster-internal URLs (for running from within cluster Workbench/Notebook)
# NeMo Retriever service URL
NIM_RETRIEVER_URL = f"http://nv-rerankqa-1b-v2.{NMS_NAMESPACE}.svc.cluster.local:8000"

# Optional: Other NeMo services for RAG integration
ENTITY_STORE_URL = f"http://nemoentitystore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
NIM_EMBEDDING_URL = f"http://nv-embedqa-1b-v2.{NMS_NAMESPACE}.svc.cluster.local:8000"
NIM_CHAT_URL = os.getenv("NIM_CHAT_URL", f"http://meta-llama3-1b-instruct.{NMS_NAMESPACE}.svc.cluster.local:8000")

# (Optional) NeMo Data Store token (if using Data Store)
NDS_TOKEN = os.getenv("NDS_TOKEN", "token")

# (Optional) Use a dedicated namespace and dataset name for tutorial assets
DATASET_NAME = os.getenv("DATASET_NAME", "retriever-tutorial-documents")

# (Optional) API Keys - should be set via environment variables
# Only needed if using external APIs as fallback
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")

# (Optional) NIM Service Account Token for authenticating with NIM model services
# This is a Kubernetes service account token (JWT) used to authenticate with NIM endpoints
NIM_SERVICE_ACCOUNT_TOKEN = os.getenv("NIM_SERVICE_ACCOUNT_TOKEN", "")

# (Optional) Retriever Configuration
# Number of documents to rerank
RETRIEVER_TOP_K = int(os.getenv("RETRIEVER_TOP_K", "10"))
# Number of top results to return after reranking
RETRIEVER_TOP_N = int(os.getenv("RETRIEVER_TOP_N", "5"))
