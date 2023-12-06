def pod_name_from_ss_name(ss_name):
    # ss example name data-feed-binance-spot-6d1641b134-ss
    # pod name example data-feed-binance-spot-6d1641b134 (remove '-ss')
    return ss_name[:-3]


def ss_name_from_pod_name(pod_name):
    return pod_name + '-ss'


def cm_name_pod_name(pod_name):
    return pod_name + '-cm'


def get_payload_config(payload):
    return payload['payload_config']


def get_payload_hash(payload):
    return payload['payload_hash']