"""Tests for command generators."""

import pytest

from zev.llms.local.generators.base import CommandGeneratorRegistry
from zev.llms.local.generators.discovery import (
    CountCommandGenerator,
    FindCommandGenerator,
    SizeCommandGenerator,
)
from zev.llms.local.generators.fallback import FallbackCommandGenerator
from zev.llms.local.generators.file_ops import (
    ArchiveCommandGenerator,
    CopyCommandGenerator,
    DeleteCommandGenerator,
    MoveCommandGenerator,
    PermissionsCommandGenerator,
)
from zev.llms.local.generators.search import (
    GrepCommandGenerator,
    ReplaceCommandGenerator,
)
from zev.llms.local.generators.system import (
    DiskUsageCommandGenerator,
    KillCommandGenerator,
    MemoryCommandGenerator,
    NetworkCommandGenerator,
    ProcessCommandGenerator,
    UptimeCommandGenerator,
    WhoamiCommandGenerator,
)
from zev.llms.local.parser import ParsedQuery


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_parsed(**kwargs) -> ParsedQuery:
    """Create a ParsedQuery with sensible defaults."""
    defaults = {"raw_query": "", "raw_query_original": ""}
    defaults.update(kwargs)
    return ParsedQuery(**defaults)


# ---------------------------------------------------------------------------
# FindCommandGenerator
# ---------------------------------------------------------------------------

class TestFindCommandGenerator:
    def setup_method(self):
        self.gen = FindCommandGenerator()

    def test_basic_find(self):
        p = _make_parsed(action="find", file_types=["py"])
        cmds = self.gen.generate(p)
        assert len(cmds) >= 1
        assert "find" in cmds[0].command
        assert ".py" in cmds[0].command and "*" in cmds[0].command

    def test_find_with_path(self):
        p = _make_parsed(action="find", file_types=["log"], path="/var/log")
        cmds = self.gen.generate(p)
        assert "/var/log" in cmds[0].command

    def test_find_with_time(self):
        p = _make_parsed(action="find", file_types=["py"], time_minutes=60)
        cmds = self.gen.generate(p)
        assert "-mmin" in cmds[0].command

    def test_find_with_depth(self):
        p = _make_parsed(action="find", depth=2)
        cmds = self.gen.generate(p)
        assert "-maxdepth 2" in cmds[0].command

    def test_find_with_size(self):
        p = _make_parsed(action="find", size_constraint="+10M")
        cmds = self.gen.generate(p)
        assert "-size +10M" in cmds[0].command

    def test_find_multiple_types(self):
        p = _make_parsed(action="find", file_types=["py", "js"])
        cmds = self.gen.generate(p)
        assert ".py" in cmds[0].command and "*" in cmds[0].command
        assert ".js" in cmds[0].command

    def test_find_with_name_pattern(self):
        p = _make_parsed(action="find", name_pattern="config")
        cmds = self.gen.generate(p)
        assert "*config*" in cmds[0].command or "config" in cmds[0].command

    def test_not_dangerous(self):
        p = _make_parsed(action="find", file_types=["py"])
        cmds = self.gen.generate(p)
        for cmd in cmds:
            assert cmd.is_dangerous is False

    def test_max_three_commands(self):
        p = _make_parsed(action="find", file_types=["py"], time_minutes=60,
                         raw_query="find recent py files")
        cmds = self.gen.generate(p)
        assert len(cmds) <= 3


# ---------------------------------------------------------------------------
# SizeCommandGenerator
# ---------------------------------------------------------------------------

class TestSizeCommandGenerator:
    def setup_method(self):
        self.gen = SizeCommandGenerator()

    def test_du_output(self):
        p = _make_parsed(action="size")
        cmds = self.gen.generate(p)
        assert len(cmds) >= 1
        assert any("du" in c.command or "ls" in c.command for c in cmds)

    def test_file_type_size(self):
        p = _make_parsed(action="size", file_types=["py"])
        cmds = self.gen.generate(p)
        assert any(".py" in c.command and "*" in c.command for c in cmds)


# ---------------------------------------------------------------------------
# CountCommandGenerator
# ---------------------------------------------------------------------------

class TestCountCommandGenerator:
    def setup_method(self):
        self.gen = CountCommandGenerator()

    def test_count_files(self):
        p = _make_parsed(action="count", file_types=["py"])
        cmds = self.gen.generate(p)
        assert any("wc -l" in c.command for c in cmds)
        assert any(".py" in c.command and "*" in c.command for c in cmds)

    def test_count_all(self):
        p = _make_parsed(action="count")
        cmds = self.gen.generate(p)
        assert any("wc -l" in c.command for c in cmds)


# ---------------------------------------------------------------------------
# GrepCommandGenerator
# ---------------------------------------------------------------------------

class TestGrepCommandGenerator:
    def setup_method(self):
        self.gen = GrepCommandGenerator()

    def test_basic_grep(self):
        p = _make_parsed(action="grep", search_pattern="todo",
                         search_pattern_original="TODO")
        cmds = self.gen.generate(p)
        assert len(cmds) >= 1
        assert "grep" in cmds[0].command
        assert "TODO" in cmds[0].command

    def test_grep_with_file_type(self):
        p = _make_parsed(action="grep", search_pattern="error",
                         search_pattern_original="error", file_types=["py"])
        cmds = self.gen.generate(p)
        assert any("--include" in c.command for c in cmds)

    def test_no_pattern_gives_template(self):
        p = _make_parsed(action="grep")
        cmds = self.gen.generate(p)
        assert len(cmds) >= 1
        assert "PATTERN" in cmds[0].command

    def test_case_insensitive_option(self):
        p = _make_parsed(action="grep", search_pattern="todo",
                         search_pattern_original="TODO")
        cmds = self.gen.generate(p)
        assert any("-rni" in c.command for c in cmds)

    def test_files_only_option(self):
        p = _make_parsed(action="grep", search_pattern="todo",
                         search_pattern_original="TODO")
        cmds = self.gen.generate(p)
        assert any("-rl" in c.command for c in cmds)


# ---------------------------------------------------------------------------
# ReplaceCommandGenerator
# ---------------------------------------------------------------------------

class TestReplaceCommandGenerator:
    def setup_method(self):
        self.gen = ReplaceCommandGenerator()

    def test_replace_gives_preview_first(self):
        p = _make_parsed(action="replace", search_pattern="foo",
                         search_pattern_original="foo")
        cmds = self.gen.generate(p)
        assert len(cmds) >= 2
        # First command should be safe preview
        assert cmds[0].is_dangerous is False
        assert "grep" in cmds[0].command

    def test_replace_is_dangerous(self):
        p = _make_parsed(action="replace", search_pattern="foo",
                         search_pattern_original="foo")
        cmds = self.gen.generate(p)
        dangerous_cmds = [c for c in cmds if c.is_dangerous]
        assert len(dangerous_cmds) >= 1
        assert any("sed" in c.command for c in dangerous_cmds)

    def test_replace_no_pattern_gives_template(self):
        p = _make_parsed(action="replace")
        cmds = self.gen.generate(p)
        assert len(cmds) >= 1


# ---------------------------------------------------------------------------
# DeleteCommandGenerator
# ---------------------------------------------------------------------------

class TestDeleteCommandGenerator:
    def setup_method(self):
        self.gen = DeleteCommandGenerator()

    def test_preview_first(self):
        p = _make_parsed(action="delete", file_types=["log"])
        cmds = self.gen.generate(p)
        assert cmds[0].is_dangerous is False
        assert "-delete" not in cmds[0].command

    def test_delete_is_dangerous(self):
        p = _make_parsed(action="delete", file_types=["tmp"])
        cmds = self.gen.generate(p)
        dangerous = [c for c in cmds if c.is_dangerous]
        assert len(dangerous) >= 1
        assert all(c.dangerous_explanation for c in dangerous)

    def test_interactive_delete_option(self):
        p = _make_parsed(action="delete", file_types=["log"])
        cmds = self.gen.generate(p)
        assert any("rm -i" in c.command for c in cmds)


# ---------------------------------------------------------------------------
# CopyCommandGenerator
# ---------------------------------------------------------------------------

class TestCopyCommandGenerator:
    def setup_method(self):
        self.gen = CopyCommandGenerator()

    def test_copy_with_destination(self):
        p = _make_parsed(action="copy", file_types=["py"], destination="/backup")
        cmds = self.gen.generate(p)
        assert any("cp" in c.command or "rsync" in c.command for c in cmds)
        assert any("/backup" in c.command for c in cmds)

    def test_copy_not_dangerous(self):
        p = _make_parsed(action="copy", file_types=["py"])
        cmds = self.gen.generate(p)
        # Copy operations are generally not dangerous
        assert any(not c.is_dangerous for c in cmds)


# ---------------------------------------------------------------------------
# MoveCommandGenerator
# ---------------------------------------------------------------------------

class TestMoveCommandGenerator:
    def setup_method(self):
        self.gen = MoveCommandGenerator()

    def test_move_is_dangerous(self):
        p = _make_parsed(action="move", destination="/tmp")
        cmds = self.gen.generate(p)
        assert any(c.is_dangerous for c in cmds)

    def test_move_has_preview(self):
        p = _make_parsed(action="move", file_types=["py"], destination="/tmp")
        cmds = self.gen.generate(p)
        # Should have a preview (non-dangerous) option first
        assert any(not c.is_dangerous for c in cmds)


# ---------------------------------------------------------------------------
# KillCommandGenerator
# ---------------------------------------------------------------------------

class TestKillCommandGenerator:
    def setup_method(self):
        self.gen = KillCommandGenerator()

    def test_kill_preview_first(self):
        p = _make_parsed(action="kill", process_name="node")
        cmds = self.gen.generate(p)
        assert cmds[0].is_dangerous is False
        assert "pgrep" in cmds[0].command

    def test_kill_is_dangerous(self):
        p = _make_parsed(action="kill", process_name="python")
        cmds = self.gen.generate(p)
        dangerous = [c for c in cmds if c.is_dangerous]
        assert len(dangerous) >= 1
        assert all(c.dangerous_explanation for c in dangerous)

    def test_kill_with_signal(self):
        p = _make_parsed(action="kill", process_name="python", signal="SIGKILL")
        cmds = self.gen.generate(p)
        assert any("SIGKILL" in c.command for c in cmds)

    def test_kill_no_name_gives_template(self):
        p = _make_parsed(action="kill")
        cmds = self.gen.generate(p)
        assert any("PID" in c.command for c in cmds)


# ---------------------------------------------------------------------------
# PermissionsCommandGenerator
# ---------------------------------------------------------------------------

class TestPermissionsCommandGenerator:
    def setup_method(self):
        self.gen = PermissionsCommandGenerator()

    def test_make_executable(self):
        p = _make_parsed(action="permissions", path="script.sh",
                         raw_query="make script.sh executable")
        cmds = self.gen.generate(p)
        assert any("chmod +x" in c.command for c in cmds)

    def test_permissions_are_dangerous(self):
        p = _make_parsed(action="permissions", path="script.sh",
                         raw_query="make script.sh executable")
        cmds = self.gen.generate(p)
        chmod_cmds = [c for c in cmds if "chmod" in c.command]
        assert all(c.is_dangerous for c in chmod_cmds)


# ---------------------------------------------------------------------------
# SystemCommandGenerators
# ---------------------------------------------------------------------------

class TestDiskUsageCommandGenerator:
    def test_generates_df(self):
        gen = DiskUsageCommandGenerator()
        cmds = gen.generate(_make_parsed())
        assert len(cmds) >= 1
        assert all("df" in c.command for c in cmds)
        assert all(not c.is_dangerous for c in cmds)


class TestMemoryCommandGenerator:
    def test_generates_memory_commands(self):
        gen = MemoryCommandGenerator()
        cmds = gen.generate(_make_parsed())
        assert len(cmds) >= 1
        assert all(not c.is_dangerous for c in cmds)


class TestUptimeCommandGenerator:
    def test_generates_uptime(self):
        gen = UptimeCommandGenerator()
        cmds = gen.generate(_make_parsed())
        assert any("uptime" in c.command for c in cmds)


class TestWhoamiCommandGenerator:
    def test_generates_whoami(self):
        gen = WhoamiCommandGenerator()
        cmds = gen.generate(_make_parsed())
        assert any("whoami" in c.command for c in cmds)


class TestNetworkCommandGenerator:
    def test_generates_network(self):
        gen = NetworkCommandGenerator()
        cmds = gen.generate(_make_parsed(raw_query="show network"))
        assert len(cmds) >= 1

    def test_port_query(self):
        gen = NetworkCommandGenerator()
        cmds = gen.generate(_make_parsed(raw_query="show port usage"))
        assert len(cmds) >= 1


class TestArchiveCommandGenerator:
    def test_compress(self):
        gen = ArchiveCommandGenerator()
        cmds = gen.generate(_make_parsed(action="archive", raw_query="compress the folder"))
        assert any("tar" in c.command for c in cmds)
        assert any("-c" in c.command for c in cmds)

    def test_extract(self):
        gen = ArchiveCommandGenerator()
        cmds = gen.generate(_make_parsed(action="archive", path="archive.tar.gz",
                                         raw_query="extract archive.tar.gz"))
        assert any("-x" in c.command for c in cmds)


# ---------------------------------------------------------------------------
# FallbackCommandGenerator
# ---------------------------------------------------------------------------

class TestFallbackCommandGenerator:
    def setup_method(self):
        self.gen = FallbackCommandGenerator()

    def test_no_context_gives_examples(self):
        p = _make_parsed(raw_query="hello world")
        cmds = self.gen.generate(p)
        assert len(cmds) >= 1
        assert any("# Try:" in c.command for c in cmds)

    def test_partial_file_type(self):
        p = _make_parsed(file_types=["py"], raw_query="something about python")
        cmds = self.gen.generate(p)
        assert len(cmds) >= 1
        assert any(".py" in c.command or "py" in c.command for c in cmds)

    def test_partial_search_pattern(self):
        p = _make_parsed(search_pattern="error", search_pattern_original="ERROR",
                         raw_query="something with error")
        cmds = self.gen.generate(p)
        assert any("grep" in c.command or "ERROR" in c.command for c in cmds)

    def test_partial_path(self):
        p = _make_parsed(path="/tmp", raw_query="something in tmp")
        cmds = self.gen.generate(p)
        assert any("/tmp" in c.command for c in cmds)

    def test_partial_time(self):
        p = _make_parsed(time_minutes=30, raw_query="something recent")
        cmds = self.gen.generate(p)
        assert any("-mmin" in c.command for c in cmds)


# ---------------------------------------------------------------------------
# CommandGeneratorRegistry
# ---------------------------------------------------------------------------

class TestCommandGeneratorRegistry:
    def test_register_and_dispatch(self):
        registry = CommandGeneratorRegistry()
        gen = FindCommandGenerator()
        registry.register("find", gen)
        p = _make_parsed(action="find", file_types=["py"])
        cmds = registry.generate(p)
        assert len(cmds) >= 1

    def test_fallback_on_unknown_action(self):
        registry = CommandGeneratorRegistry()
        registry.set_fallback(FallbackCommandGenerator())
        p = _make_parsed(action="unknown_action", raw_query="some nonsense")
        cmds = registry.generate(p)
        assert len(cmds) >= 1

    def test_fallback_on_no_action(self):
        registry = CommandGeneratorRegistry()
        registry.set_fallback(FallbackCommandGenerator())
        p = _make_parsed(raw_query="hello")
        cmds = registry.generate(p)
        assert len(cmds) >= 1

    def test_register_many(self):
        registry = CommandGeneratorRegistry()
        gen = FindCommandGenerator()
        registry.register_many(["find", "locate"], gen)
        p = _make_parsed(action="locate", file_types=["py"])
        cmds = registry.generate(p)
        assert len(cmds) >= 1
