from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any

from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet


@dataclass
class SimulationState:
    """Holds all long-lived objects for the demo session."""

    client: JsonRpcClient
    issuer: Optional[Wallet] = None
    seller: Optional[Wallet] = None
    buyer: Optional[Wallet] = None

    token_code: str = "PYT"
    token_supply: str = "125"

    last_trade_tx: Optional[Any] = None  # xrpl.transaction response (SubmitAndWaitResult)
    latest_xrp_price: Optional[float] = None


def create_default_state(
    rpc_url: str = "https://s.altnet.rippletest.net:51234/",
    token_code: str = "PYT",
    token_supply: str = "125",
) -> SimulationState:
    return SimulationState(
        client=JsonRpcClient(rpc_url),
        token_code=token_code,
        token_supply=token_supply,
    )
