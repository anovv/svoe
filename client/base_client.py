import logging

INTERNAL_BASE_URL = 'http://apiserver-svc.apiserver:1228'

log = logging.getLogger(__name__)

# for OpenAPI client codegen:
# https://github.com/openapi-generators/openapi-python-client


class BaseClient:

    def __init__(self, base_url: str = INTERNAL_BASE_URL):
        self.base_url = base_url
