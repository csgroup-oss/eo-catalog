{{/*
Copyright 2025 CS Group

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/}}

{{/*
Return the proper Docker Image Registry Secret Names
*/}}
{{- define "cnpgstac.imagePullSecrets" -}}
{{- include "common.images.pullSecrets" (dict "images" (list .Values.cnpgstac.image) "global" .Values.global) -}}
{{- end -}}

{{/*
Render imageCatalogRef block inside spec
*/}}
{{- define "cnpgstac.imageCatalogRef" -}}
apiGroup: postgresql.cnpg.io
kind: ClusterImageCatalog
name: {{ default "cnpgstac" .Values.cnpgstac.imageCatalog.name }}
major: {{ default 17 .Values.cnpgstac.imageCatalog.major }}
{{- end -}}

{{/*
Render only the images list for ClusterImageCatalog, with inline image values
*/}}
{{- define "cnpgstac.clusterImageCatalogList" -}}
{{- range .Values.cnpgstac.imageCatalog.images }}
  - major: {{ .major }}
    image: "{{- $registry := trimSuffix "/" (default "ghcr.io" .registry) -}}
            {{- $repository := trimPrefix "/" (default "csgroup-oss/eo-catalog-cnpgstac" .repository) -}}
            {{- $tag := default "latest" .tag -}}
            {{- $digest := .digest -}}
            {{- if $digest -}}
              {{- printf "%s/%s@%s" $registry $repository $digest -}}
            {{- else -}}
              {{- printf "%s/%s:%v" $registry $repository $tag -}}
            {{- end }}"
{{- end }}
{{- end }}

{{/*
Calculate the memory settings
*/}}

{{/*
Convert suffix to PostgreSQL valid memory units :
https://www.postgresql.org/docs/current/config-setting.html#CONFIG-SETTING-NAMES-VALUES
*/}}
{{- define "limit_suffix_bytes" -}}
{{- $limit_suffix := .Values.cnpgstac.resources.limits.memory | toString | regexFind "[^0-9.]+" -}}
  {{- if eq "G" $limit_suffix -}} 
    GB
  {{- else if eq "Gi" $limit_suffix -}} 
    GB
  {{- else if eq "M" $limit_suffix -}} 
    MB
  {{- else if eq "Mi" $limit_suffix -}} 
    MB
  {{- else if eq "k" $limit_suffix -}} 
    KB
  {{- else if eq "Ki" $limit_suffix -}} 
    KB
  {{- else if eq "T" $limit_suffix -}} 
    TB
  {{- else if eq "Ti" $limit_suffix -}} 
    TB
  {{- else if eq "P" $limit_suffix -}} 
    PB
  {{- else if eq "Pi" $limit_suffix -}} 
    PB
  {{- else if eq "E" $limit_suffix -}} 
    EB
  {{- else if eq "Ei" $limit_suffix -}} 
    EB
  {{- else if eq "" $limit_suffix -}}
  {{- /* Check for empty suffix, meaning bytes */ -}}
    B
  {{- else -}}
  {{- /* Unknown suffix case, assume GB */ -}}
    GB {{- printf " # Warning: Unknown suffix '%s' Defaulting to GB." . -}}
  {{- end -}}
{{- end -}}

{{/*
Calculate shared_buffers: should be 1/4 of the total RAM
*/}}
{{- define "shared_buffers" -}}
{{- $limit_value := .Values.cnpgstac.resources.limits.memory | toString | regexFind "[0-9.]+" -}}
{{ mulf $limit_value 0.25 }}
{{- end -}}

{{/*
Calculate effective_cache_size: should be 3/4 of the total RAM
*/}}
{{- define "effective_cache_size" -}}
{{- $limit_value := .Values.cnpgstac.resources.limits.memory | toString | regexFind "[0-9.]+" -}}
{{ mulf $limit_value 0.75 }}
{{- end -}}

