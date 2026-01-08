from __future__ import annotations

import math
import time
from decimal import Decimal

from xrpl.wallet import generate_faucet_wallet

from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.requests import AccountLines
from xrpl.models.transactions import OfferCreate, Payment, TrustSet
from xrpl.transaction import submit_and_wait
from xrpl.utils import xrp_to_drops

from .pricing import get_xrp_price_coingecko
from .state import SimulationState


def setup_and_issue(state: SimulationState, school_fees_usd: float):
    """Step 1: Create wallets, establish trust line, and mint initial token supply.

    This is a generator so Gradio can stream logs.
    """
    log = "⏳ Initializing Simulation...\n"
    yield log

    try:
        xrp_price = get_xrp_price_coingecko() or 0.50
        state.latest_xrp_price = xrp_price
        log += f"✅ Current XRP Price: ${xrp_price}\n"
        yield log

        xrps_needed = math.ceil(float(school_fees_usd) / xrp_price)
        price_per_token = xrps_needed / float(state.token_supply)
        log += f"💰 Funding Needed: {xrps_needed} XRP\n"
        log += f"🏷️ Calculated Initial Price: {price_per_token:.4f} XRP per Token\n\n"
        yield log

        log += "⏳ Generating Wallets (testnet faucet)...\n"
        yield log
        # Faucet calls can be slow; give the UI time to update.
        state.issuer = generate_faucet_wallet(state.client)
        state.seller = generate_faucet_wallet(state.client)
        state.buyer = generate_faucet_wallet(state.client)

        log += (
            "✅ Wallets Ready:\n"
            f"Issuer: {state.issuer.classic_address}\n"
            f"Seller: {state.seller.classic_address}\n"
            f"Buyer:  {state.buyer.classic_address}\n\n"
        )
        yield log

        log += "⏳ Establishing Trust Line (Seller trusts Issuer)...\n"
        yield log
        trust_tx = TrustSet(
            account=state.seller.classic_address,
            limit_amount=IssuedCurrencyAmount(
                currency=state.token_code,
                issuer=state.issuer.classic_address,
                value="1000000000",
            ),
        )
        submit_and_wait(trust_tx, state.client, state.seller)

        log += "⏳ Minting Tokens (Issuer → Seller)...\n"
        yield log
        payment_tx = Payment(
            account=state.issuer.classic_address,
            destination=state.seller.classic_address,
            amount=IssuedCurrencyAmount(
                currency=state.token_code,
                issuer=state.issuer.classic_address,
                value=state.token_supply,
            ),
        )
        submit_and_wait(payment_tx, state.client, state.issuer)

        log += f"✅ SUCCESS: Issued {state.token_supply} {state.token_code} to Seller.\n"
        log += f"➡️ Suggested initial price: {price_per_token:.4f} XRP/token\n"
        return
    except Exception as e:
        yield f"❌ Error: {e}"


def execute_trade(state: SimulationState, trade_mode: str, qty: float, price_per_token_xrp: float) -> str:
    """Step 2: Execute a trade between Buyer and Seller via OfferCreate."""
    state.last_trade_tx = None
    if not state.seller or not state.issuer or not state.buyer:
        return "❌ Error: Run Step 1 first."

    log = ""
    try:
        qty_dec = Decimal(str(qty))
        p_dec = Decimal(str(price_per_token_xrp))
        total_price = qty_dec * p_dec
        log += f"📝 Order: {qty_dec} tokens @ {p_dec} XRP = {total_price} Total XRP\n"
        log += f"🔄 Mode: {trade_mode}\n\n"

        # Ensure buyer has trust line so they can hold the token
        log += "0️⃣ Ensuring Buyer trust line exists...\n"
        submit_and_wait(
            TrustSet(
                account=state.buyer.classic_address,
                limit_amount=IssuedCurrencyAmount(
                    currency=state.token_code,
                    issuer=state.issuer.classic_address,
                    value="1000000000",
                ),
            ),
            state.client,
            state.buyer,
        )

        current_tx = None

        if trade_mode == "Buyer Wants to Buy (Buyer Posts Order)":
            # 1) Buyer posts BUY offer (maker)
            log += "1️⃣ Buyer posting BUY offer...\n"
            submit_and_wait(
                OfferCreate(
                    account=state.buyer.classic_address,
                    # Buyer is offering XRP...
                    taker_gets=xrp_to_drops(total_price),
                    # ...in exchange for tokens.
                    taker_pays={
                        "currency": state.token_code,
                        "issuer": state.issuer.classic_address,
                        "value": str(qty_dec),
                    },
                ),
                state.client,
                state.buyer,
            )

            log += "   (Waiting 4s for ledger propagation...)\n"
            time.sleep(4)

            # 2) Seller fills (taker): ask slightly LESS XRP to improve matching odds
            aggressive_price = total_price * Decimal("0.99")
            log += f"2️⃣ Seller filling order (asking {aggressive_price} XRP to ensure match)...\n"
            current_tx = submit_and_wait(
                OfferCreate(
                    account=state.seller.classic_address,
                    taker_gets={
                        "currency": state.token_code,
                        "issuer": state.issuer.classic_address,
                        "value": str(qty_dec),
                    },
                    taker_pays=xrp_to_drops(aggressive_price),
                ),
                state.client,
                state.seller,
            )

        else:
            # Seller posts SELL offer (maker)
            log += "1️⃣ Seller posting SELL offer...\n"
            submit_and_wait(
                OfferCreate(
                    account=state.seller.classic_address,
                    taker_gets={
                        "currency": state.token_code,
                        "issuer": state.issuer.classic_address,
                        "value": str(qty_dec),
                    },
                    taker_pays=xrp_to_drops(total_price),
                ),
                state.client,
                state.seller,
            )

            log += "   (Waiting 4s for ledger propagation...)\n"
            time.sleep(4)

            # Buyer fills (taker): pay slightly MORE XRP to improve matching odds
            aggressive_price = total_price * Decimal("1.01")
            log += f"2️⃣ Buyer filling order (paying {aggressive_price} XRP to ensure match)...\n"
            current_tx = submit_and_wait(
                OfferCreate(
                    account=state.buyer.classic_address,
                    taker_gets=xrp_to_drops(aggressive_price),
                    taker_pays={
                        "currency": state.token_code,
                        "issuer": state.issuer.classic_address,
                        "value": str(qty_dec),
                    },
                ),
                state.client,
                state.buyer,
            )

        state.last_trade_tx = current_tx
        result = (current_tx.result.get("meta") or {}).get("TransactionResult")
        log += f"\n✅ Trade submitted!\nStatus: {result}\nHash: {current_tx.result.get('hash')}\n"

        if result != "tesSUCCESS":
            log += "⚠️ WARNING: Trade did not succeed. Step 3 may fail.\n"

        return log

    except Exception as e:
        return f"❌ Error: {e}"


def analyze_and_mint(state: SimulationState, next_semester_fees_usd: float) -> str:
    """Step 3: Analyze the last trade transaction and mint additional tokens."""
    if not state.last_trade_tx:
        return "❌ Error: No trade found. Please run Step 2."
    if not state.issuer or not state.seller or not state.buyer:
        return "❌ Error: Setup first."

    log = "🔍 Analyzing Latest Ledger Entry...\n"

    try:
        current_xrp_price = get_xrp_price_coingecko() or state.latest_xrp_price or 0.50
        log += f"💲 Live XRP Price: ${current_xrp_price}\n"

        tx = state.last_trade_tx
        tx_hash = tx.result.get("hash")
        log += f"📄 Analyzing Tx: {tx_hash}\n"

        meta = tx.result.get("meta") or {}
        affected = meta.get("AffectedNodes") or []

        buyer_addr = state.buyer.classic_address
        token_code = state.token_code

        # Determine who paid the fee (the signer)
        tx_signer = tx.result.get("Account")

        xrp_spent = Decimal("0")
        tokens_moved = Decimal("0")
        fee_drops = Decimal(tx.result.get("Fee", "12"))

        buyer_touched = False

        for node in affected:
            entry = node.get("ModifiedNode") or node.get("CreatedNode") or node.get("DeletedNode")
            if not entry:
                continue

            # Buyer XRP balance change
            if entry.get("LedgerEntryType") == "AccountRoot":
                final = entry.get("FinalFields") or entry.get("NewFields") or {}
                acct = final.get("Account")
                if acct == buyer_addr:
                    buyer_touched = True
                    prev_fields = entry.get("PreviousFields") or {}
                    prev_bal = Decimal(prev_fields.get("Balance", final.get("Balance", "0")))
                    curr_bal = Decimal(final.get("Balance", "0"))
                    diff = prev_bal - curr_bal  # positive => spent
                    if tx_signer == buyer_addr:
                        diff -= fee_drops
                    xrp_spent = diff / Decimal("1000000")

            # Token balance change (RippleState line)
            if entry.get("LedgerEntryType") == "RippleState":
                final = entry.get("FinalFields") or entry.get("NewFields") or {}
                bal = final.get("Balance") or {}
                if bal.get("currency") == token_code:
                    prev_fields = entry.get("PreviousFields") or {}
                    prev_bal = Decimal((prev_fields.get("Balance") or {}).get("value", "0"))
                    curr_bal = Decimal(bal.get("value", "0"))
                    tokens_moved += abs(curr_bal - prev_bal)

        if tokens_moved > 0 and xrp_spent > 0:
            implied_price = xrp_spent / tokens_moved
            log += (
                "✅ Analysis Success:\n"
                f"- Tokens Moved: {tokens_moved}\n"
                f"- XRP Spent:   {xrp_spent}\n"
                f"- Trade Price: {implied_price:.6f} XRP/token\n\n"
            )

            fees_in_xrp = Decimal(str(float(next_semester_fees_usd) / float(current_xrp_price)))
            new_mint = int(math.ceil(float(fees_in_xrp / implied_price)))

            log += f"🏫 Next Fees: ${next_semester_fees_usd} (~{fees_in_xrp:.2f} XRP)\n"
            log += f"🏭 Minting: {fees_in_xrp:.2f} / {implied_price:.6f} = {new_mint} Tokens\n"

            submit_and_wait(
                Payment(
                    account=state.issuer.classic_address,
                    destination=state.seller.classic_address,
                    amount=IssuedCurrencyAmount(
                        currency=state.token_code,
                        issuer=state.issuer.classic_address,
                        value=str(new_mint),
                    ),
                ),
                state.client,
                state.issuer,
            )
            log += f"✅ MINTED {new_mint} TOKENS."
        else:
            log += "⚠️ Could not infer a valid trade from metadata.\n"
            if not buyer_touched:
                log += "   (Buyer account was not modified in this transaction)\n"
            log += f"   (Transaction Result: {meta.get('TransactionResult')})\n"
            log += "   Try running the trade again."

        return log

    except Exception as e:
        return f"❌ Error: {e}"


def pay_dividends(state: SimulationState, income_usd: float) -> str:
    """Step 4: Pay XRP dividends to token holders (based on issuer's trust lines)."""
    if not state.issuer:
        return "❌ Error: Setup first."

    log = "💰 Dividend Run...\n"
    try:
        price = get_xrp_price_coingecko() or 0.50
        income_xrp = Decimal(str(float(income_usd) / float(price)))
        payout_per_token = income_xrp * Decimal("0.0001")  # 0.01% per token (demo heuristic)

        log += f"Income: ${income_usd} (~{income_xrp:.4f} XRP)\n"
        log += f"Payout: {payout_per_token:.8f} XRP/token\n\n"

        lines = state.client.request(
            AccountLines(account=state.issuer.classic_address, ledger_index="validated")
        ).result.get("lines", [])

        count = 0
        for line in lines:
            if line.get("currency") != state.token_code:
                continue

            bal = Decimal(str(line.get("balance", "0")))
            # Issuer sees holders as negative balances
            if bal < 0:
                tokens_held = abs(bal)
                amt_xrp = tokens_held * payout_per_token
                if amt_xrp <= 0:
                    continue
                try:
                    submit_and_wait(
                        Payment(
                            account=state.issuer.classic_address,
                            destination=line["account"],
                            amount=xrp_to_drops(amt_xrp),
                        ),
                        state.client,
                        state.issuer,
                    )
                    log += f"💸 Paid {line['account']}: {amt_xrp:.8f} XRP\n"
                    count += 1
                except Exception:
                    # Keep going; some accounts/lines may be invalid.
                    pass

        log += f"\n✅ Complete. Paid {count} holder(s)."
        return log

    except Exception as e:
        return f"❌ Error: {e}"
