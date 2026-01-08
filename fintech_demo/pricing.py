import requests

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=ripple&vs_currencies=usd"

def get_xrp_price_coingecko(timeout_s: float = 10.0) -> float | None:
    """Fetch XRP/USD price from CoinGecko. Returns float or None."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
        }
        resp = requests.get(COINGECKO_URL, headers=headers, timeout=timeout_s)
        resp.raise_for_status()
        data = resp.json()
        return float(data["ripple"]["usd"])
    except Exception:
        return None
