#!/usr/bin/env python3
"""
Ferxvis v2.0 - Entry point
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from gui.chat_window import run_gui

if __name__ == "__main__":
    run_gui()
