import math
import time
from decimal import Decimal

from xrpl.wallet import generate_faucet_wallet
from xrpl.models.transactions import TrustSet, Payment, OfferCreate
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.requests import AccountLines
from xrpl.transaction import submit_and_wait
from xrpl.utils import xrp_to_drops

from .pricing import get_xrp_price_coingecko
from .state import AppState

TRUST_LIMIT = "1000000000"

def setup_and_issue(state: AppState, school_fees_usd: float):
    """Generator for Gradio streaming logs."""
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

        log += "⏳ Generating Wallets (faucet)...\n"
        yield log

        state.issuer = generate_faucet_wallet(state.client)
        state.seller = generate_faucet_wallet(state.client)
        state.buyer  = generate_faucet_wallet(state.client)

        log += (
            "✅ Wallets Ready:\n"
            f"Issuer: {state.issuer.classic_address}\n"
            f"Seller: {state.seller.classic_address}\n"
            f"Buyer:  {state.buyer.classic_address}\n\n"
        )
        yield log

        # Seller trusts Issuer
        log += "⏳ Establishing Seller trust line...\n"
        yield log
        trust_tx = TrustSet(
            account=state.seller.classic_address,
            limit_amount=IssuedCurrencyAmount(
                currency=state.token_code,
                issuer=state.issuer.classic_address,
                value=TRUST_LIMIT,
            ),
        )
        submit_and_wait(trust_tx, state.client, state.seller)

        # Issuer sends tokens to Seller
        log += "⏳ Minting tokens to Seller...\n"
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

        log += f"✅ SUCCESS: Issued {state.token_supply} {state.token_code} to Seller."
        yield log

    except Exception as e:
        yield log + f"\n❌ Error: {e}"

def _ensure_buyer_trust(state: AppState):
    buyer_trust = TrustSet(
        account=state.buyer.classic_address,
        limit_amount=IssuedCurrencyAmount(
            currency=state.token_code,
            issuer=state.issuer.classic_address,
            value=TRUST_LIMIT,
        ),
    )
    submit_and_wait(buyer_trust, state.client, state.buyer)

def execute_trade(state: AppState, trade_mode: str, qty: float, price_per_token_xrp: float) -> str:
    """Matches your notebook's 'aggressive matching' logic."""
    state.last_trade_tx = None
    if not (state.issuer and state.seller and state.buyer):
        return "❌ Error: Run Step 1 first."

    try:
        qty = float(qty)
        price_per_token_xrp = float(price_per_token_xrp)
        total_price = qty * price_per_token_xrp

        log = ""
        log += f"📝 Order: {qty} tokens @ {price_per_token_xrp} XRP = {total_price} Total XRP\n"
        log += f"🔄 Mode: {trade_mode}\n\n"

        current_tx = None

        if trade_mode == "Buyer Wants to Buy (Buyer Posts Order)":
            log += "1️⃣ Buyer setting trust line...\n"
            _ensure_buyer_trust(state)

            log += "2️⃣ Buyer posting BUY offer...\n"
            submit_and_wait(
                OfferCreate(
                    account=state.buyer.classic_address,
                    taker_gets=xrp_to_drops(Decimal(str(total_price))),
                    taker_pays={
                        "currency": state.token_code,
                        "issuer": state.issuer.classic_address,
                        "value": str(qty),
                    },
                ),
                state.client,
                state.buyer,
            )

            log += "   (Waiting 5s for ledger propagation...)\n"
            time.sleep(5)

            aggressive_price = total_price * 0.99
            log += f"3️⃣ Seller filling order (Asking {aggressive_price:.2f} XRP to ensure match)...\n"
            current_tx = submit_and_wait(
                OfferCreate(
                    account=state.seller.classic_address,
                    taker_gets={
                        "currency": state.token_code,
                        "issuer": state.issuer.classic_address,
                        "value": str(qty),
                    },
                    taker_pays=xrp_to_drops(Decimal(str(aggressive_price))),
                ),
                state.client,
                state.seller,
            )

        else:
            log += "1️⃣ Seller posting SELL offer...\n"
            submit_and_wait(
                OfferCreate(
                    account=state.seller.classic_address,
                    taker_gets={
                        "currency": state.token_code,
                        "issuer": state.issuer.classic_address,
                        "value": str(qty),
                    },
                    taker_pays=xrp_to_drops(Decimal(str(total_price))),
                ),
                state.client,
                state.seller,
            )

            log += "   (Waiting 5s for ledger propagation...)\n"
            time.sleep(5)

            log += "2️⃣ Buyer setting trust line...\n"
            _ensure_buyer_trust(state)

            aggressive_price = total_price * 1.01
            log += f"3️⃣ Buyer purchasing (Offering {aggressive_price:.2f} XRP to ensure match)...\n"
            current_tx = submit_and_wait(
                OfferCreate(
                    account=state.buyer.classic_address,
                    taker_gets=xrp_to_drops(Decimal(str(aggressive_price))),
                    taker_pays={
                        "currency": state.token_code,
                        "issuer": state.issuer.classic_address,
                        "value": str(qty),
                    },
                ),
                state.client,
                state.buyer,
            )

        state.last_trade_tx = current_tx
        result = current_tx.result.get("meta", {}).get("TransactionResult")
        tx_hash = current_tx.result.get("hash")

        log += f"\n✅ Trade Executed!\nStatus: {result}\nHash: {tx_hash}\n"
        if result != "tesSUCCESS":
            log += "⚠️ WARNING: Trade did not succeed. Step 3 may fail.\n"
        return log

    except Exception as e:
        return f"❌ Error: {e}"
import math
from decimal import Decimal
from xrpl.models.transactions import Payment
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.transaction import submit_and_wait

from .pricing import get_xrp_price_coingecko
from .state import AppState


def analyze_and_mint(state: AppState, next_semester_fees_usd: float) -> str:
    if not state.last_trade_tx:
        return "❌ Error: No trade found. Please run Step 2."
    if not (state.issuer and state.seller and state.buyer):
        return "❌ Error: Setup not complete."

    log = "🔍 Analyzing Latest Ledger Entry...\n"

    try:
        current_xrp_price = get_xrp_price_coingecko() or state.latest_xrp_price or 0.50
        log += f"💲 Live XRP Price: ${current_xrp_price}\n"

        tx = state.last_trade_tx
        tx_hash = tx.result.get("hash")
        log += f"📄 Analyzing Tx: {tx_hash}\n"

        meta = tx.result.get("meta", {})
        affected = meta.get("AffectedNodes", [])
        buyer_addr = state.buyer.classic_address
        issuer_addr = state.issuer.classic_address
        tx_signer = tx.result.get("Account")

        fee_drops = Decimal(tx.result.get("Fee", "12"))
        xrp_spent = Decimal(0)         # XRP
        tokens_delta = Decimal(0)      # tokens (+/- from buyer perspective)

        found_buyer = False
        found_token_line = False

        for node in affected:
            entry = node.get("ModifiedNode") or node.get("CreatedNode")
            if not entry:
                continue

            # ----------------------------
            # Buyer XRP delta (AccountRoot)
            # ----------------------------
            if entry.get("LedgerEntryType") == "AccountRoot":
                ff = entry.get("FinalFields", {})
                if ff.get("Account") != buyer_addr:
                    continue

                found_buyer = True
                pf = entry.get("PreviousFields", {})
                if "Balance" not in pf:
                    # No delta info in this node (common). We'll fallback later if needed.
                    continue

                prev = Decimal(pf["Balance"])          # drops
                curr = Decimal(ff["Balance"])          # drops
                diff_drops = prev - curr               # total drops decreased

                # If buyer is the tx signer, fee is included in their balance delta.
                if tx_signer == buyer_addr:
                    diff_drops -= fee_drops

                # Convert drops -> XRP
                xrp_spent = diff_drops / Decimal("1000000")

            # --------------------------------------------
            # Buyer token delta from the buyer↔issuer line
            # --------------------------------------------
            if entry.get("LedgerEntryType") == "RippleState":
                ff = entry.get("FinalFields", {})
                pf = entry.get("PreviousFields", {})

                bal = ff.get("Balance", {})
                if bal.get("currency") != state.token_code:
                    continue

                low = ff.get("LowLimit", {})
                high = ff.get("HighLimit", {})

                parties = {low.get("issuer"), high.get("issuer")}
                if buyer_addr not in parties or issuer_addr not in parties:
                    continue

                found_token_line = True

                # Previous balance (fallback to current if PreviousFields missing)
                prev_val = Decimal(pf.get("Balance", {}).get("value", bal.get("value", "0")))
                curr_val = Decimal(bal.get("value", "0"))

                # RippleState balance sign depends on whether buyer is LowLimit or HighLimit side
                buyer_is_low = (low.get("issuer") == buyer_addr)

                # Convert RippleState Balance -> buyer holding
                # If buyer is Low: buyer_holding = -Balance
                # If buyer is High: buyer_holding = +Balance
                buyer_prev = -prev_val if buyer_is_low else prev_val
                buyer_curr = -curr_val if buyer_is_low else curr_val

                tokens_delta += (buyer_curr - buyer_prev)

        tokens_moved = abs(tokens_delta)

        # ----------------------------
        # Fallback for XRP spent
        # ----------------------------
        if xrp_spent <= 0:
            intended = getattr(state, "last_trade_total_xrp_intended", None)
            if intended is not None:
                xrp_spent = Decimal(str(intended))
                log += f"ℹ️ XRP delta missing in meta; using intended total XRP: {xrp_spent}\n"
            else:
                log += "⚠️ Could not compute XRP spent from metadata (no AccountRoot delta).\n"
                log += "   Tip: store state.last_trade_total_xrp_intended in Step 2.\n"
                return log

        # ----------------------------
        # Validate tokens moved
        # ----------------------------
        if tokens_moved <= 0:
            log += "⚠️ No tokens moved detected on buyer↔issuer trustline.\n"
            if not found_token_line:
                log += "   (Did not find buyer↔issuer RippleState node in AffectedNodes)\n"
            log += f"   (Transaction Result: {meta.get('TransactionResult')})\n"
            return log

        implied_price = xrp_spent / tokens_moved

        log += (
            "✅ Analysis Success:\n"
            f"- Tokens Moved: {tokens_moved}\n"
            f"- XRP Cost: {xrp_spent}\n"
            f"- Trade Price: {implied_price:.6f} XRP\n\n"
        )

        fees_xrp = Decimal(str(float(next_semester_fees_usd) / current_xrp_price))
        new_mint = math.ceil(float(fees_xrp / implied_price))

        log += f"🏫 Next Fees: ${next_semester_fees_usd} (~{fees_xrp:.2f} XRP)\n"
        log += f"🏭 Minting: {fees_xrp:.2f} / {implied_price:.6f} = {new_mint} Tokens\n"

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
        return log

    except Exception as e:
        return f"❌ Error: {e}"


def pay_dividends(state: AppState, income_usd: float) -> str:
    if not state.issuer:
        return "❌ Error: Setup first."

    log = "💰 Dividend Run...\n"
    try:
        price = get_xrp_price_coingecko() or 0.50
        income_xrp = float(income_usd) / price

        payout_per_token = Decimal(str(income_xrp * 0.0001))  # 0.01%
        log += f"Income: ${income_usd} (~{income_xrp:.2f} XRP)\n"
        log += f"Payout: {payout_per_token:.8f} XRP/token\n"

        lines = state.client.request(
            AccountLines(account=state.issuer.classic_address, ledger_index="validated")
        ).result["lines"]

        count = 0
        for line in lines:
            if line["currency"] != state.token_code:
                continue
            bal = Decimal(line["balance"])
            if bal >= 0:
                continue  # issuer perspective: holders show negative

            user_holding = abs(bal)
            payout = user_holding * payout_per_token
            if payout <= 0:
                continue

            try:
                submit_and_wait(
                    Payment(
                        account=state.issuer.classic_address,
                        destination=line["account"],
                        amount=xrp_to_drops(payout),
                    ),
                    state.client,
                    state.issuer,
                )
                log += f"💸 Paid {line['account']}: {payout:.8f} XRP\n"
                count += 1
            except Exception:
                # keep going like the notebook
                pass

        log += f"✅ Complete. Paid {count} holders."
        return log

    except Exception as e:
        return f"❌ Error: {e}"
