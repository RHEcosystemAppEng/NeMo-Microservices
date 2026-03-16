# (Required) NeMo Microservices URLs — set NMS_NAMESPACE in env or env.donotcommit
import os
_NMS_NAMESPACE = os.getenv("NMS_NAMESPACE", "anemo-rhoai")
NDS_URL = f"http://nemodatastore-sample.{_NMS_NAMESPACE}.svc.cluster.local:8000"
ENTITY_STORE_URL = f"http://nemoentitystore-sample.{_NMS_NAMESPACE}.svc.cluster.local:8000"
NEMO_URL = f"http://nemocustomizer-sample.{_NMS_NAMESPACE}.svc.cluster.local:8000"
EVAL_URL = f"http://nemoevaluator-sample.{_NMS_NAMESPACE}.svc.cluster.local:8000"
GUARDRAILS_URL = f"http://nemoguardrails-sample.{_NMS_NAMESPACE}.svc.cluster.local:8000"
NIM_URL = f"http://meta-llama3-1b-instruct.{_NMS_NAMESPACE}.svc.cluster.local:8000"
LLAMASTACK_URL = f"http://llamastack.{_NMS_NAMESPACE}.svc.cluster.local:8321"

# (Required) Configure the base model. Must be one supported by the NeMo Customizer deployment!
BASE_MODEL = "meta/llama-3.2-1b-instruct"

# (Required) Hugging Face Token
HF_TOKEN = ""

# (Optional) Namespace to associate with Datasets and Customization jobs
NAMESPACE = "nvidia-e2e-tutorial"

# (Optional) Entity Store Project ID. Modify if you've created a project in Entity Store that you'd
# like to associate with your Customized models.
PROJECT_ID = ""

# (Optional) Directory to save the Customized model
CUSTOMIZED_MODEL_DIR = "nvidia-e2e-tutorial/test-messages-model@v1"
