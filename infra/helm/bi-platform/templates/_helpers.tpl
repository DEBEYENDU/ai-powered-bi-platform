{{- define "bi.labels" -}}
app.kubernetes.io/part-of: bi-platform
app.kubernetes.io/managed-by: Helm
{{- end -}}

{{- define "bi.dbUrl" -}}
{{- if .Values.postgresql.enabled -}}
postgresql+psycopg://{{ .Values.postgresql.auth.username }}:{{ .Values.secrets.postgresPassword }}@{{ .Release.Name }}-postgresql:5432/{{ .Values.postgresql.auth.database }}
{{- else -}}
{{ required "External DB: set dbUrlOverride" .Values.dbUrlOverride }}
{{- end -}}
{{- end -}}

{{- define "bi.redisUrl" -}}
{{- if .Values.redis.enabled -}}
redis://{{ .Release.Name }}-redis-master:6379/0
{{- else -}}
{{ required "External Redis: set redisUrlOverride" .Values.redisUrlOverride }}
{{- end -}}
{{- end -}}
