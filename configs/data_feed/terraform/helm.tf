provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

locals {
  finalizers = ["kubernetes.io/pvc-protection"]
  accessModes = ["ReadWriteOnce"]
}

resource "helm_release" "prometheus" {
  name       = "prometheus"
  namespace  = "monitoring"
  create_namespace = true
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"

  // make sure serviceMonitorSelector sees all namespaces
  set {
    name  = "kubelet.serviceMonitor.https"
    value = true
  }

  set {
    name  = "prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues"
    value = false
  }

  // Prometheus persistence
  // https://stackoverflow.com/questions/56391693/how-to-enable-persistence-in-helm-prometheus-operator
  set {
    name = "prometheus.server.persistentVolume.enabled"
    value = true
  }

  set {
    name = "prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.accessModes"
    value = "{${join(",", local.accessModes)}}"
  }

  set {
    name = "prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage"
    value = "10Gi"
  }

  // Grafana persistence
  //  https://github.com/prometheus-community/helm-charts/issues/436
  set {
    name = "grafana.enabled"
    value = true
  }

  set {
    name = "grafana.persistence.enabled"
    value = true
  }

  set {
    name = "grafana.persistence.type"
    value = "pvc"
  }

  set {
    name = "grafana.persistence.storageClassName"
    value = "default"
  }

  set {
    name = "grafana.persistence.accessModes"
    value = "{${join(",", local.accessModes)}}"
  }

  set {
    name = "grafana.persistence.size"
    value = "4Gi"
  }

  set {
    name = "grafana.persistence.finalizers"
    value = "{${join(",", local.finalizers)}}"
  }
}