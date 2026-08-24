"""
BeeFriendly — one-time API key setup.
Run once:  py save_key.py
Your key is saved to .streamlit/secrets.toml and loaded automatically
on every startup — you will never type it again (locally).
"""

import pathlib

SECRETS = pathlib.Path(__file__).parent / ".streamlit" / "secrets.toml"


def main() -> None:
    import getpass
    print("BeeFriendly setup — save your Gemini API key permanently\n")
    key = getpass.getpass("Paste your Gemini API key (input hidden): ").strip()
    if not key:
        raise SystemExit("No key entered. Get one at https://aistudio.google.com/apikey")

    SECRETS.parent.mkdir(exist_ok=True)
    SECRETS.write_text(f'GEMINI_API_KEY = "{key}"\n', encoding="utf-8")
    print(f"\nSaved to: {SECRETS}")
    print("Done! Start the app with:  streamlit run app.py")


if __name__ == "__main__":
    main()
