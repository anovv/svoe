https://aymen-segni.com/index.php/2020/04/19/deploy-kubernetes-aws-k8s-cluster-with-terraform-and-kops/

Usage (inside kops/ dir)

- Gen cluster.yaml based on template.yaml
$ TF_OUTPUT_JSON=$(cd ../terraform && terraform output -json)
$ (echo $TF_OUTPUT_JSON | yq e -P -) > values.yaml
$ CLUSTER_NAME="$(echo $TF_OUTPUT_JSON | jq -r .cluster_name.value)"

$ kops toolbox template --name ${CLUSTER_NAME} --values values.yaml --template template.yaml --format-yaml > cluster.yaml

- Put kops state in s3

$ STATE="s3://$(echo ${$TF_OUTPUT_JSON} | jq -r .kops_s3_bucket_name.value)"

$ kops replace -f cluster.yaml --state ${STATE} --name ${CLUSTER_NAME} --force

$ kops create secret --name ${CLUSTER_NAME} --state ${STATE} --name ${CLUSTER_NAME} sshpublickey admin -i ~/.ssh/id_rsa.pub

- Create terraform config for cluster

$ kops update cluster \
--out=terraform_out \
--target=terraform \
--state ${STATE} \
--name ${CLUSTER_NAME}

- Apply

$ terraform init
$ terraform plan
$ terraform apply

Suggestions:
 * validate cluster: kops validate cluster --wait 10m
 * list nodes: kubectl get nodes --show-labels
 * ssh to the master: ssh -i ~/.ssh/id_rsa ubuntu@api.apn1.k8s.local
 * the ubuntu user is specific to Ubuntu. If not using Ubuntu please use the appropriate user based on your OS.

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
# DNS records show up after some time, cilium-controller fails and waits long to restart
# need to ssh and restart cilium-controller pod