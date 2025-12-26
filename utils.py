import os
import sys

def clamp(x, lo, hi):
    # keep number within range
    return max(lo, min(hi, x))

def resource_path(relative_path):
    # Get absolute path for PyInstaller or normal execution.
    if hasattr(sys, "_MEIPASS"):  # PyInstaller temporary folder
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Use this for assets
ASSET_DIR = resource_path("assets")
PIECE_DIR = resource_path("assets/pieces")