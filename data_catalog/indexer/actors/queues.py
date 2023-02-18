from typing import List, Optional, TypeVar, Generic

from ray.util.client import ray

from data_catalog.indexer.models import InputItemBatch, InputItem, IndexItem, IndexItemBatch

# T = TypeVar('T')


# @ray.remote
# class Queue(Generic[T]):
#     q: List[T] = []
#
#     def pop(self) -> Optional[T]:
#         if len(self.q) != 0:
#             return self.q.pop(0)
#         else:
#             return None
#
#     def put(self, item: T):
#         self.q.append(item)

# TODO create mixin for common methods size, put, pop, figure out generics
@ray.remote
class InputQueue:
    q: List[InputItemBatch] = []

    def pop(self) -> Optional[InputItemBatch]:
        if len(self.q) != 0:
            return self.q.pop(0)
        else:
            return None

    def put(self, item: InputItemBatch):
        self.q.append(item)

    def size(self):
        return len(self.q)


@ray.remote
class DownloadQueue:
    q: List[InputItem] = []

    def pop(self) -> Optional[InputItem]:
        if len(self.q) != 0:
            return self.q.pop(0)
        else:
            return None

    def put(self, batch: InputItemBatch):
        self.q.extend(batch)

    def size(self):
        return len(self.q)


@ray.remote
class StoreQueue:
    q: List[IndexItem] = []

    def __init__(self, batch_size: int):
        self.batch_size = batch_size

    def pop_with_wait_if_last(self) -> Optional[IndexItemBatch]:
        if len(self.q) < self.batch_size:
            # TODO check if queue contains last item, if so, wait until notified from outside and pop all
            return None
        else:
            res = self.q[0:self.batch_size]
            self.q = self.q[self.batch_size:]
            return res

    def put(self, item: IndexItem):
        self.q.append(item)

    def size(self):
        return len(self.q)
