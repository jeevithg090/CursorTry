"""Backwards-compatible entry point: ``python main.py`` == ``bulbul talk``."""

import sys

from fintechagent.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or ["talk"]))
