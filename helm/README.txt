# Debug pod:
# kk run -n monitoring -i --tty --rm debug --image=busybox --restart=Never -- sh
#
# Networking debug:
# kk apply -f https://k8s.io/examples/admin/dns/dnsutils.yaml
# Busybox
# kubectl run -i --tty busybox --image=busybox