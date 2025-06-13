# utils/timing.py
import time
from functools import wraps
from resumix.utils.logger import logger


def timeit(name: str = None):
    """
    装饰器：记录函数运行时间到 logger（loguru）

    :param name: 自定义函数名标识（用于日志输出），默认为函数名
    """

    def decorator(func):
        func_name = name or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            logger.info(f"[⏱️ {func_name}] 执行时间: {duration:.4f} 秒")
            return result

        return wrapper

    return decorator
