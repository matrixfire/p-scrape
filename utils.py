import asyncio
import time
from functools import wraps

from typing import Dict, List, Any

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



def resolve_currency(input_value: str) -> str:
    """
    Resolves a currency symbol or code to a standardized ISO 4217 currency code (e.g., USD, EUR).

    Args:
        input_value (str): A currency symbol (e.g., "$") or code (e.g., "usd", "USD").

    Returns:
        str: ISO currency code (e.g., USD) or 'Unknown' if unrecognized.
    """
    input_value = input_value.strip().upper()

    # ISO 4217 currency codes
    iso_codes = {
        "USD", "EUR", "GBP", "JPY", "INR", "KRW", "RUB", "TRY", "BRL", "VND",
        "ILS", "THB", "UAH", "NGN", "CAD", "AUD", "NZD", "CHF", "HKD", "SGD"
    }

    # If it's already a valid ISO currency code
    if input_value in iso_codes:
        return input_value

    # Map symbols to ISO currency codes
    symbol_map = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        "₹": "INR",
        "₩": "KRW",
        "₽": "RUB",
        "₺": "TRY",
        "R$": "BRL",
        "₫": "VND",
        "₪": "ILS",
        "฿": "THB",
        "₴": "UAH",
        "₦": "NGN",
        "C$": "CAD",
        "A$": "AUD",
        "NZ$": "NZD",
        "CHF": "CHF",
        "HK$": "HKD",
        "SGD": "SGD",
        "美元": "USD",
    }

    return symbol_map.get(input_value, input_value.upper())