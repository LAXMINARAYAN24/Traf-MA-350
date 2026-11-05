"""Runs the TRAF-MA command line when the package is started with python -m trafma."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
