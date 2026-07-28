"""
Check that the configured Gemini model is actually reachable and usable BEFORE
you kick off a long ingestion. Google is retiring older Gemini models, so a
model that worked last month may now return NOT_FOUND

Usage:
    # Check the model metadata_gen will use (settings.gemini_model_metadata):
    PYTHONPATH=. python scripts/check_llm.py

    # Check a specific model:
    PYTHONPATH=. python scripts/check_llm.py --model gemini-1.5-pro

    # List every model your API key can use for generation:
    PYTHONPATH=. python scripts/check_llm.py --list

Needs GEMINI_API_KEY in your .env (the Gemini Developer API path). Get one at
https://aistudio.google.com/apikey
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts._gcp_logging import describe_google_error, setup_logging

from config.settings import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a Gemini model is available.")
    parser.add_argument("--model", default=None,
                        help="Model id to check (default: settings.gemini_model_metadata).")
    parser.add_argument("--list", action="store_true",
                        help="List all models your key can use for generateContent.")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging.")
    args = parser.parse_args()

    logger = setup_logging(args.verbose)
    model = args.model or settings.gemini_model_metadata

    try:
        import google.generativeai as genai
    except ImportError:
        logger.error("google-generativeai is not installed. Run: pip install -r requirements.txt")
        sys.exit(2)

    api_key = settings.gemini_api_key
    if not api_key:
        logger.error(
            "No GEMINI_API_KEY set (checked .env and the environment). The Gemini "
            "Developer API needs one.\n  Get a key at https://aistudio.google.com/apikey "
            "and add it to .env as GEMINI_API_KEY=..."
        )
        sys.exit(2)
    genai.configure(api_key=api_key)

    try:
        if args.list:
            print("Models your key can use for generateContent:")
            found = False
            for m in genai.list_models():
                if "generateContent" in getattr(m, "supported_generation_methods", []):
                    print(f"  {m.name}")
                    found = True
            if not found:
                print("  (none — check that your key/project has Gemini access)")
            return

        name = model if model.startswith("models/") else f"models/{model}"
        info = genai.get_model(name)
        methods = list(getattr(info, "supported_generation_methods", []))
        usable = "generateContent" in methods

        print(f"Model: {info.name}")
        print(f"  supports generateContent: {usable}")
        if not usable:
            print("  ✗ This model can't be used for metadata generation.")
            print("    Run:  PYTHONPATH=. python scripts/check_llm.py --list   to see usable models,")
            print("    then set GEMINI_MODEL_METADATA in .env to one of them.")
            sys.exit(1)
        print("  ✓ Reachable and usable. Safe to ingest.")
    except Exception as exc:  # noqa: BLE001 — surface any API error with a hint
        logger.error("Could not verify model '%s'.\n%s", model, describe_google_error(exc))
        print("\nTip: run  PYTHONPATH=. python scripts/check_llm.py --list  to see what your key can use.")
        sys.exit(1)


if __name__ == "__main__":
    main()
