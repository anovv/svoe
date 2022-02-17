{{- define "monitoring-extra.thanos-global-service" }}
apiVersion: v1
kind: Service
metadata:
  name: thanos-global-cluster-{{ .clusterId }}
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
  {{ if not .isObserver }}
  selector:
    app.kubernetes.io/name: prometheus
    prometheus: kube-prometheus-stack-prometheus
  {{ end }}
{{- end }}
{{- define "monitoring-extra.alertmanager-global-service" }}
apiVersion: v1
kind: Service
metadata:
  name: alertmanager-global-cluster-{{ .clusterId }}
  annotations:
    io.cilium/global-service: "true"
spec:
  type: ClusterIP
  ports:
    - name: http-web
      protocol: TCP
      port: 9093
      targetPort: 9093
  {{ if not .isObserver }}
  selector:
    alertmanager: kube-prometheus-stack-alertmanager
    app.kubernetes.io/name: alertmanager
  {{ end }}
{{- end }}
