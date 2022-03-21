{{- define "data-feed.data-feed-name-prefix" }}
{{- lower (regexReplaceAll "_" .exchange "-") }}-{{ lower .instrumentType }}-quote-{{ lower .quote }}-data-feed
{{- end }}
{{- define "data-feed.data-feed-service" }}
{{- $prefix := include "data-feed.data-feed-name-prefix" . }}
apiVersion: v1
kind: Service
metadata:
  labels:
    monitored: all
    name: {{ $prefix }}-svc
  name: {{ $prefix }}-svc
spec:
  clusterIP: None
  ports:
  - name: redis
    port: {{ .redis.port }}
    protocol: TCP
    targetPort: {{ .redis.port }}
  - name: redis-metrics
    port: {{ .redis.exporterPort }}
    protocol: TCP
    targetPort: {{ .redis.exporterPort }}
  selector:
    name: {{ $prefix }}-ss
{{- end }}
{{- define "data-feed.data-feed-stateful-set" }}
{{- $prefix := include "data-feed.data-feed-name-prefix" . }}
# TODO set terminationGracePeriodSeconds
# TODO namespace
# TODO make one pod per statefulset
apiVersion: apps/v1
kind: StatefulSet
metadata:
  labels:
    name: {{ $prefix }}-ss
  name: {{ $prefix }}-ss
spec:
  replicas: 1
  selector:
    matchLabels:
      name: {{ $prefix }}-ss
  serviceName: {{ $prefix }}-svc
  template:
    metadata:
      labels:
        name: {{ $prefix }}-ss
    spec:
      containers:
      - image: redis:alpine
        name: redis
        ports:
        - containerPort: {{ .redis.port }}
      - image: oliver006/redis_exporter:latest
        name: redis-exporter
        ports:
        - containerPort: {{ .redis.exporterPort }}
          name: redis-metrics
      - image: {{ .dataFeed.image }}
        imagePullPolicy: IfNotPresent
        name: data-feed-container
        volumeMounts:
        - mountPath: {{ .dataFeed.podConfigsVolumeMountPath }}
          name: {{ $prefix }}-conf-vol
        envFrom:
          - secretRef:
              name: data-feed-common-secret
      initContainers:
      - command:
        - {{ .initScript.scriptsVolumeMountPath }}/{{ .initScript.name }}
        image: busybox
        name: data-feed-init-container
        volumeMounts:
        - mountPath: {{ .initScript.scriptsVolumeMountPath }}
          name: {{ $prefix }}-scripts-vol
        - mountPath: {{ .initScript.configsVolumeMountPath }}
          name: {{ $prefix }}-conf-vol
      volumes:
      - configMap:
          defaultMode: 365
          name: {{ $prefix }}-cm
        name: {{ $prefix }}-scripts-vol
      - emptyDir: {}
        name: {{ $prefix }}-conf-vol
{{- end }}
{{- define "data-feed.data-feed-config-map" }}
{{- $prefix := include "data-feed.data-feed-name-prefix" . }}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ $prefix }}-cm
data:
  {{ range $podConfig := .dataFeed.podConfigs }}
  {{- $podConfig.name }}: |
  {{- $podConfig.config | nindent 4 }}
  {{- end }}
  {{ .initScript.name }}: |-
  {{- .initScript.script | nindent 4}}
{{- end }}