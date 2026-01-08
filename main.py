from __future__ import annotations

import os

import gradio as gr
import nest_asyncio

from fintech_demo import create_default_state
from fintech_demo.xrpl_workflows import (
    setup_and_issue,
    execute_trade,
    analyze_and_mint,
    pay_dividends,
)

nest_asyncio.apply()

# Prevent imports from user-site packages (helps avoid ~/Library/Python/... conflicts)
os.environ.setdefault("PYTHONNOUSERSITE", "1")

state = create_default_state(token_code="PYT", token_supply="125")


def ui_setup_and_issue(fees_usd: float):
    # Return generator for streaming logs
    return setup_and_issue(state, fees_usd)


def ui_execute_trade(mode: str, qty: float, price_xrp: float) -> str:
    return execute_trade(state, mode, qty, price_xrp)


def ui_analyze_and_mint(next_fees_usd: float) -> str:
    return analyze_and_mint(state, next_fees_usd)


def ui_pay_dividends(income_usd: float) -> str:
    return pay_dividends(state, income_usd)


with gr.Blocks(title="Student Token Econ", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🎓 XRPL Student Token Simulator")

    with gr.Tab("1️⃣ Setup"):
        fees = gr.Number(label="School Fees (USD)", value=2780)
        btn1 = gr.Button("🚀 Setup & Issue", variant="primary")
        log1 = gr.Textbox(label="Log", lines=12)
        btn1.click(ui_setup_and_issue, inputs=[fees], outputs=log1)

    with gr.Tab("2️⃣ Trade"):
        mode = gr.Radio(
            ["Buyer Wants to Buy (Buyer Posts Order)", "Seller Wants to Sell (Seller Posts Order)"],
            value="Buyer Wants to Buy (Buyer Posts Order)",
            label="Who starts?",
        )
        qty = gr.Number(label="Tokens", value=5)
        price = gr.Number(label="Price (XRP) per token", value=12)
        btn2 = gr.Button("💸 Execute Trade")
        log2 = gr.Textbox(label="Log", lines=12)
        btn2.click(ui_execute_trade, inputs=[mode, qty, price], outputs=log2)

    with gr.Tab("3️⃣ Expansion"):
        fees_next = gr.Number(label="Next Fees (USD)", value=3000)
        btn3 = gr.Button("🏭 Analyze & Mint")
        log3 = gr.Textbox(label="Log", lines=12)
        btn3.click(ui_analyze_and_mint, inputs=[fees_next], outputs=log3)

    with gr.Tab("4️⃣ Dividends"):
        inc = gr.Number(label="Income (USD)", value=500)
        btn4 = gr.Button("💰 Pay Dividends")
        log4 = gr.Textbox(label="Log", lines=12)
        btn4.click(ui_pay_dividends, inputs=[inc], outputs=log4)

if __name__ == "__main__":
    demo.launch(share=True)
