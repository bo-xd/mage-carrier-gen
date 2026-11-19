"""Naming and escaping helpers for Magento 2.4.9 module generation."""

from __future__ import annotations

import json
import re
from xml.sax.saxutils import escape as _xml_escape


def to_pascal_case(name: str) -> str:
    """Normalize a vendor or carrier name into a valid PascalCase PHP identifier."""
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", name.strip()) if part]
    if not parts:
        raise ValueError(f"Invalid identifier: {name!r}")

    pascal = "".join(part[0].upper() + part[1:] for part in parts)
    if not pascal[0].isalpha():
        raise ValueError(f"Identifier must start with a letter: {name!r}")
    return pascal


def to_snake_case(name: str) -> str:
    """Convert a name into lowercase snake_case suitable for Magento carrier codes."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name.strip())
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", cleaned)
    snake = re.sub(r"_+", "_", snake).strip("_").lower()
    if not snake:
        raise ValueError(f"Invalid identifier: {name!r}")
    return snake


def to_kebab_case(name: str) -> str:
    """Convert a name into lowercase kebab-case suitable for Composer package names."""
    return to_snake_case(name).replace("_", "-")


def php_escape(value: str) -> str:
    """Escape a string for inclusion inside a single-quoted PHP string literal."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def php_array_literal(mapping: dict[str, str] | None) -> str:
    """Render a string-to-string dict as a single-line PHP associative array literal."""
    if not mapping:
        return "[]"
    entries = [f"'{php_escape(str(k))}' => '{php_escape(str(v))}'" for k, v in mapping.items()]
    return "[" + ", ".join(entries) + "]"


def xml_escape(value: str) -> str:
    """Escape XML special characters."""
    return _xml_escape(value, {'"': "&quot;", "'": "&apos;"})


def json_escape(value: str) -> str:
    """Escape a string for inclusion inside a JSON double-quoted string."""
    return json.dumps(value)[1:-1]
