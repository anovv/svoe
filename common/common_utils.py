import base64
import json
import os
import sys
from typing import Dict, Any, Callable, Type

import humps


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


class RemoteCodeBase:

    @staticmethod
    def code(*args, **kwargs) -> Any:
        raise NotImplementedError


def get_callable_from_remote_code_file(python_file_path) -> Callable:
    # a/b/c/file.py
    if not os.path.isfile(python_file_path):
        raise ValueError('Not a file')
    p = python_file_path.split('/')
    module_path = python_file_path.removesuffix(p[len(p) - 1])
    module_name = p[len(p) - 1].removesuffix('.py')
    sys.path.append(os.path.abspath(module_path))
    class_name = humps.pascalize(module_name)
    module = __import__(module_name, fromlist=[class_name])
    clazz: Type[RemoteCodeBase] = getattr(module, class_name)
    if not issubclass(clazz, RemoteCodeBase):
        raise ValueError(f'{class_name} should implement RemoteCodeBase')
    return clazz.code
