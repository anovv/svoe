import threading
import time
from typing import Optional, Dict, Tuple, Any, Callable, Type

import requests
import yaml
from pydantic import BaseModel
from ray.train.predictor import Predictor
from ray.train.xgboost import XGBoostPredictor

from backtester.clock import Clock

SERVE_LOCAL_URL = 'http://127.0.0.1:8000'


class InferenceConfig(BaseModel):
    deployment_name: str
    model_uri: str
    predictor_class_name: str
    num_replicas: int

    def predictor_class(self) -> Type[Predictor]:
        if self.predictor_class_name == 'XGBoostPredictor':
            return XGBoostPredictor
        else:
            raise ValueError(f'Unsupported predictor class: {self.predictor_class_name}')

    def load_config(cls, path: str) -> 'InferenceConfig':
        with open(path, 'r') as stream:
            d = yaml.safe_load(stream)
            return InferenceConfig.parse_obj(d)


class InferenceLoop:
    def __init__(self, input_values_provider_callable: Callable, inference_config: Optional[InferenceConfig] = None, clock: Optional[Clock] = None):
        self.clock = clock
        self.serve_deployment_name = inference_config.deployment_name
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
        t = time.time()
        while self.latest_inference_result is None:
            thresh_s = 5
            if time.time() - t > thresh_s:
                raise RuntimeError(f'No inference results after {thresh_s}s')
            time.sleep(1)
        print('Inference loop started')

    def _loop(self):
        while self.is_running:
            self.latest_inference_result = self._make_request()
            self.latest_inference_ts = time.time() if self.clock is None else self.clock.now # TODO for backtest this should use backtester's clock
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
