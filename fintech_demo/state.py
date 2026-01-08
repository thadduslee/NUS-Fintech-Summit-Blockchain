from dataclasses import dataclass
from decimal import Decimal
from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet

XRPL_TESTNET_RPC = "https://s.altnet.rippletest.net:51234/"

@dataclass
class AppState:
    client: JsonRpcClient
    issuer: Wallet | None = None
    seller: Wallet | None = None
    buyer: Wallet | None = None
    latest_price_per_token_xrp: Decimal | None = None
    last_trade_total_xrp_intended: Decimal | None = None
    token_code: str = "PYT"
    token_supply: str = "125"

    latest_xrp_price: float | None = None
    last_trade_tx: object | None = None  # submit_and_wait returns a response-like object

def default_state() -> AppState:
    return AppState(client=JsonRpcClient(XRPL_TESTNET_RPC))
