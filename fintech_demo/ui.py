import gradio as gr
from functools import partial
from .state import AppState
from .xrpl_workflows import setup_and_issue, execute_trade, analyze_and_mint, pay_dividends

def build_demo(state: AppState) -> gr.Blocks:
    with gr.Blocks(title="Student Token Econ", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🎓 XRPL Student Token Simulator")

        with gr.Tab("1️⃣ Setup"):
            fees = gr.Number(label="School Fees (USD)", value=2780)
            btn1 = gr.Button("🚀 Setup & Issue", variant="primary")
            log1 = gr.Textbox(label="Log", lines=12)
            btn1.click(
                fn=partial(setup_and_issue, state),  # binds state as first arg
                inputs=[fees],
                outputs=[log1],
            )

        with gr.Tab("2️⃣ Trade"):
            mode = gr.Radio(
                ["Buyer Wants to Buy (Buyer Posts Order)", "Seller Wants to Sell (Seller Posts Order)"],
                value="Buyer Wants to Buy (Buyer Posts Order)",
                label="Who Starts?"
            )
            qty = gr.Number(label="Tokens", value=5)
            price = gr.Number(label="Price (XRP) per token", value=12)
            btn2 = gr.Button("💸 Execute Trade")
            log2 = gr.Textbox(label="Log", lines=12)

            btn2.click(lambda m,q,p: execute_trade(state, m, q, p), inputs=[mode, qty, price], outputs=log2)

        with gr.Tab("3️⃣ Expansion"):
            fees_next = gr.Number(label="Next Fees (USD)", value=3000)
            btn3 = gr.Button("🏭 Analyze & Mint")
            log3 = gr.Textbox(label="Log", lines=12)
            btn3.click(lambda x: analyze_and_mint(state, x), inputs=[fees_next], outputs=log3)

        with gr.Tab("4️⃣ Dividends"):
            inc = gr.Number(label="Income (USD)", value=500)
            btn4 = gr.Button("💰 Pay Dividends")
            log4 = gr.Textbox(label="Log", lines=12)
            btn4.click(lambda x: pay_dividends(state, x), inputs=[inc], outputs=log4)

    return demo
