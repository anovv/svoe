{{- define "monitoring-extra.thanos-global-service" }}
{{- $clusterId := .}}
apiVersion: v1
kind: Service
metadata:
  name: thanos-global-cluster-{{ $clusterId }}
  annotations:
    io.cilium/global-service: "true"
spec:
  type: ClusterIP
  ports:
    - name: grpc
      protocol: TCP
      port: 10901
      targetPort: grpc
    - name: http
      protocol: TCP
      port: 10902
      targetPort: http
  selector:
    app.kubernetes.io/name: prometheus
    prometheus: kube-prometheus-stack-prometheus
    cluster-id: {{ $clusterId | quote }}
{{- end }}