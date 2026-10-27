{{- define "pa2577.validate" -}}
{{- if or (ne .Values.namespace "pa2577") (ne .Release.Namespace "pa2577") -}}
{{- fail "Render this chart with --namespace pa2577; other namespaces are not supported." -}}
{{- end -}}
{{- if not (or (regexMatch "^[0-9a-f]{40}$" .Values.imageTag) (regexMatch "^v[0-9]+\\.[0-9]+\\.[0-9]+$" .Values.imageTag)) -}}
{{- fail "imageTag must be a fixed vMAJOR.MINOR.PATCH tag or the full 40-character commit SHA verified by CI." -}}
{{- end -}}
{{- range $component := list "tasks" "statistics" -}}
{{- $service := index $.Values $component -}}
{{- if lt (int $service.replicaCount) 1 -}}
{{- fail "Each Flask replicaCount must be at least one." -}}
{{- end -}}
{{- if not (hasPrefix "docker.io/" $service.repository) -}}
{{- fail "Application repositories must be explicit Docker Hub references." -}}
{{- end -}}
{{- end -}}
{{- if or (lt (int .Values.tasks.service.nodePort) 30000) (gt (int .Values.tasks.service.nodePort) 32767) -}}
{{- fail "Tasks nodePort must be in the standard 30000-32767 range; verify availability before deployment." -}}
{{- end -}}
{{- if or (empty .Values.postgresql.existingSecret) (empty .Values.postgresql.adminPasswordKey) (empty .Values.postgresql.tasksPasswordKey) -}}
{{- fail "An existing Secret and both password key names are required." -}}
{{- end -}}
{{- if eq .Values.postgresql.adminPasswordKey .Values.postgresql.tasksPasswordKey -}}
{{- fail "Administrator and Tasks must use separate Secret keys and distinct passwords." -}}
{{- end -}}
{{- if empty .Values.postgresql.persistence.volumeName -}}
{{- fail "Select an explicitly approved dedicated PV; automatic storage provisioning is not configured." -}}
{{- end -}}
{{- end -}}