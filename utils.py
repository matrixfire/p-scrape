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



from typing import List, Optional
import pyperclip as p
from bs4 import BeautifulSoup, Tag

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



import os
import random

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








# Example usage
if __name__ == "__main__":
    html = p.paste()
    soup = BeautifulSoup(html, "html.parser")
    paths = extract_category_paths(soup)

    # Display extracted paths
    for path in paths:
        # print(" > ".join(str(node.url) for node in path))
        print(f'{path[-1]}, {path[-1]}')



# Example usage:
if __name__ == "__main__":
    # Keep only specific attributes, remove all others
    attrs_to_keep = ["id", "class", "href"]
    result = clean_clipboard_html(mode="ultra", keep_attrs=attrs_to_keep)
    print("Cleaned HTML has been copied back to the clipboard.")
    print(result)



 