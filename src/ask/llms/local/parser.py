"""Modular query parser using an extractor pipeline.

Each extractor is responsible for one aspect of query understanding (action,
file type, time window, path, search pattern, etc.).  The QueryParser runs
every extractor against the *lowercased* query to build a ParsedQuery, while
the original casing is preserved for literal search strings.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# ParsedQuery – the structured output of the parser
# ---------------------------------------------------------------------------

@dataclass
class ParsedQuery:
    """Structured representation of a user's natural-language query."""
    action: Optional[str] = None
    file_types: List[str] = field(default_factory=list)
    time_minutes: Optional[int] = None
    time_days: Optional[int] = None
    path: Optional[str] = None
    search_pattern: Optional[str] = None
    search_pattern_original: Optional[str] = None  # original casing
    name_pattern: Optional[str] = None
    size_constraint: Optional[str] = None  # e.g. "+10M", "-1k"
    permissions: Optional[str] = None
    process_name: Optional[str] = None
    signal: Optional[str] = None
    depth: Optional[int] = None
    count: Optional[int] = None
    destination: Optional[str] = None
    raw_query: str = ""
    raw_query_original: str = ""


# ---------------------------------------------------------------------------
# Extractor base class
# ---------------------------------------------------------------------------

class Extractor:
    """Base class for all extractors.

    Subclasses must implement ``extract(query, query_original, parsed)`` which
    mutates *parsed* in-place.
    """

    def extract(self, query: str, query_original: str, parsed: ParsedQuery) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# ActionExtractor
# ---------------------------------------------------------------------------

class ActionExtractor(Extractor):
    """Determine the primary *action* the user wants (find, search, delete, …)."""

    _PATTERNS = [
        # --- Higher-priority: specific verbs that override generic patterns ---

        # Kill / terminate (must come before "process")
        (re.compile(r"\bkill\b|\bstop\s+(?:the\s+)?process|\bterminate\b"), "kill"),

        # Replace / sed (must come before "search")
        (re.compile(r"\breplace\b|\bsubstitut"), "replace"),
        (re.compile(r"\bsed\b"), "replace"),

        # Search inside files (must come before generic file discovery)
        (re.compile(r"\bgrep\b"), "grep"),
        (re.compile(r"\b(?:search|look)\s+(?:for\s+)?['\"]"), "grep"),
        (re.compile(r"\b(?:search|look)\s+for\s+\S+\s+(?:in|inside|within)\b"), "grep"),
        (re.compile(r"\b(?:search|look)\s+(?:for\s+|inside\s+|within\s+|in\s+files?\b).*\b(?:contain|content|text|string|word|line)"), "grep"),
        (re.compile(r"\bcontain(?:s|ing)?\b"), "grep"),

        # Delete
        (re.compile(r"\b(?:delete|remove|rm|erase|clean\s*(?:up)?|purge)\b"), "delete"),

        # Copy
        (re.compile(r"\bcopy\b|\bcp\b|\bduplicate\b"), "copy"),

        # Move / rename
        (re.compile(r"\bmove\b|\bmv\b|\brename\b"), "move"),

        # Permissions (handle "make X executable" with flexible gap)
        (re.compile(r"\b(?:chmod|permissions?|change\s+permission)\b"), "permissions"),
        (re.compile(r"\bmake\b.*\bexecutable\b"), "permissions"),
        (re.compile(r"\bchown\b|\bowner"), "chown"),

        # System info (must come before generic "size" to catch "disk space")
        (re.compile(r"\bdisk\s*(?:free|space|usage)\b|\bdf\b"), "disk_usage"),
        (re.compile(r"\bmemory\b|\bram\b|\bfree\b"), "memory"),
        (re.compile(r"\buptime\b|\bhow\s+long.*running\b"), "uptime"),
        (re.compile(r"\bwho(?:ami)?\b|\bcurrent\s+user\b"), "whoami"),
        (re.compile(r"\bnetwork\b|\bip\s*addr|\binterface|\bifconfig|\bnetstat|\bport"), "network"),

        # Size / disk usage (after disk_usage to avoid "disk space" matching here)
        (re.compile(r"\b(?:size|disk\s*usage|du|largest|biggest|smallest|heaviest)\b"), "size"),
        (re.compile(r"\bhow\s+(?:much|big)\b"), "size"),

        # Count
        (re.compile(r"\bcount\b|\bhow\s+many\b|\bnumber\s+of\b|\bwc\b"), "count"),

        # Process management (after kill, so "kill" is checked first)
        (re.compile(r"\b(?:process|ps|running|pid)\b"), "process"),

        # File discovery (generic — lower priority)
        (re.compile(r"\b(?:find|look\s*(?:for)?|locate|search\s*(?:for)?|list|show|display|get)\b.*\b(?:file|folder|director|document|image|photo|video|log)"), "find"),
        (re.compile(r"\bfind\b"), "find"),
        (re.compile(r"\blist\b|\bls\b|\bshow\s+(?:all|me|the)?\s*(?:file|folder|director|content)"), "find"),
        (re.compile(r"\blocate\b"), "find"),

        # Tar / archive
        (re.compile(r"\b(?:tar|archive|compress|zip|extract|untar|unzip|decompress)\b"), "archive"),

        # Sort
        (re.compile(r"\bsort\b"), "sort"),

        # Recent / last modified
        (re.compile(r"\brecent(?:ly)?\b|\blast\s+modified\b|\bnewest\b|\blatest\b"), "find"),
    ]

    def extract(self, query: str, query_original: str, parsed: ParsedQuery) -> None:
        for pattern, action in self._PATTERNS:
            if pattern.search(query):
                parsed.action = action
                return


# ---------------------------------------------------------------------------
# FileTypeExtractor
# ---------------------------------------------------------------------------

class FileTypeExtractor(Extractor):
    """Extract requested file extensions / type keywords."""

    _EXT_PATTERN = re.compile(
        r"\.([a-zA-Z0-9]{1,10})\b"
        r"|\b(py|python|javascript|js|typescript|ts|java|cpp|c\+\+|"
        r"go|golang|rust|rs|ruby|rb|php|html|css|json|yaml|yml|xml|"
        r"md|markdown|txt|text|csv|log|sql|sh|bash|shell|"
        r"jpg|jpeg|png|gif|svg|mp4|mp3|pdf|doc|docx|toml|ini|cfg|conf)\b"
        r"|\b(\w+)\s+files?\b"
    )

    _TYPE_MAP = {
        "python": "py", "javascript": "js", "typescript": "ts",
        "c++": "cpp", "golang": "go", "ruby": "rb", "rust": "rs",
        "markdown": "md", "text": "txt", "bash": "sh", "shell": "sh",
        "jpeg": "jpg", "yml": "yaml", "config": "conf",
    }

    # Known extensions for the 3rd capture group heuristic
    _KNOWN_EXTS = {
        "py", "js", "ts", "java", "cpp", "go", "rs", "rb", "php",
        "html", "css", "json", "yaml", "yml", "xml", "md", "txt",
        "csv", "log", "sql", "sh", "jpg", "jpeg", "png", "gif",
        "svg", "mp4", "mp3", "pdf", "doc", "docx", "toml", "ini",
        "cfg", "conf", "c", "h", "hpp", "swift", "kt", "lua", "r",
        "pl", "pm", "ex", "exs", "erl", "hs", "scala", "groovy",
    }

    def extract(self, query: str, query_original: str, parsed: ParsedQuery) -> None:
        for m in self._EXT_PATTERN.finditer(query):
            ext = m.group(1) or m.group(2) or m.group(3)
            if ext:
                ext = ext.lower()
                ext = self._TYPE_MAP.get(ext, ext)
                if ext in self._KNOWN_EXTS or m.group(1) or m.group(2):
                    if ext not in parsed.file_types:
                        parsed.file_types.append(ext)


# ---------------------------------------------------------------------------
# TimeWindowExtractor
# ---------------------------------------------------------------------------

class TimeWindowExtractor(Extractor):
    """Extract time-based filters like 'last hour', 'past 30 minutes', '2 days ago'."""

    _PATTERNS = [
        # "last N minutes/hours/days"
        (re.compile(r"\b(?:last|past|within|recent)\s+(\d+)\s*(min(?:ute)?s?|hours?|hrs?|days?)\b"), None),
        # "from the last hour"
        (re.compile(r"\b(?:from\s+)?(?:the\s+)?last\s+(hour|day|week|month)\b"), None),
        # "N minutes/hours/days ago"
        (re.compile(r"\b(\d+)\s*(min(?:ute)?s?|hours?|hrs?|days?)\s*ago\b"), None),
        # "today"
        (re.compile(r"\btoday\b"), "today"),
        # "yesterday"
        (re.compile(r"\byesterday\b"), "yesterday"),
        # "this week"
        (re.compile(r"\bthis\s+week\b"), "this_week"),
    ]

    _UNIT_TO_MINUTES = {
        "min": 1, "mins": 1, "minute": 1, "minutes": 1,
        "hour": 60, "hours": 60, "hr": 60, "hrs": 60,
        "day": 1440, "days": 1440,
        "week": 10080, "month": 43200,
    }

    def extract(self, query: str, query_original: str, parsed: ParsedQuery) -> None:
        for pattern, shorthand in self._PATTERNS:
            m = pattern.search(query)
            if not m:
                continue

            if shorthand == "today":
                parsed.time_minutes = 1440  # 24 hours
                return
            if shorthand == "yesterday":
                parsed.time_days = 2
                return
            if shorthand == "this_week":
                parsed.time_days = 7
                return

            groups = m.groups()
            if len(groups) == 2 and groups[0] and groups[1]:
                count = int(groups[0])
                unit = groups[1].lower().rstrip("s")
                if unit in ("min", "minute"):
                    unit = "min"
                multiplier = self._UNIT_TO_MINUTES.get(unit, 1)
                total_minutes = count * multiplier
                if total_minutes >= 1440:
                    parsed.time_days = total_minutes // 1440
                else:
                    parsed.time_minutes = total_minutes
                return
            elif len(groups) >= 1 and groups[0]:
                unit = groups[0].lower()
                multiplier = self._UNIT_TO_MINUTES.get(unit, 60)
                total_minutes = multiplier
                if total_minutes >= 1440:
                    parsed.time_days = total_minutes // 1440
                else:
                    parsed.time_minutes = total_minutes
                return


# ---------------------------------------------------------------------------
# PathExtractor
# ---------------------------------------------------------------------------

class PathExtractor(Extractor):
    """Extract file system paths from the query."""

    _PATTERNS = [
        # "in <dir>" / "from <dir>" / "under <dir>" (source-indicating prepositions)
        re.compile(r"\b(?:in|from|under|inside|within|at)\s+((?:~|\.\.?)?/[\w./_*?{}-]+)"),
        # "in the current directory"
        re.compile(r"\b(?:in|from)\s+(?:the\s+)?(?:current|this)\s+(?:directory|dir|folder)\b"),
        # "in home" / "in root"
        re.compile(r"\b(?:in|from)\s+(?:the\s+)?(?:home)\s*(?:directory|dir|folder)?\b"),
        # Explicit paths: /foo/bar, ~/something, ./relative
        # Exclude paths preceded by "to" / "into" (those are destinations)
        re.compile(r"(?:^|(?<!\bto\s)(?<!\binto\s))\s((?:~|\.\.?)?/[\w./_*?{}-]+)"),
    ]

    # Prepositions that indicate a destination rather than a source
    _DEST_PREPOSITIONS = re.compile(r"\b(?:to|into)\s+((?:~|\.\.?)?/[\w./_*?{}-]+)")

    def extract(self, query: str, query_original: str, parsed: ParsedQuery) -> None:
        # Check destination-indicating paths to exclude them from source
        dest_paths = set()
        for m in self._DEST_PREPOSITIONS.finditer(query_original):
            dest_paths.add(m.group(1))

        # Try source path patterns (use original casing for paths)
        for i, pat in enumerate(self._PATTERNS):
            target = query_original if i in (0, 3) else query
            m = pat.search(target)
            if m:
                if i == 1:  # "current directory"
                    parsed.path = "."
                    return
                elif i == 2:  # "home"
                    parsed.path = "~"
                    return
                else:
                    path = m.group(1)
                    if path not in dest_paths:
                        parsed.path = path
                        return


# ---------------------------------------------------------------------------
# SearchPatternExtractor
# ---------------------------------------------------------------------------

class SearchPatternExtractor(Extractor):
    """Extract literal search strings and name patterns from the query."""

    _QUOTED = re.compile(r"""['"]([^'"]+)['"]""")
    _CONTAINING = re.compile(r"\bcontain(?:s|ing)?\s+(?:the\s+)?(?:word|text|string|pattern)?\s*['\"]?([^'\"]+?)['\"]?\s*(?:$|in\b|from\b)")
    _NAMED = re.compile(r"\b(?:named?|called)\s+['\"]?([^\s'\"]+)['\"]?")
    _MATCHING = re.compile(r"\bmatching\s+['\"]?([^\s'\"]+)['\"]?")
    # "search for WORD in" / "grep WORD in" — bare unquoted search term
    _SEARCH_FOR_BARE = re.compile(
        r"\b(?:search|grep|look)\s+(?:for\s+)?(\S+)\s+(?:in|inside|within|from)\b"
    )
    # "replace WORD with" — for replace actions
    _REPLACE_PATTERN = re.compile(
        r"\breplace\s+['\"]?(\S+?)['\"]?\s+(?:with|by)\b"
    )

    # Words that should not be treated as search patterns
    _SKIP_WORDS = frozenset({
        "all", "any", "the", "a", "an", "some", "every", "files", "file",
        "folders", "folder", "directories", "directory", "content", "contents",
    })

    def extract(self, query: str, query_original: str, parsed: ParsedQuery) -> None:
        # Try quoted strings first (use original for casing)
        m = self._QUOTED.search(query_original)
        if m:
            parsed.search_pattern_original = m.group(1)
            parsed.search_pattern = m.group(1).lower()
            return

        # "containing <text>"
        m = self._CONTAINING.search(query)
        if m:
            text = m.group(1).strip()
            # Find original casing
            m_orig = self._CONTAINING.search(query_original)
            parsed.search_pattern = text
            parsed.search_pattern_original = m_orig.group(1).strip() if m_orig else text
            return

        # "search for WORD in ..." (bare unquoted term)
        m = self._SEARCH_FOR_BARE.search(query)
        if m:
            word = m.group(1).strip()
            if word.lower() not in self._SKIP_WORDS:
                # Get original casing
                m_orig = self._SEARCH_FOR_BARE.search(query_original)
                parsed.search_pattern = word
                parsed.search_pattern_original = m_orig.group(1).strip() if m_orig else word
                return

        # "replace WORD with ..."
        m = self._REPLACE_PATTERN.search(query)
        if m:
            word = m.group(1).strip()
            m_orig = self._REPLACE_PATTERN.search(query_original)
            parsed.search_pattern = word
            parsed.search_pattern_original = m_orig.group(1).strip() if m_orig else word
            return

        # "named <pattern>"
        m = self._NAMED.search(query)
        if m:
            parsed.name_pattern = m.group(1)
            return

        # "matching <pattern>"
        m = self._MATCHING.search(query)
        if m:
            parsed.name_pattern = m.group(1)
            return


# ---------------------------------------------------------------------------
# SizeExtractor
# ---------------------------------------------------------------------------

class SizeExtractor(Extractor):
    """Extract size constraints like 'larger than 10MB', 'files over 1G'."""

    _PATTERNS = [
        re.compile(r"\b(?:larger|bigger|greater|over|above|more)\s+than\s+(\d+)\s*(k|kb|m|mb|g|gb|b|bytes?)\b", re.IGNORECASE),
        re.compile(r"\b(?:smaller|less|under|below)\s+than\s+(\d+)\s*(k|kb|m|mb|g|gb|b|bytes?)\b", re.IGNORECASE),
        re.compile(r"\b(\d+)\s*(k|kb|m|mb|g|gb)\b", re.IGNORECASE),
    ]

    _SIZE_MAP = {
        "b": "", "byte": "", "bytes": "",
        "k": "k", "kb": "k",
        "m": "M", "mb": "M",
        "g": "G", "gb": "G",
    }

    def extract(self, query: str, query_original: str, parsed: ParsedQuery) -> None:
        for i, pat in enumerate(self._PATTERNS):
            m = pat.search(query)
            if m:
                amount = m.group(1)
                unit = self._SIZE_MAP.get(m.group(2).lower(), "M")
                if i == 0:  # larger than
                    parsed.size_constraint = f"+{amount}{unit}"
                elif i == 1:  # smaller than
                    parsed.size_constraint = f"-{amount}{unit}"
                else:
                    # Heuristic: if "large/big" in query, it's a minimum
                    if re.search(r"\b(?:larg|big|heav)", query):
                        parsed.size_constraint = f"+{amount}{unit}"
                    else:
                        parsed.size_constraint = f"+{amount}{unit}"
                return


# ---------------------------------------------------------------------------
# DepthExtractor
# ---------------------------------------------------------------------------

class DepthExtractor(Extractor):
    """Extract max depth constraints."""

    _PATTERNS = [
        re.compile(r"\b(?:max\s*)?depth\s+(?:of\s+)?(\d+)\b"),
        re.compile(r"\b(\d+)\s+level"),
        re.compile(r"\bnon[\s-]*recursive\b"),
        re.compile(r"\btop[\s-]*level\b|\bshallow\b"),
    ]

    def extract(self, query: str, query_original: str, parsed: ParsedQuery) -> None:
        for i, pat in enumerate(self._PATTERNS):
            m = pat.search(query)
            if m:
                if i == 0:
                    parsed.depth = int(m.group(1))
                elif i == 1:
                    parsed.depth = int(m.group(1))
                else:
                    parsed.depth = 1
                return


# ---------------------------------------------------------------------------
# ProcessExtractor
# ---------------------------------------------------------------------------

class ProcessExtractor(Extractor):
    """Extract process names and signals for kill/process actions."""

    _PROCESS_NAME = re.compile(
        r"\b(?:kill|stop|terminate|process)\s+(?:the\s+)?(?:process\s+)?['\"]?(\w[\w.-]*)['\"]?"
    )
    _SIGNAL = re.compile(r"\b(?:signal|sig)\s*(\w+)\b|\b(-\d+|sigkill|sigterm|sighup|sigint)\b")

    def extract(self, query: str, query_original: str, parsed: ParsedQuery) -> None:
        m = self._PROCESS_NAME.search(query)
        if m:
            name = m.group(1)
            # Exclude common words that aren't process names
            skip = {"the", "a", "an", "all", "any", "this", "that", "named", "called",
                    "running", "on", "port", "using", "with"}
            if name.lower() not in skip:
                parsed.process_name = name

        m = self._SIGNAL.search(query)
        if m:
            sig = (m.group(1) or m.group(2)).upper()
            if not sig.startswith("SIG") and not sig.startswith("-"):
                sig = "SIG" + sig
            parsed.signal = sig


# ---------------------------------------------------------------------------
# CountExtractor
# ---------------------------------------------------------------------------

class CountExtractor(Extractor):
    """Extract count/limit like 'top 10', 'first 5'."""

    _PATTERNS = [
        re.compile(r"\b(?:top|first|head|limit)\s+(\d+)\b"),
        re.compile(r"\b(\d+)\s+(?:largest|biggest|smallest|newest|oldest|recent)\b"),
    ]

    def extract(self, query: str, query_original: str, parsed: ParsedQuery) -> None:
        for pat in self._PATTERNS:
            m = pat.search(query)
            if m:
                parsed.count = int(m.group(1))
                return


# ---------------------------------------------------------------------------
# DestinationExtractor
# ---------------------------------------------------------------------------

class DestinationExtractor(Extractor):
    """Extract destination path for copy/move operations."""

    _PATTERNS = [
        re.compile(r"\bto\s+((?:~|\.\.?)?/[\w./_*?{}-]+)"),
        re.compile(r"\b(?:into|destination)\s+((?:~|\.\.?)?/[\w./_*?{}-]+)"),
    ]

    def extract(self, query: str, query_original: str, parsed: ParsedQuery) -> None:
        for pat in self._PATTERNS:
            m = pat.search(query_original)  # preserve casing for paths
            if m:
                parsed.destination = m.group(1)
                return


# ---------------------------------------------------------------------------
# QueryParser – the pipeline
# ---------------------------------------------------------------------------

# Default pipeline ordering matters: action first, then specifics.
_DEFAULT_EXTRACTORS: List[Extractor] = [
    ActionExtractor(),
    FileTypeExtractor(),
    TimeWindowExtractor(),
    PathExtractor(),
    SearchPatternExtractor(),
    SizeExtractor(),
    DepthExtractor(),
    ProcessExtractor(),
    CountExtractor(),
    DestinationExtractor(),
]


class QueryParser:
    """Run a pipeline of extractors to convert free-text into ParsedQuery."""

    def __init__(self, extractors: Optional[List[Extractor]] = None):
        self.extractors = extractors if extractors is not None else _DEFAULT_EXTRACTORS

    def parse(self, query: str) -> ParsedQuery:
        query_original = query.strip()
        query_lower = query_original.lower()
        parsed = ParsedQuery(raw_query=query_lower, raw_query_original=query_original)
        for extractor in self.extractors:
            extractor.extract(query_lower, query_original, parsed)
        return parsed
