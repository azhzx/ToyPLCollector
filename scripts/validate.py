#!/usr/bin/env python3
"""Validate every language entry in ``collections/*.toml``.

Run locally::

    python3 scripts/validate.py           # lint collections/*.toml

On GitHub Actions, errors are also emitted as workflow annotations
(``::error file=...``) so they show up inline in the PR diff.
Network reachability failures are *warnings only* so flaky hosts can
never block a merge.

Exit code: 0 = all good (warnings ok), 1 = at least one error.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import plc


def head_ok(url: str, timeout: float = 8.0) -> bool:
    """HEAD-check a URL.  Any failure (client, server, network) -> False."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "ToyPLCollector-CI/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError):
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dir",
        default=str(plc.COLLECTIONS_DIR),
        help="directory to scan (default: collections/)",
    )
    parser.add_argument("--no-network", action="store_true", help="skip URL reachability checks")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    coll_dir = Path(args.dir)
    files = sorted(coll_dir.glob("*.toml"))
    report: list[dict] = []
    names: dict[str, str] = {}
    today = date.today()

    if not files:
        err = f"no .toml found under {coll_dir}"
        if not args.json:
            print(f"::error::{err}")
            print(f"error: {err}")
        return 1

    for path in files:
        entry: dict = {"file": str(path), "errors": [], "warnings": []}
        lang, load_err = plc.load_language(path)
        if lang is None:
            entry["errors"].append(load_err)
        else:
            errors, warnings = plc.lint_language(path, lang)
            entry["errors"], entry["warnings"] = errors, warnings

            if errors:
                pass  # don't touch the network for a file that already failed
            else:
                name = lang["name"]
                if name in names:
                    entry["errors"].append(
                        f"duplicate language name '{name}' already used by {names[name]}"
                    )
                names[name] = str(path)

                if not args.no_network:
                    # data: logo URLs are skipped by the https filter below
                    for field in plc.URL_FIELDS + ("logo",):
                        url = lang.get(field)
                        if isinstance(url, str) and url.startswith("https://"):
                            if not head_ok(url):
                                entry["warnings"].append(
                                    f"{field} URL could not be reached (checked as a warning only, do not block merging): {url}"
                                )

        report.append(entry)

    error_count = sum(len(e["errors"]) for e in report)
    warn_count = sum(len(e["warnings"]) for e in report)

    if args.json:
        print(json.dumps({"files": report, "errors": error_count, "warnings": warn_count}, indent=2))
        return 1 if error_count else 0

    for entry in report:
        for msg in entry["errors"]:
            print(f"::error file={entry['file']},title=Validation error::{msg}")
            print(f"ERROR  {entry['file']}: {msg}")
        for msg in entry["warnings"]:
            print(f"::warning file={entry['file']},title=Validation warning::{msg}")
            print(f"WARN   {entry['file']}: {msg}")

    print(f"checked {len(report)} file(s): {error_count} error(s), {warn_count} warning(s) [{today.isoformat()}]")
    return 1 if error_count else 0


if __name__ == "__main__":
    sys.exit(main())
