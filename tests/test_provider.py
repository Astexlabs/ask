"""Tests for the LocalProvider (end-to-end integration)."""

import pytest

from zev.llms.local.provider import LocalProvider


class TestLocalProvider:
    def setup_method(self):
        self.provider = LocalProvider()

    def test_find_py_files(self):
        resp = self.provider.get_options("find python files", "OS: Linux\nSHELL: /bin/bash")
        assert resp is not None
        assert resp.is_valid is True
        assert len(resp.commands) >= 1
        assert any("find" in c.command for c in resp.commands)
        assert any(".py" in c.command and "*" in c.command for c in resp.commands)

    def test_grep_todo(self):
        resp = self.provider.get_options("search for 'TODO' in js files", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        assert any("grep" in c.command for c in resp.commands)

    def test_delete_generates_safe_preview(self):
        resp = self.provider.get_options("delete log files in /var/log", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        # First command should be safe preview
        assert resp.commands[0].is_dangerous is False
        # Should have a dangerous delete option
        dangerous = [c for c in resp.commands if c.is_dangerous]
        assert len(dangerous) >= 1
        assert all(c.dangerous_explanation for c in dangerous)

    def test_kill_process(self):
        resp = self.provider.get_options("kill the node process", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        assert resp.commands[0].is_dangerous is False  # preview first
        assert any(c.is_dangerous for c in resp.commands)

    def test_empty_prompt(self):
        resp = self.provider.get_options("", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is False

    def test_whitespace_only_prompt(self):
        resp = self.provider.get_options("   ", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is False

    def test_disk_usage(self):
        resp = self.provider.get_options("check disk space", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        assert any("df" in c.command for c in resp.commands)

    def test_show_processes(self):
        resp = self.provider.get_options("show running processes", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        assert any("ps" in c.command for c in resp.commands)

    def test_find_recent_files(self):
        resp = self.provider.get_options("find py files from the last hour", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        assert any("-mmin" in c.command for c in resp.commands)

    def test_copy_files(self):
        resp = self.provider.get_options("copy py files to /backup", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        assert any("cp" in c.command or "rsync" in c.command for c in resp.commands)

    def test_count_files(self):
        resp = self.provider.get_options("how many python files are there", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        assert any("wc" in c.command for c in resp.commands)

    def test_unrecognized_query_uses_fallback(self):
        resp = self.provider.get_options("something completely random", "OS: Linux")
        assert resp is not None
        # May be valid (fallback gives suggestions) or invalid
        if resp.is_valid:
            assert len(resp.commands) >= 1

    def test_uptime(self):
        resp = self.provider.get_options("show uptime", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        assert any("uptime" in c.command for c in resp.commands)

    def test_network_ports(self):
        resp = self.provider.get_options("show listening ports", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True

    def test_replace_gives_preview_first(self):
        resp = self.provider.get_options("replace 'foo' with bar in py files", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        assert resp.commands[0].is_dangerous is False

    def test_archive(self):
        resp = self.provider.get_options("compress the ./src folder", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        assert any("tar" in c.command for c in resp.commands)

    def test_max_three_commands(self):
        resp = self.provider.get_options("find python files from the last hour in /tmp", "OS: Linux")
        assert resp is not None
        assert len(resp.commands) <= 3

    def test_permissions(self):
        resp = self.provider.get_options("make script.sh executable", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        assert any("chmod" in c.command for c in resp.commands)

    def test_memory_usage(self):
        resp = self.provider.get_options("show memory usage", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True

    def test_large_files(self):
        resp = self.provider.get_options("find files larger than 100MB", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        assert any("-size" in c.command for c in resp.commands)

    def test_whoami(self):
        resp = self.provider.get_options("who am i", "OS: Linux")
        assert resp is not None
        assert resp.is_valid is True
        assert any("whoami" in c.command or "id" in c.command for c in resp.commands)
