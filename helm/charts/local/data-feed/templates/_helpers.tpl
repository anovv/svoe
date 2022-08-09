# TODO dummy placeholder pod for spot buffer
{{- define "data-feed.data-feed-service" }}
apiVersion: v1
kind: Service
metadata:
  labels:
    monitored-by: data-feed-servicemonitor
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
      port: 9121
      protocol: TCP
      targetPort: 9121
    - name: df-metrics
      port: {{ .dataFeed.prometheus.metricsPort }}
      protocol: TCP
      targetPort: {{ .dataFeed.prometheus.metricsPort }}
  selector:
    name: {{ .name }}-ss
{{- end }}
{{- define "data-feed.data-feed-stateful-set" }}
apiVersion: apps/v1
kind: StatefulSet
metadata:
  labels:
    name: {{ .name }}-ss
    {{- range $k, $v := .labels }}
    {{ $k }}: {{ $v | quote }}
    {{- end }}
  name: {{ .name }}-ss
spec:
  {{- if .dataFeed.resources }}
  replicas: 1
  {{- else}}
  replicas: 0
  {{- end}}
  selector:
    matchLabels:
      name: {{ .name }}-ss
  serviceName: {{ .name }}-svc
  template:
    metadata:
      labels:
        name: {{ .name }}-ss
        {{- range $k, $v := .labels }}
        {{ $k }}: {{ $v | quote }}
        {{- end }}
    spec:
      {{ if .dataFeed.imagePullSecret }}
      imagePullSecrets:
        - name: {{ .dataFeed.imagePullSecret }}
      {{ end }}
      containers:
        - image: redis:alpine
          name: redis
          ports:
            - containerPort: {{ .redis.port }}
          command: ["/bin/sh", "-c"]
          args:
            - |
              redis-server &
              PID=$!

              stop () {
                echo "Calling stop..."
                while true; do
                  if [ -f "/lifecycle/data-feed-finished" ]; then
                    echo "Data feed container finished."
                    kill $PID
                    break
                  fi
                  sleep 1
                done
              }
              trap stop TERM INT EXIT
              wait $PID
              echo "Exited."
          volumeMounts:
            - name: lifecycle
              mountPath: /lifecycle
          {{- if .dataFeed.resources }}
          {{- if .dataFeed.resources.redis }}
          resources:
            {{- if .dataFeed.resources.redis.requests }}
            requests:
              {{- if .dataFeed.resources.redis.requests.memory }}
              memory: {{ .dataFeed.resources.redis.requests.memory }}
              {{- end }}
              {{- if .dataFeed.resources.redis.requests.cpu }}
              cpu: {{ .dataFeed.resources.redis.requests.cpu }}
              {{- end }}
            {{- end }}
            {{- if .dataFeed.resources.redis.limits }}
            limits:
              {{- if .dataFeed.resources.redis.limits.memory }}
              memory: {{ .dataFeed.resources.redis.limits.memory }}
              {{- end }}
              {{- if .dataFeed.resources.redis.limits.cpu }}
              cpu: {{ .dataFeed.resources.redis.limits.cpu }}
              {{- end }}
            {{- end }}
          {{- end }}
          {{- end }}
        - image: oliver006/redis_exporter:latest
          name: redis-exporter
          ports:
            - containerPort: 9121
              name: redis-metrics
          {{- if .dataFeed.resources }}
          {{- if .dataFeed.resources.redisExporter }}
          resources:
            {{- if .dataFeed.resources.redisExporter.requests }}
            requests:
              {{- if .dataFeed.resources.redisExporter.requests.memory }}
              memory: {{ .dataFeed.resources.redisExporter.requests.memory }}
              {{- end }}
              {{- if .dataFeed.resources.redisExporter.requests.cpu }}
              cpu: {{ .dataFeed.resources.redisExporter.requests.cpu }}
              {{- end }}
            {{- end }}
            {{- if .dataFeed.resources.redisExporter.limits }}
            limits:
              {{- if .dataFeed.resources.redisExporter.limits.memory }}
              memory: {{ .dataFeed.resources.redisExporter.limits.memory }}
              {{- end }}
              {{- if .dataFeed.resources.redisExporter.limits.cpu }}
              cpu: {{ .dataFeed.resources.redisExporter.limits.cpu }}
              {{- end }}
            {{- end }}
          {{- end }}
          {{- end }}
        - image: {{ .dataFeed.image }}
          imagePullPolicy: IfNotPresent
          name: data-feed-container
          command: ["/bin/sh", "-c"]
          args:
            - |
              svoe_data_feed_launch &
              PID=$!
              echo "Waiting for termination..."
              while kill -0 $PID
              do
                sleep 1
              done
              echo "data-feed-container process finished."
              touch /lifecycle/data-feed-finished
              echo "Flagged data-feed-container finished."
          ports:
            - containerPort: {{ .dataFeed.prometheus.metricsPort }}
              name: df-metrics
            - containerPort: {{ .dataFeed.healthPort }}
              name: df-health
          volumeMounts:
            - mountPath: {{ .dataFeed.configVolumeMountPath }}
              name: {{ .name }}-conf-vol
            - mountPath: /lifecycle
              name: lifecycle
          envFrom:
            - secretRef:
                name: data-feed-common-secret
          env:
            - name: PROMETHEUS_MULTIPROC_DIR
              value: {{ .dataFeed.prometheus.multiprocDir }}
             # TODO
            - name: ENV
              value: TESTING

          # TODO configure startup/liveness probes based on environment
          startupProbe:
            initialDelaySeconds: 15
            periodSeconds: 2
            failureThreshold: 60
            httpGet:
              path: {{ .dataFeed.healthPath }}
              port: df-health
          livenessProbe:
            httpGet:
              path: {{ .dataFeed.healthPath }}
              port: df-health
            initialDelaySeconds: 5
            periodSeconds: 2
            failureThreshold: 10
          {{- if .dataFeed.resources }}
          {{- if .dataFeed.resources.dataFeedContainer }}
          resources:
            {{- if .dataFeed.resources.dataFeedContainer.requests }}
            requests:
              {{- if .dataFeed.resources.dataFeedContainer.requests.memory }}
              memory: {{ .dataFeed.resources.dataFeedContainer.requests.memory }}
              {{- end }}
              {{- if .dataFeed.resources.dataFeedContainer.requests.cpu }}
              cpu: {{ .dataFeed.resources.dataFeedContainer.requests.cpu }}
              {{- end }}
            {{- end }}
            {{- if .dataFeed.resources.dataFeedContainer.limits }}
            limits:
              {{- if .dataFeed.resources.dataFeedContainer.limits.memory }}
              memory: {{ .dataFeed.resources.dataFeedContainer.limits.memory }}
              {{- end }}
              {{- if .dataFeed.resources.dataFeedContainer.limits.cpu }}
              cpu: {{ .dataFeed.resources.dataFeedContainer.limits.cpu }}
              {{- end }}
            {{- end }}
          {{- end }}
          {{- end }}
      terminationGracePeriodSeconds: 30
      volumes:
        - configMap:
            defaultMode: 365
            name: {{ .name }}-cm
          name: {{ .name }}-conf-vol
        - name: lifecycle
          emptyDir: {}
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: workload-type
                    operator: In
                    values:
                      - data-feed
                  - key: node-type
                    operator: In
                    values:
                      - spot
      tolerations:
        - key: node-type
          operator: Equal
          value: spot
          effect: NoSchedule
        - key: workload-type
          operator: Equal
          value: data-feed
          effect: NoSchedule
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