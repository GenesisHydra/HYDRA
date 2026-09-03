# __main__.py
"""Entry point for HYDRA ecosystem initialization and CEO execution."""

import os
import sys
import time

# Add the HYDRA root directory to path so we can import src.ceo.service
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.ceo import main as business_main

if __name__ == "__main__":
    try:
        business_main()
    except KeyboardInterrupt:
        print("\n[HYDRA] Shutting down gracefully...")
        sys.exit(0)