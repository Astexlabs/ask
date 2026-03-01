"""Tests for the clipboard helper in command_selector."""

import sys
from unittest.mock import MagicMock, call, patch

import pytest

from ask.command_selector import _copy_to_clipboard, handle_selected_option
from ask.llms.types import Command


class TestCopyToClipboard:
    def test_returns_true_when_tool_succeeds(self):
        with patch("shutil.which", return_value="/usr/bin/wl-copy"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert _copy_to_clipboard("echo hello") is True

    def test_returns_false_when_no_tool_found_and_pyperclip_fails(self):
        with patch("shutil.which", return_value=None), \
             patch.dict("sys.modules", {"pyperclip": None}):
            assert _copy_to_clipboard("some command") is False

    def test_falls_back_to_next_tool_on_subprocess_error(self):
        call_count = [0]

        def fake_which(name):
            return f"/usr/bin/{name}"

        def fake_run(cmd, **kwargs):
            call_count[0] += 1
            if cmd[0] == "wl-copy":
                raise OSError("not found")
            mock = MagicMock()
            mock.returncode = 0
            return mock

        with patch("shutil.which", side_effect=fake_which), \
             patch("subprocess.run", side_effect=fake_run):
            result = _copy_to_clipboard("ls -la")
        assert result is True
        assert call_count[0] >= 2

    def test_pyperclip_used_as_last_resort(self):
        mock_pyperclip = MagicMock()
        mock_pyperclip.copy = MagicMock()

        with patch("shutil.which", return_value=None), \
             patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            result = _copy_to_clipboard("df -h")

        assert result is True
        mock_pyperclip.copy.assert_called_once_with("df -h")

    def test_pyperclip_exception_returns_false(self):
        import importlib
        mock_pyperclip = MagicMock()
        mock_pyperclip.copy.side_effect = Exception("no clipboard")

        with patch("shutil.which", return_value=None), \
             patch.dict("sys.modules", {"pyperclip": mock_pyperclip}):
            result = _copy_to_clipboard("df -h")

        assert result is False

    def test_correct_candidates_on_linux(self):
        captured_cmds = []

        def fake_which(name):
            return f"/usr/bin/{name}" if name == "xclip" else None

        def fake_run(cmd, **kwargs):
            captured_cmds.append(cmd[0])
            mock = MagicMock()
            mock.returncode = 0
            return mock

        with patch("sys.platform", "linux"), \
             patch("shutil.which", side_effect=fake_which), \
             patch("subprocess.run", side_effect=fake_run):
            result = _copy_to_clipboard("uptime")

        assert result is True
        assert "xclip" in captured_cmds

    def test_uses_pbcopy_on_macos(self):
        captured = []

        def fake_which(name):
            return "/usr/bin/pbcopy" if name == "pbcopy" else None

        def fake_run(cmd, **kwargs):
            captured.append(cmd[0])
            mock = MagicMock()
            mock.returncode = 0
            return mock

        with patch("sys.platform", "darwin"), \
             patch("shutil.which", side_effect=fake_which), \
             patch("subprocess.run", side_effect=fake_run):
            result = _copy_to_clipboard("ps aux")

        assert result is True
        assert captured == ["pbcopy"]

    def test_uses_clip_on_windows(self):
        captured = []

        def fake_which(name):
            return "C:\\Windows\\System32\\clip.exe" if name == "clip" else None

        def fake_run(cmd, **kwargs):
            captured.append(cmd[0])
            mock = MagicMock()
            mock.returncode = 0
            return mock

        with patch("sys.platform", "win32"), \
             patch("shutil.which", side_effect=fake_which), \
             patch("subprocess.run", side_effect=fake_run):
            result = _copy_to_clipboard("dir")

        assert result is True
        assert captured == ["clip"]

    def test_text_is_encoded_as_bytes_for_subprocess(self):
        received_input = []

        def fake_which(name):
            return "/usr/bin/wl-copy"

        def fake_run(cmd, input=None, **kwargs):
            received_input.append(input)
            mock = MagicMock()
            mock.returncode = 0
            return mock

        with patch("sys.platform", "linux"), \
             patch("shutil.which", side_effect=fake_which), \
             patch("subprocess.run", side_effect=fake_run):
            _copy_to_clipboard("find . -name *.py")

        assert received_input[0] == b"find . -name *.py"

    def test_unicode_text_encoded_correctly(self):
        received_input = []

        def fake_which(name):
            return "/usr/bin/wl-copy"

        def fake_run(cmd, input=None, **kwargs):
            received_input.append(input)
            mock = MagicMock()
            mock.returncode = 0
            return mock

        with patch("sys.platform", "linux"), \
             patch("shutil.which", side_effect=fake_which), \
             patch("subprocess.run", side_effect=fake_run):
            _copy_to_clipboard("echo \u4e2d\u6587")

        assert received_input[0] == "echo \u4e2d\u6587".encode()

    def test_wsl_clip_exe_absence_does_not_crash(self):
        """Regression: pyperclip auto-detects WSL and tries clip.exe; our helper must not."""
        with patch("sys.platform", "linux"), \
             patch("shutil.which", return_value=None), \
             patch.dict("sys.modules", {"pyperclip": None}):
            result = _copy_to_clipboard("ls -la")
        assert result is False


class TestHandleSelectedOptionClipboard:
    def _make_command(self, cmd="ls -la", dangerous=False, dangerous_explanation=None):
        return Command(
            command=cmd,
            short_explanation="list files",
            is_dangerous=dangerous,
            dangerous_explanation=dangerous_explanation,
        )

    def test_shows_hint_when_clipboard_fails(self, capsys):
        cmd = self._make_command()

        with patch("ask.command_selector._copy_to_clipboard", return_value=False), \
             patch("questionary.select") as mock_select:
            mock_select.return_value.ask.return_value = "done"
            handle_selected_option(cmd)

        captured = capsys.readouterr()
        assert "wl-clipboard" in captured.out or "xclip" in captured.out or "Could not copy" in captured.out

    def test_shows_copied_message_on_success(self, capsys):
        cmd = self._make_command()

        with patch("ask.command_selector._copy_to_clipboard", return_value=True), \
             patch("questionary.select") as mock_select:
            mock_select.return_value.ask.return_value = "done"
            handle_selected_option(cmd)

        captured = capsys.readouterr()
        assert "Copied" in captured.out or "copied" in captured.out

    def test_cancel_returns_immediately(self):
        with patch("ask.command_selector._copy_to_clipboard") as mock_clip:
            handle_selected_option(None)
            mock_clip.assert_not_called()

        with patch("ask.command_selector._copy_to_clipboard") as mock_clip:
            handle_selected_option("Cancel")
            mock_clip.assert_not_called()

    def test_dangerous_command_shows_warning(self, capsys):
        cmd = self._make_command(dangerous=True, dangerous_explanation="deletes files")

        with patch("ask.command_selector._copy_to_clipboard", return_value=True), \
             patch("questionary.select") as mock_select, \
             patch("questionary.confirm") as mock_confirm:
            mock_select.return_value.ask.return_value = "run"
            mock_confirm.return_value.ask.return_value = False
            handle_selected_option(cmd)

        captured = capsys.readouterr()
        assert "deletes files" in captured.out
