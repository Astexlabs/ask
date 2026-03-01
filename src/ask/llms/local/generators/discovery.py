"""Generators for file discovery: find, ls, du, wc."""

from typing import List

from ask.llms.local.generators.base import CommandGenerator
from ask.llms.local.parser import ParsedQuery
from ask.llms.local.platform_utils import (
    du_human_sort_flags,
    find_mtime_days_flag,
    find_mtime_flag,
    is_macos,
)
from ask.llms.local.sanitize import quote_find_pattern, quote_path, quote_pattern
from ask.llms.types import Command


class FindCommandGenerator(CommandGenerator):
    """Generate find / ls commands for file discovery."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        base_path = quote_path(parsed.path) if parsed.path else "."

        parts = ["find", base_path]
        explanation_bits: List[str] = []

        # Depth
        if parsed.depth is not None:
            parts.append(f"-maxdepth {parsed.depth}")
            explanation_bits.append(f"max depth {parsed.depth}")

        # File type filters
        if parsed.file_types:
            name_clauses = []
            for ext in parsed.file_types:
                name_clauses.append(f"-name {quote_find_pattern('*.' + ext)}")
            if len(name_clauses) == 1:
                parts.append(name_clauses[0])
                explanation_bits.append(f".{parsed.file_types[0]} files")
            else:
                inner = " -o ".join(name_clauses)
                parts.append(f"\\( {inner} \\)")
                exts = ", ".join(f".{e}" for e in parsed.file_types)
                explanation_bits.append(f"{exts} files")

        # Name pattern
        if parsed.name_pattern:
            pat = parsed.name_pattern
            if "*" not in pat and "?" not in pat:
                pat = f"*{pat}*"
            parts.append(f"-name {quote_find_pattern(pat)}")
            explanation_bits.append(f"matching '{parsed.name_pattern}'")

        # Time filter
        if parsed.time_minutes:
            parts.append(find_mtime_flag(parsed.time_minutes))
            explanation_bits.append(f"modified in the last {_human_time(parsed.time_minutes)}")
        elif parsed.time_days:
            parts.append(find_mtime_days_flag(parsed.time_days))
            explanation_bits.append(f"modified in the last {parsed.time_days} day(s)")

        # Size filter
        if parsed.size_constraint:
            parts.append(f"-size {parsed.size_constraint}")
            explanation_bits.append(f"size {parsed.size_constraint}")

        parts.append("-type f")

        cmd_str = " ".join(parts)
        explanation = "Find " + (", ".join(explanation_bits) if explanation_bits else "files") + f" in {base_path}"
        commands.append(Command(
            command=cmd_str,
            short_explanation=explanation,
            is_dangerous=False,
        ))

        if not parsed.size_constraint and not parsed.time_minutes and not parsed.time_days:
            if parsed.file_types:
                globs = " ".join(quote_pattern(f"*.{ext}") for ext in parsed.file_types)
                ls_cmd = f"ls -la {globs}"
                commands.append(Command(
                    command=ls_cmd,
                    short_explanation=f"List {globs} in current directory (non-recursive)",
                    is_dangerous=False,
                ))

        if parsed.time_minutes or parsed.time_days or "recent" in parsed.raw_query or "newest" in parsed.raw_query or "latest" in parsed.raw_query:
            sort_cmd = cmd_str.replace("-type f", "-type f -printf '%T@ %p\\n'") + " | sort -rn | head -20"
            if is_macos():
                sort_cmd = cmd_str.replace("-type f", "-type f -print0") + " | xargs -0 ls -lt | head -20"
            commands.append(Command(
                command=sort_cmd,
                short_explanation="Find and sort by most recently modified",
                is_dangerous=False,
            ))

        return commands[:3]


class SizeCommandGenerator(CommandGenerator):
    """Generate du / find commands for disk usage and file size queries."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        base_path = quote_path(parsed.path) if parsed.path else "."

        # du for directory sizes
        du_flags = du_human_sort_flags()
        if parsed.file_types:
            # Show size of specific file types
            for ext in parsed.file_types[:2]:
                cmd = f"find {base_path} -name {quote_find_pattern('*.' + ext)} -type f -exec {du_flags}" + " {} +"
                commands.append(Command(
                    command=cmd,
                    short_explanation=f"Show sizes of .{ext} files",
                    is_dangerous=False,
                ))
        else:
            # General directory size
            if parsed.depth is not None:
                cmd = f"du -h --max-depth={parsed.depth} {base_path} | sort -rh | head -20"
                if is_macos():
                    cmd = f"du -hd {parsed.depth} {base_path} | sort -rh | head -20"
            else:
                cmd = f"du -h --max-depth=1 {base_path} | sort -rh"
                if is_macos():
                    cmd = f"du -hd 1 {base_path} | sort -rh"

            commands.append(Command(
                command=cmd,
                short_explanation=f"Show directory sizes in {base_path}",
                is_dangerous=False,
            ))

        # Largest files
        count = parsed.count or 10
        if parsed.file_types:
            name_filter = " -o ".join(f"-name {quote_find_pattern('*.' + e)}" for e in parsed.file_types)
            if len(parsed.file_types) > 1:
                name_filter = f"\\( {name_filter} \\)"
            cmd = f"find {base_path} {name_filter} -type f -exec ls -lhS {{}} + | head -{count}"
        else:
            cmd = f"find {base_path} -type f -exec ls -lhS {{}} + | head -{count}"
        commands.append(Command(
            command=cmd,
            short_explanation=f"Show {count} largest files",
            is_dangerous=False,
        ))

        return commands[:3]


class CountCommandGenerator(CommandGenerator):
    """Generate wc / find commands for counting files or lines."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        base_path = quote_path(parsed.path) if parsed.path else "."

        if parsed.file_types:
            for ext in parsed.file_types[:2]:
                # Count files
                cmd = f"find {base_path} -name {quote_find_pattern('*.' + ext)} -type f | wc -l"
                commands.append(Command(
                    command=cmd,
                    short_explanation=f"Count .{ext} files in {base_path}",
                    is_dangerous=False,
                ))
            # Count lines across files
            if parsed.file_types:
                ext = parsed.file_types[0]
                cmd = f"find {base_path} -name {quote_find_pattern('*.' + ext)} -type f -exec wc -l {{}} + | tail -1"
                commands.append(Command(
                    command=cmd,
                    short_explanation=f"Count total lines across .{ext} files",
                    is_dangerous=False,
                ))
        else:
            cmd = f"find {base_path} -type f | wc -l"
            commands.append(Command(
                command=cmd,
                short_explanation=f"Count all files in {base_path}",
                is_dangerous=False,
            ))
            cmd2 = f"ls -1 {base_path} | wc -l"
            commands.append(Command(
                command=cmd2,
                short_explanation=f"Count entries in {base_path} (non-recursive)",
                is_dangerous=False,
            ))

        return commands[:3]


def _human_time(minutes: int) -> str:
    """Convert minutes to a human-readable string."""
    if minutes < 60:
        return f"{minutes} minute(s)"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour(s)"
    days = hours // 24
    return f"{days} day(s)"
