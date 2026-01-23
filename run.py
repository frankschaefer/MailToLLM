#!/usr/bin/env python3
"""Simple launcher script for MailToLLM application."""

import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Import and run the app
from mailtollm.ui.app import MailToLLMApp

if __name__ == "__main__":
    app = MailToLLMApp()
    app.mainloop()
