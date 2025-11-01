from __future__ import annotations
import os

def main() -> None:
    print("template_pkg demo")
    print("  OPENAI_API_KEY set? ", bool(os.getenv("OPENAI_API_KEY")))
    print("  ANTHROPIC_API_KEY set? ", bool(os.getenv("ANTHROPIC_API_KEY")))
    print("  SNOWFLAKE_ACCOUNT: ", os.getenv("SNOWFLAKE_ACCOUNT"))

if __name__ == "__main__":
    main()
