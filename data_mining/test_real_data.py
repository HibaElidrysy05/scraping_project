"""Alias vers run_p2 sqlite (compatibilité scripts existants)."""

import sys

from data_mining.run_p2 import cmd_sqlite

if __name__ == "__main__":
    sys.exit(cmd_sqlite())
