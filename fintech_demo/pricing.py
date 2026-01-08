from __future__ import annotations

import requests


def get_xrp_price_coingecko(timeout_s: float = 10.0) -> float | None:
    """Fetch live XRP/USD price from CoinGecko.

    Returns None if the request fails for any reason.
    """
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "ripple", "vs_currencies": "usd"}
        r = requests.get(url, params=params, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()
        return float(data["ripple"]["usd"])
    except Exception:
        return None
