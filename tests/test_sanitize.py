"""Tests for shell sanitization utilities."""

import shlex

import pytest

from zev.llms.local.sanitize import quote_path, quote_pattern


class TestQuotePath:
    def test_simple_path(self):
        result = quote_path("/tmp/foo")
        # Must produce a value that the shell would interpret as /tmp/foo
        assert "tmp/foo" in result

    def test_path_with_spaces(self):
        result = quote_path("/tmp/my dir/file")
        # The space must be safely handled (quoted or escaped)
        assert result == shlex.quote("/tmp/my dir/file")

    def test_empty_path(self):
        assert quote_path("") == "''"

    def test_path_with_semicolon(self):
        result = quote_path("/tmp/foo;rm -rf /")
        # Must neutralize the semicolon injection
        assert result == shlex.quote("/tmp/foo;rm -rf /")

    def test_path_with_backtick(self):
        result = quote_path("/tmp/`whoami`")
        assert result == shlex.quote("/tmp/`whoami`")


class TestQuotePattern:
    def test_simple_pattern_no_glob(self):
        result = quote_pattern("hello")
        # Must equal shlex.quote output (which may or may not have quotes
        # depending on Python version)
        assert result == shlex.quote("hello")

    def test_glob_star_preserved(self):
        result = quote_pattern("*.py")
        # The * must be present and the extension preserved
        assert "*" in result
        assert ".py" in result

    def test_glob_question_preserved(self):
        result = quote_pattern("file?.txt")
        assert "?" in result
        assert "txt" in result

    def test_mixed_glob(self):
        result = quote_pattern("*.log?")
        assert "*" in result
        assert "?" in result

    def test_no_glob_uses_shlex(self):
        result = quote_pattern("README.md")
        assert result == shlex.quote("README.md")

    def test_empty(self):
        assert quote_pattern("") == "''"

    def test_injection_attempt(self):
        result = quote_pattern("*.py; rm -rf /")
        # The * must be present
        assert "*" in result
        # The dangerous part must be safely quoted (shlex handles it)
        # Verify it would not execute as a separate command
        # The semicolon and rm should be inside quotes
        assert "; rm -rf /" not in result or result.count("'") >= 2

    def test_safe_glob_no_unnecessary_quotes(self):
        # On modern Python, *.py shouldn't have extra quotes around .py
        result = quote_pattern("*.py")
        # Regardless of quoting style, shell should expand to *.py
        stripped = result.replace("'", "")
        assert stripped == "*.py"
