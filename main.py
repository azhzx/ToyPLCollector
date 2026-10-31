#!/usr/bin/env python3
"""ToyPLCollector — command line entry.

    python3 main.py validate [--no-network]   lint collections/*.toml
    python3 main.py build    [--out _site]    generate the static website

Everything lives in scripts/; this wrapper just dispatches.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

USAGE = """usage:
  python3 main.py validate [--no-network]    lint collections/*.toml
  python3 main.py build    [--out _site]     generate the static website
"""


def main(argv: list[str]) -> int:
    if not argv:
        print(USAGE, end="")
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd in ("validate", "v"):
        import validate  # noqa: PLC0415 (import deferred so paths are ready)

        return validate.main(rest)
    if cmd in ("build", "site", "b"):
        import make_website  # noqa: PLC0415

        return make_website.main(rest)
    print(f"unknown command: {cmd!r}\n{USAGE}", end="")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
