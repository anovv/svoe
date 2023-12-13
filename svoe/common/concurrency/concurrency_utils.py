from typing import Callable, List, Any
import concurrent.futures
import concurrent


def run_concurrently(cs: List[Callable]) -> List[Any]:
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1024)
    futures = [executor.submit(callable) for callable in cs]
    return [f.result() for f in futures]
