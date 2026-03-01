"""Generators for file operations: rm, cp, mv, chmod, chown, tar/archive."""

from typing import List

from ask.llms.local.generators.base import CommandGenerator
from ask.llms.local.parser import ParsedQuery
from ask.llms.local.sanitize import quote_find_pattern, quote_path
from ask.llms.types import Command


class DeleteCommandGenerator(CommandGenerator):
    """Generate rm / find -delete commands with safe previews."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        base_path = quote_path(parsed.path) if parsed.path else "."

        find_parts = ["find", base_path]

        if parsed.depth is not None:
            find_parts.append(f"-maxdepth {parsed.depth}")

        if parsed.file_types:
            name_clauses = [f"-name {quote_find_pattern('*.' + ext)}" for ext in parsed.file_types]
            if len(name_clauses) == 1:
                find_parts.append(name_clauses[0])
            else:
                inner = " -o ".join(name_clauses)
                find_parts.append(f"\\( {inner} \\)")

        if parsed.name_pattern:
            pat = parsed.name_pattern
            if "*" not in pat and "?" not in pat:
                pat = f"*{pat}*"
            find_parts.append(f"-name {quote_find_pattern(pat)}")

        if parsed.time_minutes:
            find_parts.append(f"-mmin -{parsed.time_minutes}")
        elif parsed.time_days:
            find_parts.append(f"-mtime -{parsed.time_days}")

        if parsed.size_constraint:
            find_parts.append(f"-size {parsed.size_constraint}")

        find_parts.append("-type f")
        find_expr = " ".join(find_parts)

        commands.append(Command(
            command=find_expr,
            short_explanation="Preview: list files that would be deleted (safe, read-only)",
            is_dangerous=False,
        ))

        commands.append(Command(
            command=f"{find_expr} -delete",
            short_explanation="Delete matching files",
            is_dangerous=True,
            dangerous_explanation="Permanently deletes files matching the criteria; cannot be undone",
        ))

        # Interactive rm alternative
        commands.append(Command(
            command=f"{find_expr} -exec rm -i {{}} \\;",
            short_explanation="Interactively delete matching files (asks for each file)",
            is_dangerous=True,
            dangerous_explanation="Deletes files but prompts for each one; still destructive",
        ))

        return commands[:3]


class CopyCommandGenerator(CommandGenerator):
    """Generate cp commands."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        base_path = quote_path(parsed.path) if parsed.path else "."
        dest = quote_path(parsed.destination) if parsed.destination else "DESTINATION"

        if parsed.file_types:
            for ext in parsed.file_types[:2]:
                cmd = f"find {base_path} -name {quote_find_pattern('*.' + ext)} -type f -exec cp {{}} {dest} \\;"
                commands.append(Command(
                    command=cmd,
                    short_explanation=f"Copy all .{ext} files to {dest}",
                    is_dangerous=False,
                ))
        elif parsed.name_pattern:
            pat = parsed.name_pattern
            if "*" not in pat and "?" not in pat:
                pat = f"*{pat}*"
            cmd = f"find {base_path} -name {quote_find_pattern(pat)} -type f -exec cp {{}} {dest} \\;"
            commands.append(Command(
                command=cmd,
                short_explanation=f"Copy files matching '{parsed.name_pattern}' to {dest}",
                is_dangerous=False,
            ))
        else:
            commands.append(Command(
                command=f"cp -r {base_path} {dest}",
                short_explanation=f"Recursively copy {base_path} to {dest}",
                is_dangerous=False,
            ))

        # rsync alternative
        commands.append(Command(
            command=f"rsync -av {base_path}/ {dest}/",
            short_explanation=f"Sync {base_path} to {dest} (preserves attributes)",
            is_dangerous=False,
        ))

        return commands[:3]


class MoveCommandGenerator(CommandGenerator):
    """Generate mv commands."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        base_path = quote_path(parsed.path) if parsed.path else "."
        dest = quote_path(parsed.destination) if parsed.destination else "DESTINATION"

        if parsed.file_types:
            for ext in parsed.file_types[:2]:
                # Preview first
                find_cmd = f"find {base_path} -name {quote_find_pattern('*.' + ext)} -type f"
                commands.append(Command(
                    command=find_cmd,
                    short_explanation=f"Preview: list .{ext} files that would be moved",
                    is_dangerous=False,
                ))
                cmd = f"find {base_path} -name {quote_find_pattern('*.' + ext)} -type f -exec mv {{}} {dest} \\;"
                commands.append(Command(
                    command=cmd,
                    short_explanation=f"Move all .{ext} files to {dest}",
                    is_dangerous=True,
                    dangerous_explanation="Moves files from original location; ensure destination exists",
                ))
        else:
            commands.append(Command(
                command=f"mv {base_path} {dest}",
                short_explanation=f"Move/rename {base_path} to {dest}",
                is_dangerous=True,
                dangerous_explanation="Moves the file or directory; original path will no longer exist",
            ))

        return commands[:3]


class PermissionsCommandGenerator(CommandGenerator):
    """Generate chmod commands."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        base_path = quote_path(parsed.path) if parsed.path else "FILE"

        if "executable" in parsed.raw_query or "exec" in parsed.raw_query:
            commands.append(Command(
                command=f"chmod +x {base_path}",
                short_explanation=f"Make {base_path} executable",
                is_dangerous=True,
                dangerous_explanation="Changes file permissions",
            ))

        if parsed.permissions:
            commands.append(Command(
                command=f"chmod {parsed.permissions} {base_path}",
                short_explanation=f"Set permissions to {parsed.permissions}",
                is_dangerous=True,
                dangerous_explanation="Changes file permissions",
            ))

        # Show current permissions
        commands.append(Command(
            command=f"ls -la {base_path}",
            short_explanation=f"View current permissions for {base_path}",
            is_dangerous=False,
        ))

        if parsed.file_types:
            ext = parsed.file_types[0]
            cmd = f"find . -name {quote_find_pattern('*.' + ext)} -type f -exec ls -la {{}} +"
            commands.append(Command(
                command=cmd,
                short_explanation=f"View permissions of all .{ext} files",
                is_dangerous=False,
            ))

        return commands[:3]


class ChownCommandGenerator(CommandGenerator):
    """Generate chown commands."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        base_path = quote_path(parsed.path) if parsed.path else "FILE"

        # Preview: show current owner
        commands.append(Command(
            command=f"ls -la {base_path}",
            short_explanation=f"View current ownership for {base_path}",
            is_dangerous=False,
        ))

        commands.append(Command(
            command=f"chown USER:GROUP {base_path}",
            short_explanation="Change ownership (replace USER:GROUP)",
            is_dangerous=True,
            dangerous_explanation="Changes file ownership; may require sudo",
        ))

        commands.append(Command(
            command=f"chown -R USER:GROUP {base_path}",
            short_explanation="Recursively change ownership (replace USER:GROUP)",
            is_dangerous=True,
            dangerous_explanation="Recursively changes ownership; may require sudo",
        ))

        return commands[:3]


class ArchiveCommandGenerator(CommandGenerator):
    """Generate tar/zip commands for archiving and extraction."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        base_path = quote_path(parsed.path) if parsed.path else "."
        raw = parsed.raw_query

        is_extract = any(w in raw for w in ("extract", "untar", "unzip", "decompress", "unpack"))

        if is_extract:
            commands.append(Command(
                command=f"tar -xzvf {base_path}",
                short_explanation=f"Extract gzipped tar archive {base_path}",
                is_dangerous=False,
            ))
            commands.append(Command(
                command=f"tar -xvf {base_path}",
                short_explanation=f"Extract tar archive {base_path}",
                is_dangerous=False,
            ))
            if "zip" in raw:
                commands.append(Command(
                    command=f"unzip {base_path}",
                    short_explanation=f"Extract zip archive {base_path}",
                    is_dangerous=False,
                ))
        else:
            commands.append(Command(
                command=f"tar -czvf archive.tar.gz {base_path}",
                short_explanation=f"Create gzipped tar archive of {base_path}",
                is_dangerous=False,
            ))
            if "zip" in raw:
                commands.append(Command(
                    command=f"zip -r archive.zip {base_path}",
                    short_explanation=f"Create zip archive of {base_path}",
                    is_dangerous=False,
                ))
            else:
                commands.append(Command(
                    command=f"tar -cvf archive.tar {base_path}",
                    short_explanation=f"Create tar archive of {base_path} (no compression)",
                    is_dangerous=False,
                ))

            # List contents of an archive
            commands.append(Command(
                command=f"tar -tzvf {base_path}",
                short_explanation=f"List contents of archive {base_path}",
                is_dangerous=False,
            ))

        return commands[:3]
