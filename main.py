from fintech_demo.state import default_state
from fintech_demo.ui import build_demo

def main():
    state = default_state()
    demo = build_demo(state)

    # share=True opens a public link; share=False is local only.
    demo.launch(share=True)

if __name__ == "__main__":
    main()
