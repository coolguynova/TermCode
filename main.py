#!/usr/bin/env python3
from src.ui.app import TermCodeApp

def main() -> None:
    """Launch the TermCode application."""
    app = TermCodeApp()
    app.run()

if __name__ == "__main__":
    main()