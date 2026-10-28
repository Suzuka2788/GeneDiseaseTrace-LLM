"""Project entry point for the shared contract validator (implementation in toolkit/validate.py).

Usage: python scripts/validate_contract.py RUN_DIR XML_PATH [--label NAME] [--report PATH]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from toolkit.validate import main

if __name__ == "__main__":
    main()
