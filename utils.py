import asyncio
import time
from functools import wraps

from typing import Dict, List, Any

import os
import random

from typing import List, Optional
import pyperclip as p
from bs4 import BeautifulSoup, Tag
import json
from typing import List, Tuple


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


import pyperclip
from bs4 import BeautifulSoup

def clean_clipboard_html(mode="pretty", keep_attrs=None):
    """
    Cleans clipboard HTML content:
    - If `keep_attrs` is provided (e.g. ["id", "class", "href"]), all other attributes will be removed.
    - Otherwise, only `style` and `d` attributes are removed.
    - Output format based on `mode`: "pretty", "compact", or "ultra".
    """

    # Step 1: Read from clipboard
    html_text = pyperclip.paste()

    # Step 2: Parse with BeautifulSoup
    soup = BeautifulSoup(html_text, "html.parser")

    # Step 3: Remove unwanted attributes
    for tag in soup.find_all():
        if keep_attrs is not None:
            # Keep only attributes in keep_attrs list
            tag.attrs = {k: v for k, v in tag.attrs.items() if k in keep_attrs}
        else:
            # Default: remove style and d
            tag.attrs.pop("style", None)
            tag.attrs.pop("d", None)

    # Step 4: Output formatting
    if mode == "pretty":
        cleaned_html = soup.prettify()
    elif mode == "compact":
        cleaned_html = str(soup)
    elif mode == "ultra":
        for elem in soup.descendants:
            if elem.string and not elem.name:
                elem.replace_with(elem.string.strip())
        cleaned_html = str(soup)
        cleaned_html = cleaned_html.replace('\n', '').replace('\r', '').replace('\t', '')
    else:
        raise ValueError("Invalid mode. Choose from: 'pretty', 'compact', 'ultra'")

    # Step 5: Copy back to clipboard
    pyperclip.copy(cleaned_html)

    return cleaned_html



def find_leaf_paths(tree, current_path=None):
    if current_path is None:
        current_path = []

    paths = []

    for category, subcategories in tree.items():
        new_path = current_path + [category]
        if not subcategories:  # It's a leaf node
            paths.append("/".join(new_path))
        else:
            # Recurse into subcategories
            paths.extend(find_leaf_paths(subcategories, new_path))

    return paths



def extract_category_paths(soup: BeautifulSoup) -> List[List[dict]]:
    """
    Parses HTML and returns a list of paths (each path is a list of dicts with 'name' and 'url'),
    following nested <ul class="cate1-group"><li><a>...</a><ul>...</ul></li> structure.
    """
    root_ul: Optional[Tag] = soup.find('ul', class_='cate1-group')
    result_paths: List[List[dict]] = []

    def walk_list_items(node: Tag, path: List[dict]) -> None:
        for li in node.find_all('li', recursive=False):
            anchor = li.find('a')
            if anchor:
                name: str = anchor.get_text(strip=True)
                url: str = anchor.get('href', '').strip()
                new_node = {"name": name, "url": url}
                new_path = path + [new_node]

                sub_ul = li.find('ul')
                if sub_ul:
                    walk_list_items(sub_ul, new_path)
                else:
                    result_paths.append(new_path)

    if root_ul:
        walk_list_items(root_ul, [])

    return result_paths




def save_log(content: str, prefix: str = "LOG-", folder: str = ".") -> str:
    """
    Saves the given content to a file in the specified folder.
    The filename is generated using the prefix and a random number between 100 and 999.

    Args:
        content (str): The content to write to the file.
        prefix (str): The prefix for the filename. Default is 'LOG-'.
        folder (str): The folder to save the file in. Default is current folder.

    Returns:
        str: The full path to the saved file.
    """
    random_num = random.randint(100, 999)
    filename = f"{prefix}{random_num}.txt"
    file_path = os.path.join(folder, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return file_path




def load_name_url_tuples(filename: str) -> List[Tuple[str, str]]:
    """
    Loads JSON data from the given file and converts it into a list of (name, url) tuples.

    Args:
        filename (str): Path to the JSON file.

    Returns:
        List[Tuple[str, str]]: A list of (name, url) tuples.
    """
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return [(item['name'], item['url']) for item in data]




class TaskTracker:
    def __init__(self, tasks: List[Dict], id_key: str = "id", progress_file: str = "done.json"):
        self.tasks = tasks
        self.id_key = id_key
        self.progress_file = progress_file
        self.done_ids = self._load_done_ids()

    def _load_done_ids(self) -> set:
        try:
            with open(self.progress_file, 'r') as f:
                return set(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            return set()

    def _save_done_ids(self):
        with open(self.progress_file, 'w') as f:
            json.dump(list(self.done_ids), f, indent=2)

    def is_done(self, task: Dict) -> bool:
        return task[self.id_key] in self.done_ids

    def mark_done(self, task: Dict):
        self.done_ids.add(task[self.id_key])
        if self.progress_file != '':
            self._save_done_ids()
            print(f"Task: {task}\n Marked Done.")
        else:
            print(f"Task: {task}\n done, but skipped marking.")

    def get_pending_tasks(self) -> List[Dict]:
        return [task for task in self.tasks if not self.is_done(task)]

    def reset(self):
        """Clear all tracking and start fresh (optional)."""
        self.done_ids = set()
        self._save_done_ids()
