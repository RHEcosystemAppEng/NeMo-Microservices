# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

# (Required) NeMo Microservices URLs
NDS_URL = "http://localhost:8001" # Data Store
ENTITY_STORE_URL = "http://localhost:8002" # Entity Store
NEMO_URL = "http://localhost:8003" # Customizer (also available at 8004 for Evaluator, 8005 for Guardrails)
NIM_URL = "http://localhost:8006" # NIM
LLAMASTACK_URL = "http://localhost:8321" # LlamaStack Server

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
