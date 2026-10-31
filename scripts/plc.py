"""Shared helpers for ToyPLCollector scripts.

One toy language == one TOML file under ``collections/``.  This module knows
the schema: required/optional fields, types, value rules.  Both
``validate.py`` (CI check) and ``make_website.py`` (site generator) import it,
so the two never drift apart.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COLLECTIONS_DIR = REPO_ROOT / "collections"

#: Platforms are a closed set so the website's filter chips stay meaningful.
KNOWN_PLATFORMS = ["Windows", "Linux", "macOS", "Web", "Other"]

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

REQUIRED_FIELDS = ("name", "display_name", "description", "repo", "hello_world")

#: name -> (type, required, description) ; anything unknown triggers a warning
FIELD_TYPES = {
    "name": str,
    "display_name": str,
    "logo": str,
    "description": str,
    "year": int,
    "keywords": list,
    "platforms": list,
    "file_extensions": list,
    "repo": str,
    "doc": str,
    "playground": str,
    "hello_world": str,
}

URL_FIELDS = ("repo", "doc", "playground")

#: logo accepts either an inline ``data:image/...`` URL or an https image URL
LOGO_IMAGE_RE = re.compile(r"\.(png|jpe?g|gif|svg|webp|avif|ico)$", re.IGNORECASE)

MAX = {
    "display_name": 60,
    "description": 500,
    "keywords": 12,
    "hello_world": 5000,
    "logo": 100_000,
}


def is_https_url(value: str) -> bool:
    """Basic https URL check; scheme + host, nothing fancy."""
    v = value.strip()
    if not v.startswith("https://"):
        return False
    rest = v[8:]
    host = rest.split("/", 1)[0]
    return host == "localhost" or ("." in host and not host.startswith("."))


def extract_language(data: dict, source: str = "") -> dict:
    """Accept the three ways a contributor might lay out one file:

    * plain top-level keys           (recommended, what demo.toml does)
    * one ``[language]`` table
    * exactly one ``[[language]]`` row
    """
    if "language" in data:
        v = data["language"]
        if isinstance(v, list):
            if len(v) != 1:
                raise ValueError(
                    f"{source}: '[[language]]' must contain exactly one entry; "
                    "please use one file per language"
                )
            return v[0]
        if isinstance(v, dict):
            return v
        raise ValueError(f"{source}: 'language' key has an unexpected type")
    return data


def load_language(path: Path) -> tuple[dict | None, str]:
    """Parse and shape-check a single TOML file.

    Returns ``(dict, "")`` on success or ``(None, reason)`` on failure.
    Only structural things are checked here (what full validation does per
    field is validate.py's job) so the site generator can still render an
    almost-correct entry, and CI gives precise per-field messages.
    """
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return None, f"TOML parse error: {exc}"
    except OSError as exc:
        return None, f"cannot read file: {exc}"

    try:
        lang = extract_language(raw, source=path.name)
    except ValueError as exc:
        return None, str(exc)

    if not isinstance(lang, dict):
        return None, "entry must be a TOML table"
    return lang, ""


def lint_language(path: Path, lang: dict) -> tuple[list[str], list[str]]:
    """Semantic checks for one file.  Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []
    now_year = __import__("datetime").date.today().year

    # -- unknown keys (forward-compat: warn only) --------------------------
    extra = sorted(set(lang) - set(FIELD_TYPES))
    if extra:
        warnings.append(f"unknown field(s) ignored: {', '.join(extra)}")

    # -- required fields ---------------------------------------------------
    for field in REQUIRED_FIELDS:
        if field not in lang:
            errors.append(f"missing required field: {field}")
            continue
        if not isinstance(lang[field], FIELD_TYPES[field]):
            errors.append(f"field '{field}' must be of type {FIELD_TYPES[field].__name__}")

    if errors:
        return errors, warnings  # missing basics: stop before deeper checks

    # -- name / slug -------------------------------------------------------
    name = lang["name"]
    if not SLUG_RE.match(str(name)):
        errors.append(
            "field 'name' must match ^[a-z0-9][a-z0-9-]{0,63}$ "
            "e.g. 'toy-basic' (this is used for URLs and files)"
        )
    expected_name = path.stem
    if name != expected_name:
        errors.append(f"field 'name' ({name!r}) must equal the file name 'collections/{path.stem}.toml'")
    if len(str(lang["display_name"])) > MAX["display_name"]:
        errors.append(f"display_name longer than {MAX['display_name']} characters")

    # -- free text limits ----------------------------------------------------
    description = str(lang["description"]).strip()
    if not description:
        errors.append("description must not be empty")
    elif len(description) > MAX["description"]:
        errors.append(f"description longer than {MAX['description']} characters")

    hello = str(lang["hello_world"]).strip()
    if not hello:
        errors.append("hello_world must not be empty")
    elif len(hello) > MAX["hello_world"]:
        errors.append(f"hello_world longer than {MAX['hello_world']} characters")

    # -- year ---------------------------------------------------------------
    year = lang.get("year")
    if year is not None:
        if isinstance(year, bool) or not isinstance(year, int):
            errors.append("field 'year' must be an integer, e.g. 2024")
        elif not (1940 <= year <= now_year):
            errors.append(f"field 'year' must be between 1940 and {now_year}")

    # -- keywords -------------------------------------------------------------
    keywords = lang.get("keywords")
    if keywords is not None:
        if not isinstance(keywords, list) or not all(isinstance(k, str) and k.strip() for k in keywords):
            errors.append("field 'keywords' must be an array of non-empty strings")
        elif len(keywords) > MAX["keywords"]:
            errors.append(f"more than {MAX['keywords']} keywords")

    # -- platforms ---------------------------------------------------------------
    platforms = lang.get("platforms")
    if platforms is not None:
        if not isinstance(platforms, list) or not all(isinstance(p, str) for p in platforms):
            errors.append(f"field 'platforms' must be an array chosen from {KNOWN_PLATFORMS}")
        else:
            bad = [p for p in platforms if p not in KNOWN_PLATFORMS]
            if bad:
                errors.append(f"unknown platform(s): {', '.join(bad)}; allowed: {', '.join(KNOWN_PLATFORMS)}")
            elif not platforms:
                warnings.append("platforms empty — the biggest trading platforms will not be grouped")
    else:
        warnings.append("no platforms filled in, the site will not be able to group by platform")

    # -- file extensions -----------------------------------------------------------
    exts = lang.get("file_extensions")
    if exts is not None:
        if not isinstance(exts, list) or not all(isinstance(e, str) for e in exts):
            errors.append("field 'file_extensions' must be an array of strings, e.g. [\"bas\"]")

    # -- URLs -----------------------------------------------------------------------
    for field in URL_FIELDS:
        value = lang.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not is_https_url(value):
            errors.append(f"field '{field}' must be a https URL (http / non-URL values are not accepted)")
        elif field == "playground" and not value.strip().endswith(".wasm"):
            warnings.append("the playground URL usually should end with .wasm")

    # -- logo -------------------------------------------------------------------
    logo = lang.get("logo")
    if logo is not None:
        if not isinstance(logo, str) or not logo.strip():
            errors.append("field 'logo' must be a non-empty string: a data:image/... URL or an https image URL")
        else:
            v = logo.strip()
            if v.startswith("data:image/"):
                if len(v) > MAX["logo"]:
                    errors.append(
                        f"field 'logo' data URL longer than {MAX['logo']} characters — "
                        "host the image somewhere and use an https URL instead"
                    )
            elif is_https_url(v):
                if len(v) > MAX["logo"]:
                    errors.append(f"field 'logo' longer than {MAX['logo']} characters")
                elif not LOGO_IMAGE_RE.search(v.split("?", 1)[0].split("#", 1)[0]):
                    warnings.append("logo URL does not end with an image extension (.png/.jpg/.svg/...), double-check it")
            else:
                errors.append("field 'logo' must be a data:image/... URL or an https image URL")

    return errors, warnings
