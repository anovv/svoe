import logging
from typing import Optional, Any

from client.fast_api_client import Client
from client.fast_api_client.models import Resp

INTERNAL_BASE_URL = 'http://apiserver-svc.apiserver:1228'

log = logging.getLogger(__name__)

# for OpenAPI client codegen:
# https://github.com/openapi-generators/openapi-python-client


class BaseClient:

    def __init__(self, base_url: str = INTERNAL_BASE_URL, client: Optional[Client] = None):
        self.base_url = base_url
        if client is None:
            self.client = Client(
                base_url=self.base_url,
                follow_redirects=True,
                raise_on_unexpected_status=True,
                timeout=120,
                verify_ssl=False
            )
        else:
            self.client = client

    def _parse_and_log_error(self, resp: Resp) -> Any:
        if resp.result is None or resp.error is not None:
            print(resp.error) # TODO log properly
            return None
        return resp.result
