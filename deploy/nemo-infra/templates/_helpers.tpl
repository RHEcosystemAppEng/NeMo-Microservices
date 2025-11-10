{{/*
Expand the name of the chart.
*/}}
{{- define "nemo-infra.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "nemo-infra.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "nemo-infra.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "nemo-infra.labels" -}}
helm.sh/chart: {{ include "nemo-infra.chart" . }}
{{ include "nemo-infra.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "nemo-infra.selectorLabels" -}}
app.kubernetes.io/name: {{ include "nemo-infra.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Get storage class - returns local-path if enabled, otherwise uses pvc.storageClass
*/}}
{{- define "nemo-infra.storageClass" -}}
{{- if .Values.localPathProvisioner.enabled }}
{{- "local-path" }}
{{- else }}
{{- .Values.pvc.storageClass }}
{{- end }}
{{- end }}

{{/*
Get volume access mode
*/}}
{{- define "nemo-infra.volumeAccessMode" -}}
{{- if .Values.localPathProvisioner.enabled }}
{{- "ReadWriteOnce" }}
{{- else }}
{{- .Values.pvc.volumeAccessMode }}
{{- end }}
{{- end }}

