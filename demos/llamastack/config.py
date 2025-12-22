# (Required) NeMo Microservices URLs
NDS_URL = "http://nemodatastore-sample.<your-namespace>.svc.cluster.local:8000" # Data Store
ENTITY_STORE_URL = "http://nemoentitystore-sample.<your-namespace>.svc.cluster.local:8000" # Entity Store
NEMO_URL = "http://nemocustomizer-sample.<your-namespace>.svc.cluster.local:8000" # Customizer 
EVAL_URL = "http://nemoevaluator-sample.<your-namespace>.svc.cluster.local:8000" # Evaluator
GUARDRAILS_URL = "http://nemoguardrails-sample.<your-namespace>.svc.cluster.local:8000" # Guardrails
NIM_URL = "http://meta-llama3-1b-instruct.<your-namespace>.svc.cluster.local:8000" # NIM
LLAMASTACK_URL = "http://llamastack.<your-namespace>.svc.cluster.local:8321" # LlamaStack Server

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
