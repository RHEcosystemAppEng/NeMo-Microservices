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
NMS_NAMESPACE = os.getenv("NMS_NAMESPACE", "arhkp-nemo-helm")

# Determine if running locally or in cluster
# If RUN_LOCALLY env var is explicitly set, use it
# If absent, default to cluster mode (False)
RUN_LOCALLY_ENV = os.getenv("RUN_LOCALLY")
if RUN_LOCALLY_ENV is not None:
    RUN_LOCALLY = RUN_LOCALLY_ENV.lower() == "true"
else:
    # Default to cluster mode when RUN_LOCALLY is not set
    RUN_LOCALLY = False

if RUN_LOCALLY:
    # Localhost URLs (for port-forwarding from local machine)
    NDS_URL = "http://localhost:8001"  # Data Store
    ENTITY_STORE_URL = "http://localhost:8002"  # Entity Store
    CUSTOMIZER_URL = "http://localhost:8003"  # Customizer
    EVALUATOR_URL = "http://localhost:8004"  # Evaluator
    GUARDRAILS_URL = "http://localhost:8005"  # Guardrails
    NIM_URL = "http://localhost:8006"  # NIM
else:
    # Cluster-internal URLs (for running from within cluster)
    NDS_URL = f"http://nemodatastore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
    ENTITY_STORE_URL = f"http://nemoentitystore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
    CUSTOMIZER_URL = f"http://nemocustomizer-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
    EVALUATOR_URL = f"http://nemoevaluator-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
    GUARDRAILS_URL = f"http://nemoguardrails-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
    NIM_URL = f"http://meta-llama3-1b-instruct.{NMS_NAMESPACE}.svc.cluster.local:8000"

# Cluster-internal NIM URL (for evaluation jobs running inside the cluster)
# Always use cluster service name, regardless of where notebook runs
NIM_URL_CLUSTER = f"http://meta-llama3-1b-instruct.{NMS_NAMESPACE}.svc.cluster.local:8000"

# (Required) Hugging Face Token
# MUST be set via HF_TOKEN environment variable - do not hardcode secrets
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable must be set. Export it with: export HF_TOKEN='your-token'")

# (Optional) To observe training with WandB
WANDB_API_KEY = os.getenv("WANDB_API_KEY", "")

# (Optional) Modify if you've configured a NeMo Data Store token
NDS_TOKEN = os.getenv("NDS_TOKEN", "token")

# (Optional) Use a dedicated namespace and dataset name for tutorial assets
DATASET_NAME = os.getenv("DATASET_NAME", "xlam-ft-dataset")

# (Optional) Configure the base model. Must be one supported by the NeMo Customizer deployment!
BASE_MODEL = os.getenv("BASE_MODEL", "meta/llama-3.2-1b-instruct")
BASE_MODEL_VERSION = os.getenv("BASE_MODEL_VERSION", "v1.0.0+A100")
