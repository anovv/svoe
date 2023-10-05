import threading
import time
from typing import Optional, Dict, Tuple, Any, Callable

import requests

from simulation.data.data_generator import DataStreamEvent

SERVE_LOCAL_URL = 'http://127.0.0.1:8000'


class InferenceLoop:

    def __init__(self, input_values_provider_callable: Callable, inference_config: Optional[Dict] = None):
        self.serve_deployment_name = inference_config['deployment_name']
        self.is_running = False
        self.thread = None
        self.input_values_provider_callable = input_values_provider_callable

        self.inference_results = []
        self.latest_inference_result = None
        self.latest_inference_ts = None

    def run(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.is_running:
            self.latest_inference_result = self._make_request()
            self.latest_inference_ts = time.time()
            self.inference_results.append((self.latest_inference_result, self.latest_inference_ts))
            # TODO add sleep?

    def _make_request(self) -> Optional[Any]:

        # TODO typing?
        feature_values = self.input_values_provider_callable()
        try:
            resp = requests.post(
                url=f'{SERVE_LOCAL_URL}/{self.serve_deployment_name}/',
                json={
                    'array': feature_values
                }
            )
            return resp.json()
        except Exception as e:
            print(f'Unable to make inference request: {e}') # TODO proper handle exceptions
            return None

    def stop(self):
        self.is_running = False
        self.thread.join()

    def get_latest_inference(self) -> Tuple[Any, float]:
        return self.latest_inference_result, self.latest_inference_ts
