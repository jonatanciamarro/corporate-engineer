"""
Executable module entry point for python -m corporate_engineer.cli.
"""

from __future__ import annotations

import sys

from corporate_engineer.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
