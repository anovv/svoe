{{- define "data-feed.data-feed-service" }}
apiVersion: v1
kind: Service
metadata:
  labels:
    monitored: all
    name: {{ .name }}-svc
  name: {{ .name }}-svc
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
    name: {{ .name }}-ss
{{- end }}
{{- define "data-feed.data-feed-stateful-set" }}
# TODO startup probe and port
# TODO expose prometheus metrics port on dataFeed container
apiVersion: apps/v1
kind: StatefulSet
metadata:
  labels:
    name: {{ .name }}-ss
  name: {{ .name }}-ss
spec:
  replicas: 1
  selector:
    matchLabels:
      name: {{ .name }}-ss
  serviceName: {{ .name }}-svc
  template:
    metadata:
      labels:
        name: {{ .name }}-ss
        {{- range $k, $v := .labels }}
        {{ $k }}: {{ $v }}
        {{- end }}
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
        - mountPath: {{ .dataFeed.configVolumeMountPath }}
          name: {{ .name }}-conf-vol
        envFrom:
          - secretRef:
              name: data-feed-common-secret
        livenessProbe:
          httpGet:
            path: {{ .dataFeed.healthPath }}
            port: {{ .dataFeed.healthPort }}
          initialDelaySeconds: 5
          periodSeconds: 5
      terminationGracePeriodSeconds: 30
      volumes:
      - configMap:
          defaultMode: 365
          name: {{ .name }}-cm
        name: {{ .name }}-conf-vol
{{- end }}
{{- define "data-feed.data-feed-config-map" }}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .name }}-cm
data:
  data-feed-config.yaml: |
  {{- .dataFeed.config | nindent 4 }}
{{- end }}