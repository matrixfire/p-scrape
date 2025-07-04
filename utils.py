import asyncio
import time
from functools import wraps


def async_timed(func):
    """
    Decorator to time the execution of an asynchronous function.
    Prints the start and end messages with the time taken.
    """
    @wraps(func)
    async def wrapped(*args, **kwargs):
        print(f'开始执行{func}，参数为：{args}, {kwargs}')
        start = time.time()
        try:
            return await func(*args, **kwargs)
        finally:
            end = time.time()
            total = end - start
            print(f'结束执行{func}，耗时：{total:.4f}秒')
    return wrapped

def sync_timed(func):
    """
    Decorator to time the execution of a synchronous function.
    Prints the start and end messages with the time taken.
    """
    @wraps(func)
    def wrapped(*args, **kwargs):
        print(f'开始执行{func}，参数为：{args}, {kwargs}')
        start = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            end = time.time()
            total = end - start
            print(f'结束执行{func}，耗时：{total:.4f}秒')
    return wrapped


from typing import Dict, List, Any

def flatten_dict(input_dict: Dict[str, Any], list_field: str) -> List[Dict[str, Any]]:
    """
    Transforms a dict with a list of dicts under `list_field`
    into a list of flattened dicts, copying all other top-level fields.
    """
    top_level_fields = {k: v for k, v in input_dict.items() if k != list_field}
    return [
        {**top_level_fields, **item}
        for item in input_dict.get(list_field, [])
    ]
