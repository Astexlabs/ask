"""Shell sanitization utilities to prevent command injection."""

import re
import shlex
from typing import List

_GLOB_CHARS = re.compile(r"[*?]")


def quote_path(path: str) -> str:
    """Safely quote a path for shell injection prevention using shlex.quote()."""
    if not path:
        return "''"
    return shlex.quote(path)


def quote_find_pattern(pattern: str) -> str:
    """Quote a glob pattern for use with find -name / -iname.

    ``find`` performs its own glob matching, so the shell must NOT expand
    wildcards.  The entire pattern is therefore single-quoted, which
    prevents shell glob expansion while letting ``find`` see the literal
    ``*`` and ``?`` characters it needs.

    Examples:
        quote_find_pattern("*.py")         -> "'*.py'"
        quote_find_pattern("hello")        -> "'hello'"
        quote_find_pattern("*.py; rm -rf") -> "'*.py; rm -rf'"
    """
    if not pattern:
        return "''"
    return shlex.quote(pattern)


def quote_pattern(pattern: str) -> str:
    """Quote a pattern for shell use while preserving glob wildcards (* and ?).

    Use this when the **shell** should expand the globs (e.g. ``ls *.py``).
    For ``find -name`` patterns use :func:`quote_find_pattern` instead.

    Strategy: split the pattern into segments around glob characters,
    quote each non-glob segment with shlex.quote(), then concatenate
    with the raw glob chars between them.

    Examples:
        quote_pattern("*.py")         -> "*'.py'"  (star is unquoted)
        quote_pattern("hello")        -> "'hello'"
        quote_pattern("*.py; rm -rf") -> "*'.py; rm -rf'"
    """
    if not pattern:
        return "''"

    if not _GLOB_CHARS.search(pattern):
        return shlex.quote(pattern)

    parts: List[str] = re.split(r"([*?])", pattern)

    result_parts: List[str] = []
    for part in parts:
        if part in ("*", "?"):
            result_parts.append(part)
        elif part:
            result_parts.append(shlex.quote(part))

    result = "".join(result_parts)

    result = result.replace("''", "")

    if not result:
        return "''"

    return result
