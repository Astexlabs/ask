"""Generators for content search and replacement: grep, sed."""

from typing import List

from ask.llms.local.generators.base import CommandGenerator
from ask.llms.local.parser import ParsedQuery
from ask.llms.local.sanitize import quote_path, quote_pattern
from ask.llms.types import Command


class GrepCommandGenerator(CommandGenerator):
    """Generate grep commands for searching file contents."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        base_path = quote_path(parsed.path) if parsed.path else "."

        # Use the original-cased pattern for literal search
        pattern = parsed.search_pattern_original or parsed.search_pattern or parsed.name_pattern
        if not pattern:
            # If no search pattern, maybe the raw query has a clue
            # Fall back to a helpful suggestion
            pattern = ""

        if not pattern:
            # Can't grep without a pattern, offer a template
            commands.append(Command(
                command=f"grep -rn 'PATTERN' {base_path}",
                short_explanation="Search recursively for PATTERN (replace with your text)",
                is_dangerous=False,
            ))
            return commands

        quoted_pattern = quote_path(pattern)  # shlex.quote for safety

        # Basic recursive grep
        grep_parts = ["grep", "-rn"]

        # Include specific file types
        include_flags = ""
        if parsed.file_types:
            include_flags = " ".join(f"--include={quote_pattern('*.' + ext)}" for ext in parsed.file_types)
            grep_parts.append(include_flags)

        grep_parts.extend([quoted_pattern, base_path])
        cmd_str = " ".join(grep_parts)

        type_desc = ""
        if parsed.file_types:
            type_desc = " in " + ", ".join(f".{e}" for e in parsed.file_types) + " files"

        commands.append(Command(
            command=cmd_str,
            short_explanation=f"Search for '{pattern}'{type_desc} (with line numbers)",
            is_dangerous=False,
        ))

        # Case-insensitive variant
        grep_i_parts = ["grep", "-rni"]
        if include_flags:
            grep_i_parts.append(include_flags)
        grep_i_parts.extend([quoted_pattern, base_path])
        commands.append(Command(
            command=" ".join(grep_i_parts),
            short_explanation=f"Search for '{pattern}' (case-insensitive)",
            is_dangerous=False,
        ))

        # Show only matching files
        grep_l_parts = ["grep", "-rl"]
        if include_flags:
            grep_l_parts.append(include_flags)
        grep_l_parts.extend([quoted_pattern, base_path])
        commands.append(Command(
            command=" ".join(grep_l_parts),
            short_explanation=f"List files containing '{pattern}'",
            is_dangerous=False,
        ))

        return commands[:3]


class ReplaceCommandGenerator(CommandGenerator):
    """Generate sed commands for search-and-replace operations."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        base_path = quote_path(parsed.path) if parsed.path else "."

        pattern = parsed.search_pattern_original or parsed.search_pattern
        if not pattern:
            # Template command
            commands.append(Command(
                command=f"find {base_path} -type f -exec grep -l 'SEARCH' {{}} + | head -20",
                short_explanation="Find files containing SEARCH (preview before replace)",
                is_dangerous=False,
            ))
            commands.append(Command(
                command=f"sed -i 's/SEARCH/REPLACE/g' FILE",
                short_explanation="Replace SEARCH with REPLACE in FILE (edit template)",
                is_dangerous=True,
                dangerous_explanation="sed -i modifies files in-place; back up first",
            ))
            return commands

        quoted_pattern = quote_path(pattern)

        # Safe preview: grep first to see what would change
        include_flags = ""
        if parsed.file_types:
            include_flags = " ".join(f"--include={quote_pattern('*.' + ext)}" for ext in parsed.file_types)

        grep_parts = ["grep", "-rn"]
        if include_flags:
            grep_parts.append(include_flags)
        grep_parts.extend([quoted_pattern, base_path])

        commands.append(Command(
            command=" ".join(grep_parts),
            short_explanation=f"Preview: show lines matching '{pattern}' (safe, read-only)",
            is_dangerous=False,
        ))

        # sed for in-place replacement
        if parsed.file_types:
            for ext in parsed.file_types[:1]:
                cmd = (
                    f"find {base_path} -name {quote_pattern('*.' + ext)} -type f"
                    f" -exec sed -i 's/{pattern}/REPLACEMENT/g' {{}} +"
                )
                commands.append(Command(
                    command=cmd,
                    short_explanation=f"Replace '{pattern}' with REPLACEMENT in .{ext} files",
                    is_dangerous=True,
                    dangerous_explanation="sed -i modifies files in-place; make sure to back up first",
                ))
        else:
            cmd = f"sed -i 's/{pattern}/REPLACEMENT/g' FILE"
            commands.append(Command(
                command=cmd,
                short_explanation=f"Replace '{pattern}' with REPLACEMENT in FILE",
                is_dangerous=True,
                dangerous_explanation="sed -i modifies files in-place; make sure to back up first",
            ))

        return commands[:3]
