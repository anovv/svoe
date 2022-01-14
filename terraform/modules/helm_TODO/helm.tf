provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

locals {
  // Prometheus // TODO make similar to metrics values
  finalizers = ["kubernetes.io/pvc-protection"]
  accessModes = ["ReadWriteOnce"]

  // Metrics server
  metrics-server-values = {
    // make sure it runs on master
    tolerations = [
      {
        effect = "NoSchedule",
        key = "node-role.kubernetes.io/master",
      }
    ]
    nodeSelector = {
      "node-role.kubernetes.io/master" = ""
    }
  }

  // Dask
  dask-values = {
    "scheduler.tolerations" = [
      {
        effect = "NoSchedule",
        key = "dedicated",
        operator = "Equal",
        value = "dask",
      }
    ]
    "worker.tolerations" = [
      {
        effect = "NoSchedule",
        key = "dedicated",
        operator = "Equal",
        value = "dask",
      }
    ]

    "scheduler.nodeSelector" = {
      dedicated = "dask"
    }
    "worker.nodeSelector" = {
      dedicated = "dask"
    }

    "jupyter.enabled" = false

    "scheduler.serviceType" = "LoadBalancer"
  }
}

resource "helm_release" "metrics-server" {
  name       = "metrics-server"
  namespace  = "kube-system"
  create_namespace = false
  repository = "https://charts.bitnami.com/bitnami"
  chart      = "metrics-server"

  values = [
    yamlencode(local.metrics-server-values)
  ]
}

resource "helm_release" "dask" {
  name       = "dask"
  namespace  = "dask"
  create_namespace = true
  repository = "https://helm.dask.org/"
  chart      = "dask"

  values = [
    yamlencode(local.dask-values)
  ]
}

// TODO uncomment when installing prometheus from scratch
//resource "helm_release" "prometheus" {
//  name       = "prometheus"
//  namespace  = "monitoring"
//  create_namespace = true
//  repository = "https://prometheus-community.github.io/helm-charts"
//  chart      = "kube-prometheus-stack"
//
//  // make sure serviceMonitorSelector sees all namespaces
//  set {
//    name  = "kubelet.serviceMonitor.https"
//    value = true
//  }
//
//  set {
//    name  = "prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues"
//    value = false
//  }
//
//  // Prometheus persistence
//  // https://stackoverflow.com/questions/56391693/how-to-enable-persistence-in-helm-prometheus-operator
//  set {
//    name = "prometheus.server.persistentVolume.enabled"
//    value = true
//  }
//
//  set {
//    name = "prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.accessModes"
//    value = "{${join(",", local.accessModes)}}"
//  }
//
//  set {
//    name = "prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage"
//    value = "10Gi"
//  }
//
//  // Grafana persistence
//  //  https://github.com/prometheus-community/helm-charts/issues/436
//  set {
//    name = "grafana.enabled"
//    value = true
//  }
//
//  set {
//    name = "grafana.persistence.enabled"
//    value = true
//  }
//
//  set {
//    name = "grafana.persistence.type"
//    value = "pvc"
//  }
//
//  set {
//    name = "grafana.persistence.storageClassName"
//    value = "default"
//  }
//
//  set {
//    name = "grafana.persistence.accessModes"
//    value = "{${join(",", local.accessModes)}}"
//  }
//
//  set {
//    name = "grafana.persistence.size"
//    value = "4Gi"
//  }
//
//  set {
//    name = "grafana.persistence.finalizers"
//    value = "{${join(",", local.finalizers)}}"
//  }
//}