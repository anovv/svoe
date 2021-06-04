provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

resource "helm_release" "prometheus" {
  name       = "prometheus"
  namespace  = "monitoring"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"

  //  TODO set serviceMonitorSelector
  //  set {
  //    name  = "service.type"
  //    value = "ClusterIP"
  //  }
}