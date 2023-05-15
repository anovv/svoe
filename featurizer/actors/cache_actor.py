from typing import Dict, Optional, Tuple, Any

import ray
from intervaltree import Interval
from ray import ObjectRef

CACHE_ACTOR_NAME = 'CacheActor'


@ray.remote
class CacheActor:
    def __init__(self, cache: Dict[str, Dict[Interval, Tuple[int, Optional[ObjectRef]]]]):
        self.cache = cache

    def check_cache(self, context: Dict[str, Any]) -> Tuple[Optional[ObjectRef], bool]:
        feature_key = context['feature_key']
        interval = context['interval']
        obj_ref = None
        ref_counter = 1
        if feature_key in self.cache and interval in self.cache[feature_key]:
            ref_counter, obj_ref = self.cache[feature_key][interval]
            if ref_counter == 1:
                # release obj_ref so it can be GCed
                del self.cache[feature_key][interval]
            else:
                # decrease ref counter
                self.cache[feature_key][interval] = (ref_counter - 1, obj_ref)

        should_cache = ref_counter > 1 # only use Plasma Store as cache if this block is referenced by more than 1 feature
        return obj_ref, should_cache

    def cache_obj_ref(self, obj_ref: ObjectRef, context: Dict[str, Any]):
        feature_key = context['feature_key']
        interval = context['interval']
        if feature_key in self.cache and interval in self.cache[feature_key]:
            ref_counter, _ = self.cache[feature_key][interval]
            self.cache[feature_key][interval] = (ref_counter, obj_ref)
        else:
            raise ValueError(f'Unable to locate cache key for {feature_key} {interval}')





