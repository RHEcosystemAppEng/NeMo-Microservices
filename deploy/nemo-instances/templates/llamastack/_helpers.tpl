{{/*
LlamaStack configuration partials - split into logical sections for maintainability
*/}}

{{/*
Base configuration
*/}}
{{- define "llamastack.config.base" -}}
version: 2
image_name: nvidia
apis:
  - agents
  - datasetio
  - eval
  - files
  - inference
  - post_training
  - safety
  - scoring
  - tool_runtime
  - vector_io

{{- end -}}

{{/*
Provider configurations
*/}}
{{- define "llamastack.config.providers" -}}
providers:
  inference:
    - provider_id: nvidia
      provider_type: remote::nvidia
      config:
        url: ${env.NVIDIA_BASE_URL:=https://integrate.api.nvidia.com}
        {{- if .Values.llamastack.useBearerToken }}
        # Use Bearer token authentication for KServe InferenceService
        # Note: OpenAI client (used by NVIDIA provider) automatically formats api_key as "Bearer {api_key}"
        # So we set the service account token as the api_key
        api_key: ${env.NVIDIA_SERVICE_ACCOUNT_TOKEN}
        {{- else }}
        # Use API key authentication for NVIDIA API
        api_key: ${env.NVIDIA_API_KEY}
        {{- end }}
        append_api_version: ${env.NVIDIA_APPEND_API_VERSION:=True}
  vector_io:
    - provider_id: faiss
      provider_type: inline::faiss
      config:
        persistence:
          backend: meta-reference
          namespace: default
  safety:
    - provider_id: nvidia
      provider_type: remote::nvidia
      config:
        guardrails_service_url: ${env.GUARDRAILS_SERVICE_URL:=http://{{ .Values.guardrail.name }}.{{ .Values.namespace.name }}.svc.cluster.local:8000}
        config_id: ${env.NVIDIA_GUARDRAILS_CONFIG_ID:={{ .Values.llamastack.guardrailsConfigId }}}
        model: ${env.SAFETY_MODEL:={{ .Values.llamastack.safetyModel }}}
  agents:
    - provider_id: meta-reference
      provider_type: inline::meta-reference
      config:
        persistence:
          agent_state:
            backend: meta-reference
            namespace: default
            table_name: agent_state
          responses:
            backend: meta-reference-sql
            namespace: default
            table_name: agent_responses
  eval:
    - provider_id: nvidia
      provider_type: remote::nvidia
      config:
        evaluator_url: ${env.NVIDIA_EVALUATOR_URL:=http://{{ .Values.evaluator.name }}.{{ .Values.namespace.name }}.svc.cluster.local:8000}
  post_training:
    - provider_id: nvidia
      provider_type: remote::nvidia
      config:
        api_key: ${env.NVIDIA_API_KEY:=}
        dataset_namespace: ${env.NVIDIA_DATASET_NAMESPACE:={{ .Values.llamastack.datasetNamespace }}}
        project_id: ${env.NVIDIA_PROJECT_ID:={{ .Values.llamastack.projectId }}}
        customizer_url: ${env.NVIDIA_CUSTOMIZER_URL:=http://{{ .Values.customizer.name }}.{{ .Values.namespace.name }}.svc.cluster.local:8000}
  datasetio:
    - provider_id: nvidia
      provider_type: remote::nvidia
      config:
        api_key: ${env.NVIDIA_API_KEY:=}
        dataset_namespace: ${env.NVIDIA_DATASET_NAMESPACE:={{ .Values.llamastack.datasetNamespace }}}
        project_id: ${env.NVIDIA_PROJECT_ID:={{ .Values.llamastack.projectId }}}
        datasets_url: ${env.NVIDIA_ENTITY_STORE_URL:=http://{{ .Values.entitystore.name }}.{{ .Values.namespace.name }}.svc.cluster.local:8000}
    - provider_id: localfs
      provider_type: inline::localfs
      config:
        kvstore:
          backend: meta-reference
          namespace: default
          table_name: datasets
  files:
    - provider_id: localfs
      provider_type: inline::localfs
      config:
        storage_dir: /tmp/files
        metadata_store:
          backend: meta-reference-sql
          namespace: default
          table_name: files
  scoring:
    - provider_id: basic
      provider_type: inline::basic
  tool_runtime:
    - provider_id: rag-runtime
      provider_type: inline::rag-runtime

{{- end -}}

{{/*
Storage configuration
*/}}
{{- define "llamastack.config.storage" -}}
storage:
  backends:
    meta-reference:
      type: kv_sqlite
      db_path: /tmp/storage_store.db
    meta-reference-sql:
      type: sql_sqlite
      db_path: /tmp/sql_storage_store.db
  stores:
    metadata:
      backend: meta-reference
      namespace: default
    conversations:
      backend: meta-reference-sql
      namespace: default
      table_name: conversations
    inference:
      backend: meta-reference-sql
      namespace: default
      table_name: inference
    prompts:
      backend: meta-reference
      namespace: default

{{- end -}}

{{/*
Models and shields configuration
*/}}
{{- define "llamastack.config.models" -}}
models:
  - metadata: { }
    model_id: ${env.INFERENCE_MODEL}
    provider_id: nvidia
    model_type: llm
  - metadata: { }
    model_id: ${env.SAFETY_MODEL}
    provider_id: nvidia
    model_type: llm
shields:
  - shield_id: {{ .Values.llamastack.guardrailsConfigId }}
    provider_id: nvidia
    provider_shield_id: {{ .Values.llamastack.guardrailsConfigId }}
    params:
      model: ${env.SAFETY_MODEL:={{ .Values.llamastack.safetyModel }}}

{{- end -}}

{{/*
Server and tool groups configuration
*/}}
{{- define "llamastack.config.server" -}}
vector_dbs: [ ]
datasets: [ ]
scoring_fns: [ ]
benchmarks: [ ]
tool_groups:
  - toolgroup_id: builtin::rag
    provider_id: rag-runtime
server:
  port: {{ .Values.llamastack.port }}
{{- end -}}

