from typing import Dict, Optional, Tuple, Any, List

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
                # if obj_ref is not None:
                #     del self.cache[feature_key][interval]
                # TODO figure out cache invalidation
                pass
            else:
                # decrease ref counter
                self.cache[feature_key][interval] = (ref_counter - 1, obj_ref)

        # use Plasma Store as cache only if this block is referenced by more than 1 feature
        should_cache = ref_counter > 1 and obj_ref is None
        return obj_ref, should_cache

    def cache_obj_ref(self, obj_ref_list: List[ObjectRef], context: Dict[str, Any]):
        feature_key = context['feature_key']
        interval = context['interval']
        if feature_key in self.cache and interval in self.cache[feature_key]:
            ref_counter, _ = self.cache[feature_key][interval]
            self.cache[feature_key][interval] = (ref_counter, obj_ref_list[0])
        else:
            raise ValueError(f'Unable to locate cache key for {feature_key} {interval}')

    def get_cache(self):
        return self.cache

