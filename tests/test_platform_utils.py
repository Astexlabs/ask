"""Tests for cross-platform utilities."""

import platform
from unittest.mock import patch

import pytest

from zev.llms.local.platform_utils import (
    find_mtime_days_flag,
    find_mtime_flag,
    get_platform_info,
    is_linux,
    is_macos,
    ps_sort_cpu_flag,
    ps_sort_memory_flag,
    stat_mod_time_flag,
    stat_size_flag,
)


class TestPlatformDetection:
    @patch("zev.llms.local.platform_utils._platform.system", return_value="Darwin")
    def test_is_macos(self, mock_system):
        assert is_macos() is True
        assert is_linux() is False

    @patch("zev.llms.local.platform_utils._platform.system", return_value="Linux")
    def test_is_linux(self, mock_system):
        assert is_linux() is True
        assert is_macos() is False


class TestStatFlags:
    @patch("zev.llms.local.platform_utils._platform.system", return_value="Linux")
    def test_stat_mod_time_linux(self, mock):
        result = stat_mod_time_flag()
        assert "--format" in result
        assert "%Y" in result

    @patch("zev.llms.local.platform_utils._platform.system", return_value="Darwin")
    def test_stat_mod_time_macos(self, mock):
        result = stat_mod_time_flag()
        assert "-f" in result
        assert "%m" in result

    @patch("zev.llms.local.platform_utils._platform.system", return_value="Linux")
    def test_stat_size_linux(self, mock):
        result = stat_size_flag()
        assert "--format" in result
        assert "%s" in result

    @patch("zev.llms.local.platform_utils._platform.system", return_value="Darwin")
    def test_stat_size_macos(self, mock):
        result = stat_size_flag()
        assert "-f" in result
        assert "%z" in result


class TestFindFlags:
    def test_mtime_minutes(self):
        assert find_mtime_flag(30) == "-mmin -30"

    def test_mtime_days(self):
        assert find_mtime_days_flag(7) == "-mtime -7"


class TestPsFlags:
    @patch("zev.llms.local.platform_utils._platform.system", return_value="Linux")
    def test_ps_memory_linux(self, mock):
        result = ps_sort_memory_flag()
        assert "--sort=-%mem" in result

    @patch("zev.llms.local.platform_utils._platform.system", return_value="Darwin")
    def test_ps_memory_macos(self, mock):
        result = ps_sort_memory_flag()
        assert "-m" in result

    @patch("zev.llms.local.platform_utils._platform.system", return_value="Linux")
    def test_ps_cpu_linux(self, mock):
        result = ps_sort_cpu_flag()
        assert "--sort=-%cpu" in result

    @patch("zev.llms.local.platform_utils._platform.system", return_value="Darwin")
    def test_ps_cpu_macos(self, mock):
        result = ps_sort_cpu_flag()
        assert "-r" in result


class TestGetPlatformInfo:
    def test_returns_dict(self):
        info = get_platform_info()
        assert "system" in info
        assert "release" in info
        assert "machine" in info
        assert isinstance(info["system"], str)
