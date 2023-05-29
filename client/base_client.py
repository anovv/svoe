import logging

INTERNAL_BASE_URL = 'http://apiserver-svc.apiserver:1228'

log = logging.getLogger(__name__)


class BaseClient:

    def __init__(self, base_url: str = INTERNAL_BASE_URL):
        self.base_url = base_url
