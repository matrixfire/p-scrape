from typing import Dict, List, Any
import re

def parse_aging(aging_str: str) -> int:
    """Extracts the higher end of the aging string like '3-7' => 7"""
    match = re.findall(r'\d+', aging_str)
    return int(match[-1]) if match else float('inf')

def choose_best_option(options: List[Dict[str, Any]]) -> Dict[str, str]:
    best = None
    best_score = float('inf')

    for opt in options:
        try:
            price = float(opt.get("price", "inf"))
            aging = parse_aging(opt.get("aging", ""))
            score = 0.9 * price + 0.1 * aging
            if score < best_score:
                best_score = score
                best = opt
        except (TypeError, ValueError):
            continue  # Skip invalid entries

    if best:
        return {
            "shipping_method": best.get("logisticName", ""),
            "shipping_fee": best.get("price", ""),
            "delivery_time": best.get("aging", "")
        }
    else:
        return {"shipping_method": "", "shipping_fee": "", "delivery_time": ""}

def extract_shipping_info(
    sku_dict: Dict[str, int],
    freight_data: List[Dict[str, Any]]
) -> Dict[str, Dict[str, str]]:
    # Map freight list into a SKU -> result list dictionary for fast lookup
    sku_to_result = {item["sku"]: item["result"] for item in freight_data if "sku" in item and "result" in item}

    output = {}
    for sku in sku_dict:
        if sku not in sku_to_result:
            output[sku] = {"shipping_method": "", "shipping_fee": "", "delivery_time": ""}
        else:
            options = sku_to_result[sku]
            # Ensure all options are valid dicts
            valid_options = [opt for opt in options if isinstance(opt, dict)]
            output[sku] = choose_best_option(valid_options)

    return output
