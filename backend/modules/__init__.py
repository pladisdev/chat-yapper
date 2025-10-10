import sys

def is_executable():
    """
    Detect if we're running as a PyInstaller executable.
    Returns True if running from .exe, False if running from source.
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')