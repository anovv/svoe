
class RayClusterManagerApi:

    def __int__(self, kube_ctx: str):
        self.kube_ctx = kube_ctx

    def build_crd(self, params):
        # TODO load/parse yamls, set params
        return {}

    def launch_cluster(self):
        # TODO call kube api
        return