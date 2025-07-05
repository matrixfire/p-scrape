import requests
from typing import Optional, Dict, Any, List


class CJVariantAPIClient:
    BASE_URL = 'https://developers.cjdropshipping.com/api2.0/v1/product/variant/query'

    def __init__(self, access_token: str):
        self.access_token = access_token

    def _build_headers(self) -> Dict[str, str]:
        """Construct the request headers."""
        return {
            'CJ-Access-Token': self.access_token
        }

    def query_variants(self,
                       pid: Optional[str] = None,
                       product_sku: Optional[str] = None,
                       variant_sku: Optional[str] = None,
                       country_code: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Query product variants by product ID, product SKU, or variant SKU.
        At least one of the three must be provided.
        """
        params = {}
        if pid:
            params['pid'] = pid
        elif product_sku:
            params['productSku'] = product_sku
        elif variant_sku:
            params['variantSku'] = variant_sku
        else:
            raise ValueError("You must provide one of: pid, product_sku, or variant_sku")

        if country_code:
            params['countryCode'] = country_code

        try:
            response = requests.get(self.BASE_URL, params=params, headers=self._build_headers())
            response.raise_for_status()
            return self._parse_response(response.json())
        except requests.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None

    def _parse_response(self, data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Parse and handle the API response."""
        if data.get('code') == 200 and data.get('result') is True:
            variants = data['data']
            print(f"✅ Query successful. {len(variants)} variants found:")
            for variant in variants:
                sku = variant.get('variantSku')
                price = variant.get('variantSellPrice')
                print(f"- SKU: {sku}, Price: ${price}")
            return variants
        else:
            print(f"❌ Query failed: {data.get('message')}")
            return None


# ✅ Example usage
if __name__ == "__main__":
    # ACCESS_TOKEN = 'your_access_token_here'
    ACCESS_TOKEN = '''API@CJ4234984@CJ:eyJhbGciOiJIUzI1NiJ9.[V]eyJqdGkiOiIyNTQ0MyIsInVR5cGUiOiJBQ0NFU1NfVE9LRU4iLCJzdWIiOiJicUxvYnFRMGxtTm55UXB4UFdMWnlvcUdKLzBVMERKKzBjVTFOTXhjTDQydWdXN3lmK0NvUEJ6Y3poL0JBc2hwa0R2eUVOSWx3NlQvekgrQ25kTHY0SlJSNXdENDVQNERoK3RPVFMrS3ZocjlOYkVZOVJEcXRIMy94VE5nbnRmcDdSOW9nTDFHRWpSVVpqYmxlU0lpMWsydFBJc2JOVXM3aHNDei9JVm0wWWlxaTRiMFlZNGR6M091anJ6bHp1QllVRjZ0aTl6aUllS2dFYklYcXc1aDR3dXJsdXhtZ3ROdk45V3FYZkJ6QWlIZkVlaEZCYmhsZ2hZODlnUmlqQVFhWVd0T1Y3bWg3cSt2K1FJbkwrK200WDVIeGI3K3RhcmVjbDZrTjU1c2NqST0iLCJpYXQiOjE3NTE2ODA1MTd9.Ww1wzEI9P9ciKr1zKa8IhwazWm9aJBjj9b8aApYNh1g'''
    PRODUCT_ID = '2507041054341625300'

    client = CJVariantAPIClient(ACCESS_TOKEN)
    variants = client.query_variants(pid=PRODUCT_ID)
