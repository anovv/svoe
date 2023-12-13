https://aymen-segni.com/index.php/2020/04/19/deploy-kubernetes-aws-k8s-cluster-with-terraform-and-kops/

for certs:

https://stackoverflow.com/questions/46234295/kubectl-unable-to-connect-to-server-x509-certificate-signed-by-unknown-authori

openssl.exe s_client -showcerts -connect elb.address:443
Copy paste stuff starting from -----BEGIN CERTIFICATE----- to -----END CERTIFICATE----- (these lines included) into a new text file, say... myCert.crt If there are multiple entries, copy all of them.
put in certificate-authority: myCert.crt

or
cluster:
    remove cert and add
    insecure-skip-tls-verify: true

# Another example
# https://managedkube.com/draft-posts/2018-07-07-how-i-use-kops.html

# TODO fix health check for kube-scheduler
# TODO use port: 10259 and scheme: HTTPS
# TODO or use k8s 1.22.* version
# https://github.com/kubernetes-sigs/kubespray/issues/6506
# https://github.com/kubernetes/kubernetes/pull/93208/files

# TODO for cilium:
# DNS records show up after some time, cilium-operator fails and waits long to restart
# need to ssh and restart cilium-operator pod

# cilium pods labels: k8s-app=cilium 4
# cilium-operator: io.cilium/app 3
# etcd-manager-cilium: k8s-app=etcd-manager-cilium 1
# clustermesh-apiserver: k8s-app=clustermesh-apiserver 2

# python server
# python -m http.server 8000