#!/usr/bin/env python3
"""
HYDRA Business System - Main Entry Point

This script initializes and runs the HYDRA business ecosystem,
creating businesses that generate real income.
"""

import os
import sys
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ceo import main as controller_main

if __name__ == "__main__":
    try:
        # Ensure required directories exist
        os.makedirs("data", exist_ok=True)
        os.makedirs("data/business", exist_ok=True)
        
        print("=" * 70)
        print("HYDRA BUSINESS SYSTEM - MODELO DE PRODUCCIÓN")
        print("=" * 70)
        print(f"Iniciando sistema a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Ejecutar el sistema principal
        controller_main()
        
    except KeyboardInterrupt:
        print("\n" + "=" * 70)
        print("HYDRA: Sistema detenido por el usuario")
        print("=" * 70)
        sys.exit(0)
    except Exception as e:
        print(f"\n" + "=" * 70)
        print(f"ERROR FATAL: {str(e)}")
        print("=" * 70)
        sys.exit(1)
