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
# Otherwise, try to auto-detect by checking if we can resolve cluster DNS
RUN_LOCALLY_ENV = os.getenv("RUN_LOCALLY")
if RUN_LOCALLY_ENV is not None:
    RUN_LOCALLY = RUN_LOCALLY_ENV.lower() == "true"
else:
    # Auto-detect: try to resolve cluster DNS to determine if we're in-cluster
    import socket
    try:
        # Try to resolve a cluster-internal service name
        test_host = f"nemodatastore-sample.{NMS_NAMESPACE}.svc.cluster.local"
        socket.gethostbyname(test_host)
        # If resolution succeeds, we're likely in-cluster
        RUN_LOCALLY = False
    except (socket.gaierror, OSError):
        # If DNS resolution fails, we're likely running locally
        RUN_LOCALLY = True

if RUN_LOCALLY:
    # Localhost URLs (for port-forwarding from local machine)
    NDS_URL = "http://localhost:8001"  # Data Store
    ENTITY_STORE_URL = "http://localhost:8002"  # Entity Store
    GUARDRAILS_URL = "http://localhost:8005"  # Guardrails (optional)
    NIM_CHAT_URL = "http://localhost:8006"  # Chat NIM
    NIM_EMBEDDING_URL = "http://localhost:8007"  # Embedding NIM (nv-embedqa-1b-v2)
    LLAMASTACK_URL = "http://localhost:8321"  # LlamaStack Server
else:
    # Cluster-internal URLs (for running from within cluster)
    NDS_URL = f"http://nemodatastore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
    ENTITY_STORE_URL = f"http://nemoentitystore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
    GUARDRAILS_URL = f"http://nemoguardrails-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
    NIM_CHAT_URL = f"http://meta-llama3-1b-instruct.{NMS_NAMESPACE}.svc.cluster.local:8000"
    NIM_EMBEDDING_URL = f"http://nv-embedqa-1b-v2.{NMS_NAMESPACE}.svc.cluster.local:8000"
    LLAMASTACK_URL = f"http://llamastack.{NMS_NAMESPACE}.svc.cluster.local:8321"  # LlamaStack Server

# Cluster-internal NIM URLs (always use cluster service names)
# These are used for operations that run inside the cluster
NIM_CHAT_URL_CLUSTER = f"http://meta-llama3-1b-instruct.{NMS_NAMESPACE}.svc.cluster.local:8000"
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

# (Optional) RAG Configuration
# Number of documents to retrieve
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
# Similarity threshold for retrieval
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3"))

