# utils/async_utils.py
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

_executor = ThreadPoolExecutor(max_workers=2)
_lock = Lock()


def run_async(func, *args, **kwargs):
    with _lock:
        future = _executor.submit(func, *args, **kwargs)
        return future
