"""Fallback generator: contextual suggestions when no action fully matches."""

from typing import List

from ask.llms.local.generators.base import CommandGenerator
from ask.llms.local.parser import ParsedQuery
from ask.llms.types import Command


class FallbackCommandGenerator(CommandGenerator):
    """Provide helpful, educational command suggestions when the query cannot
    be fully mapped to an action.

    Instead of running arbitrary commands, this reads whatever partial context
    was extracted and outputs formatted suggestions as comments.
    """

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        hints: List[str] = []

        # Build contextual suggestions based on whatever was extracted
        if parsed.file_types:
            exts = ", ".join(f".{e}" for e in parsed.file_types)
            hints.append(f"file type(s): {exts}")
            commands.append(Command(
                command=f"# Try: ask 'find {parsed.file_types[0]} files'",
                short_explanation=f"Hint: search for {exts} files",
                is_dangerous=False,
            ))
            commands.append(Command(
                command=f"find . -name '*.{parsed.file_types[0]}' -type f",
                short_explanation=f"Find all {exts} files in current directory",
                is_dangerous=False,
            ))

        if parsed.search_pattern:
            hints.append(f"pattern: '{parsed.search_pattern}'")
            pattern = parsed.search_pattern_original or parsed.search_pattern
            if not any(c.command.startswith("find") or c.command.startswith("grep") for c in commands):
                commands.append(Command(
                    command=f"grep -rn '{pattern}' .",
                    short_explanation=f"Search for '{pattern}' in files",
                    is_dangerous=False,
                ))

        if parsed.path:
            hints.append(f"path: {parsed.path}")
            if not commands:
                commands.append(Command(
                    command=f"ls -la {parsed.path}",
                    short_explanation=f"List contents of {parsed.path}",
                    is_dangerous=False,
                ))

        if parsed.time_minutes or parsed.time_days:
            time_desc = f"{parsed.time_minutes} minutes" if parsed.time_minutes else f"{parsed.time_days} days"
            hints.append(f"time window: last {time_desc}")
            if not commands:
                if parsed.time_minutes:
                    commands.append(Command(
                        command=f"find . -mmin -{parsed.time_minutes} -type f",
                        short_explanation=f"Find files modified in the last {time_desc}",
                        is_dangerous=False,
                    ))
                else:
                    commands.append(Command(
                        command=f"find . -mtime -{parsed.time_days} -type f",
                        short_explanation=f"Find files modified in the last {time_desc}",
                        is_dangerous=False,
                    ))

        if parsed.process_name:
            hints.append(f"process: {parsed.process_name}")
            if not commands:
                commands.append(Command(
                    command=f"pgrep -fl {parsed.process_name}",
                    short_explanation=f"Find processes matching '{parsed.process_name}'",
                    is_dangerous=False,
                ))

        # If we still have nothing, provide general help
        if not commands:
            commands.append(Command(
                command="# Try: ask 'find python files from the last hour'",
                short_explanation="Example: find files by type and time",
                is_dangerous=False,
            ))
            commands.append(Command(
                command="# Try: ask 'search for TODO in js files'",
                short_explanation="Example: search file contents",
                is_dangerous=False,
            ))
            commands.append(Command(
                command="# Try: ask 'show disk usage' or 'list running processes'",
                short_explanation="Example: system info commands",
                is_dangerous=False,
            ))

        return commands[:3]
