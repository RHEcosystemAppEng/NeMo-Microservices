# Configuration for Customizer Test Notebook
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

# Namespace for cluster services (example default; set NMS_NAMESPACE in env.donotcommit to override)
NMS_NAMESPACE = os.getenv("NMS_NAMESPACE", "anemo-rhoai")

# Cluster-internal URLs (for running from within cluster Workbench/Notebook)
CUSTOMIZER_URL = f"http://nemocustomizer-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
DATASTORE_URL = f"http://nemodatastore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
ENTITY_STORE_URL = f"http://nemoentitystore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"

# (Optional) NeMo Data Store token
NDS_TOKEN = os.getenv("NDS_TOKEN", "token")
