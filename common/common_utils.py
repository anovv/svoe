import base64
import json
from typing import Dict


def flatten_tuples(data):
    if isinstance(data, tuple):
        if len(data) == 0:
            return ()
        else:
            return flatten_tuples(data[0]) + flatten_tuples(data[1:])
    else:
        return (data,)


def base64_encode(conf: Dict) -> str:
    conf_encoded = base64.urlsafe_b64encode(json.dumps(conf).encode()).decode()
    return conf_encoded


def base64_decode(conf_encoded: str) -> Dict:
    conf = json.loads(base64.urlsafe_b64decode(conf_encoded.encode()).decode())
    return conf
