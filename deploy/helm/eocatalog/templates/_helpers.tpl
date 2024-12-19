{{/*
Create the name of the service account to use for the STAC API
*/}}
{{- define "eocatalogue.stac.serviceAccountName" -}}
{{- if .Values.stac.serviceAccount.create -}}
    {{ default (printf "%s-stac-api" (include "common.names.fullname" .)) .Values.stac.serviceAccount.name | trunc 63 | trimSuffix "-" }}
{{- else -}}
    {{ default "default" .Values.stac.serviceAccount.name }}
{{- end -}}
{{- end -}}

{{/*
Return the proper Docker Image Registry Secret Names
*/}}
{{- define "eocatalogue.imagePullSecrets" -}}
{{- include "common.images.pullSecrets" (dict "images" (list .Values.stac.image) "global" .Values.global) -}}
{{- end -}}

{{/*
Return the proper service name for EO Catalogue STAC API
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
*/}}
{{- define "eocatalogue.stac" -}}
{{- printf "%s-stac-api" (include "common.names.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name for PostgreSQL
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
*/}}
{{- define "eocatalogue.postgresql.fullname" -}}
{{- printf "%s-%s" .Release.Name "postgresql" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Return the Database hostname
*/}}
{{- define "eocatalogue.databaseHost" -}}
{{- if eq .Values.postgresql.architecture "replication" -}}
{{- ternary (include "eocatalogue.postgresql.fullname" .) .Values.externalDatabase.host .Values.postgresql.enabled -}}-primary
{{- else -}}
{{- ternary (include "eocatalogue.postgresql.fullname" .) .Values.externalDatabase.host .Values.postgresql.enabled -}}
{{- end -}}
{{- end -}}

{{/*
Return the Database hostname
*/}}
{{- define "eocatalogue.databaseHostWriter" -}}
{{- if and (not .Values.postgresql.enabled) .Values.externalDatabase.hostWriter -}}
    {{ .Values.externalDatabase.hostWriter }}
{{- else -}}
    {{ (include "eocatalogue.databaseHost" .)}}
{{- end -}}
{{- end -}}

{{/*
Return the Database port
*/}}
{{- define "eocatalogue.databasePort" -}}
{{- ternary "5432" .Values.externalDatabase.port .Values.postgresql.enabled | quote -}}
{{- end -}}

{{/*
Return the Database database name
*/}}
{{- define "eocatalogue.databaseName" -}}
{{- if .Values.postgresql.enabled -}}
    {{- if .Values.global.postgresql -}}
        {{- if .Values.global.postgresql.auth -}}
            {{- coalesce .Values.global.postgresql.auth.database .Values.postgresql.auth.database -}}
        {{- else -}}
            {{- .Values.postgresql.auth.database -}}
        {{- end -}}
    {{- else -}}
        {{- .Values.postgresql.auth.database -}}
    {{- end -}}
{{- else -}}
    {{- .Values.externalDatabase.database -}}
{{- end -}}
{{- end -}}

{{/*
Return the Database user
*/}}
{{- define "eocatalogue.databaseUser" -}}
{{- if .Values.postgresql.enabled -}}
    {{- if .Values.global.postgresql -}}
        {{- if .Values.global.postgresql.auth -}}
            {{- coalesce .Values.global.postgresql.auth.username .Values.postgresql.auth.username -}}
        {{- else -}}
            {{- .Values.postgresql.auth.username -}}
        {{- end -}}
    {{- else -}}
        {{- .Values.postgresql.auth.username -}}
    {{- end -}}
{{- else -}}
    {{- .Values.externalDatabase.user -}}
{{- end -}}
{{- end -}}

{{/*
Return the Database encrypted password
*/}}
{{- define "eocatalogue.databaseSecretName" -}}
{{- if .Values.postgresql.enabled -}}
    {{- if .Values.global.postgresql -}}
        {{- if .Values.global.postgresql.auth -}}
            {{- if .Values.global.postgresql.auth.existingSecret -}}
                {{- tpl .Values.global.postgresql.auth.existingSecret $ -}}
            {{- else -}}
                {{- default (include "eocatalogue.postgresql.fullname" .) (tpl .Values.postgresql.auth.existingSecret $) -}}
            {{- end -}}
        {{- else -}}
            {{- default (include "eocatalogue.postgresql.fullname" .) (tpl .Values.postgresql.auth.existingSecret $) -}}
        {{- end -}}
    {{- else -}}
        {{- default (include "eocatalogue.postgresql.fullname" .) (tpl .Values.postgresql.auth.existingSecret $) -}}
    {{- end -}}
{{- else -}}
    {{- default (printf "%s-externaldb" .Release.Name) (tpl .Values.externalDatabase.existingSecret $) -}}
{{- end -}}
{{- end -}}

{{/*
Add environment variables to configure database values
*/}}
{{- define "eocatalogue.databaseSecretKey" -}}
{{- if .Values.postgresql.enabled -}}
    {{- print "password" -}}
{{- else -}}
    {{- if .Values.externalDatabase.existingSecret -}}
        {{- if .Values.externalDatabase.existingSecretPasswordKey -}}
            {{- printf "%s" .Values.externalDatabase.existingSecretPasswordKey -}}
        {{- else -}}
            {{- print "db-password" -}}
        {{- end -}}
    {{- else -}}
        {{- print "db-password" -}}
    {{- end -}}
{{- end -}}
{{- end -}}

{{- define "eocatalogue.databaseSecretPostgresKey" -}}
{{- if .Values.postgresql.enabled -}}
    {{- print "postgres-password" -}}
{{- else -}}
    {{- if .Values.externalDatabase.existingSecret -}}
        {{- if .Values.externalDatabase.existingSecretPostgresPasswordKey -}}
            {{- printf "%s" .Values.externalDatabase.existingSecretPostgresPasswordKey -}}
        {{- else -}}
            {{- print "db-postgres-password" -}}
        {{- end -}}
    {{- else -}}
        {{- print "db-postgres-password" -}}
    {{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create a default fully qualified redis name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
*/}}
{{- define "eocatalogue.redis.fullname" -}}
{{- include "common.names.dependency.fullname" (dict "chartName" "redis" "chartValues" .Values.redis "context" $) -}}
{{- end -}}

{{/*
Return the Redis&reg; secret name
*/}}
{{- define "eocatalogue.redis.secretName" -}}
{{- if .Values.redis.enabled }}
    {{- if .Values.redis.auth.existingSecret }}
        {{- printf "%s" .Values.redis.auth.existingSecret -}}
    {{- else -}}
        {{- printf "%s" (include "eocatalogue.redis.fullname" .) }}
    {{- end -}}
{{- else if .Values.externalRedis.existingSecret }}
    {{- printf "%s" .Values.externalRedis.existingSecret -}}
{{- else -}}
    {{- printf "%s-redis" (include "eocatalogue.redis.fullname" .) -}}
{{- end -}}
{{- end -}}

{{/*
Return the Redis&reg; secret key
*/}}
{{- define "eocatalogue.redis.secretPasswordKey" -}}
{{- if and .Values.redis.enabled .Values.redis.auth.existingSecret }}
    {{- .Values.redis.auth.existingSecretPasswordKey | printf "%s" }}
{{- else if and (not .Values.redis.enabled) .Values.externalRedis.existingSecret }}
    {{- .Values.externalRedis.existingSecretPasswordKey | printf "%s" }}
{{- else -}}
    {{- printf "redis-password" -}}
{{- end -}}
{{- end -}}

{{/*
Return whether Redis&reg; uses password authentication or not
*/}}
{{- define "eocatalogue.redis.auth.enabled" -}}
{{- if or (and .Values.redis.enabled .Values.redis.auth.enabled) (and (not .Values.redis.enabled) (or .Values.externalRedis.password .Values.externalRedis.existingSecret)) }}
    {{- true -}}
{{- end -}}
{{- end -}}

{{/*
Return whether Redis&reg; uses password authentication or not
*/}}
{{- define "eocatalogue.redis.tlsEnabled" -}}
{{- if or (and .Values.redis.enabled .Values.redis.tls.enabled) (and (not .Values.redis.enabled) (or .Values.externalRedis.tlsEnabled)) }}
    {{- "true" | quote -}}
{{- else -}}
    {{- "false" | quote -}}
{{- end -}}
{{- end -}}

{{/*
Return the Redis&reg; hostname
*/}}
{{- define "eocatalogue.redisHost" -}}
{{- if .Values.redis.enabled }}
    {{- printf "%s-master" (include "eocatalogue.redis.fullname" .) -}}
{{- else -}}
    {{- required "If the redis dependency is disabled you need to add an external redis host" .Values.externalRedis.host -}}
{{- end -}}
{{- end -}}

{{/*
Return the Redis&reg; port
*/}}
{{- define "eocatalogue.redisPort" -}}
{{- if .Values.redis.enabled }}
    {{- .Values.redis.service.port -}}
{{- else -}}
    {{- .Values.externalRedis.port -}}
{{- end -}}
{{- end -}}

{{/*
Get the client secret for the STAC API OpenID Connect authentication.
*/}}
{{- define "eocatalogue.stac.clientSecretName" -}}
{{- if .Values.stac.oidc.existingSecret.name }}
    {{- printf "%s" (tpl .Values.stac.oidc.existingSecret.name $) -}}
{{- else -}}
    {{- printf "%s-oidc" (include "eocatalogue.stac" .) -}}
{{- end -}}
{{- end -}}

{{/*
Get the client secret key for the STAC API OpenID Connect authentication.
*/}}
{{- define "eocatalogue.stac.clientSecretKey" -}}
{{- if .Values.stac.oidc.existingSecret.key }}
    {{- printf "%s" (tpl .Values.stac.oidc.existingSecret.key $) -}}
{{- else -}}
    {{- "client-secret" -}}
{{- end -}}
{{- end -}}


{{/* Validate values of EO API - database */}}
{{- define "eocatalogue.validateValues.database" -}}
{{- if and (not .Values.postgresql.enabled) (not .Values.externalDatabase.host) (and (not .Values.externalDatabase.password) (not .Values.externalDatabase.existingSecret)) -}}
eocatalogue: database
    You disabled the PostgreSQL sub-chart but did not specify an external PostgreSQL host.
    Either deploy the PostgreSQL sub-chart (--set postgresql.enabled=true),
    or set a value for the external database host (--set externalDatabase.host=FOO)
    and set a value for the external database password (--set externalDatabase.password=BAR)
    or existing secret (--set externalDatabase.existingSecret=BAR).
{{- end -}}
{{- end -}}

{{/*
Validate Redis config
*/}}
{{- define "eocatalogue.validateValues.redis" -}}
{{- if and .Values.redis.enabled .Values.redis.auth.existingSecret }}
    {{- if not .Values.redis.auth.existingSecretPasswordKey -}}
EO Catalog: You need to provide existingSecretPasswordKey when an existingSecret is specified in redis dependency
    {{- end -}}
{{- else if and (not .Values.redis.enabled) .Values.externalRedis.existingSecret }}
    {{- if not .Values.externalRedis.existingSecretPasswordKey -}}
EO Catalog: You need to provide existingSecretPasswordKey when an existingSecret is specified in redis
    {{- end }}
{{- end -}}
{{- end -}}

{{/*
Validate external Redis config
*/}}
{{- define "eocatalogue.validateValues.externalRedis" -}}
{{- if not .Values.redis.enabled -}}
EO Catalog: If the redis dependency is disabled you need to add an external redis port
{{- end -}}
{{- end -}}

{{/*
Compile all warnings into a single message.
*/}}
{{- define "eocatalogue.validateValues" -}}
{{- $messages := list -}}
{{- $messages := append $messages (include "eocatalogue.validateValues.database" .) -}}
{{- $messages := append $messages (include "eocatalogue.validateValues.externalRedis" .) -}}
{{- $messages := append $messages (include "eocatalogue.validateValues.redis" .) -}}
{{- $messages := without $messages "" -}}
{{- $message := join "\n" $messages -}}
{{- end -}}
