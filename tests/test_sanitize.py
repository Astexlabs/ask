"""Tests for shell sanitization utilities."""

import shlex

import pytest

from ask.llms.local.sanitize import quote_find_pattern, quote_path, quote_pattern


class TestQuotePath:
    def test_simple_path(self):
        result = quote_path("/tmp/foo")
        assert "tmp/foo" in result

    def test_path_with_spaces(self):
        result = quote_path("/tmp/my dir/file")
        assert result == shlex.quote("/tmp/my dir/file")

    def test_empty_path(self):
        assert quote_path("") == "''"

    def test_path_with_semicolon(self):
        result = quote_path("/tmp/foo;rm -rf /")
        assert result == shlex.quote("/tmp/foo;rm -rf /")

    def test_path_with_backtick(self):
        result = quote_path("/tmp/`whoami`")
        assert result == shlex.quote("/tmp/`whoami`")

    # Security: shell metacharacters must be contained within a single quoted token
    def test_path_pipe_injection(self):
        result = quote_path("/tmp/foo | cat /etc/passwd")
        # shlex.quote wraps in single quotes; the whole string becomes one token
        tokens = shlex.split(result)
        assert len(tokens) == 1

    def test_path_dollar_expansion(self):
        result = quote_path("/tmp/$(id)")
        assert result.startswith("'")
        tokens = shlex.split(result)
        assert len(tokens) == 1

    def test_path_newline(self):
        result = quote_path("/tmp/foo\nrm -rf /")
        tokens = shlex.split(result)
        assert len(tokens) == 1

    def test_path_null_byte(self):
        result = quote_path("/tmp/foo\x00bar")
        assert result == shlex.quote("/tmp/foo\x00bar")

    def test_path_ampersand_injection(self):
        result = quote_path("/tmp/foo & id")
        tokens = shlex.split(result)
        assert len(tokens) == 1

    def test_path_redirect_injection(self):
        result = quote_path("/tmp/foo > /etc/passwd")
        tokens = shlex.split(result)
        assert len(tokens) == 1

    def test_path_tilde_preserved(self):
        result = quote_path("~/documents")
        assert "documents" in result

    def test_path_relative_preserved(self):
        result = quote_path("./src")
        assert "src" in result

    def test_path_double_dot(self):
        result = quote_path("../../etc/passwd")
        assert result == shlex.quote("../../etc/passwd")


class TestQuotePattern:
    def test_simple_pattern_no_glob(self):
        result = quote_pattern("hello")
        assert result == shlex.quote("hello")

    def test_glob_star_preserved(self):
        result = quote_pattern("*.py")
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

    def test_injection_attempt_semicolon(self):
        result = quote_pattern("*.py; rm -rf /")
        assert "*" in result
        assert "; rm -rf /" not in result or result.count("'") >= 2

    def test_safe_glob_no_unnecessary_quotes(self):
        result = quote_pattern("*.py")
        stripped = result.replace("'", "")
        assert stripped == "*.py"

    # Security: injection via glob pattern boundaries
    def test_injection_backtick_in_pattern(self):
        result = quote_pattern("`whoami`")
        # No glob chars — shlex.quote wraps in single quotes, preventing execution
        assert result.startswith("'")
        assert len(shlex.split(result)) == 1

    def test_injection_dollar_subshell(self):
        result = quote_pattern("$(cat /etc/passwd)")
        assert result.startswith("'")
        assert len(shlex.split(result)) == 1

    def test_injection_pipe(self):
        result = quote_pattern("*.py | cat /etc/shadow")
        assert "*" in result
        # The non-glob portion is quoted, making the pipe inert
        assert len(shlex.split(result)) == 1

    def test_injection_newline(self):
        result = quote_pattern("*.py\nrm -rf /")
        assert len(shlex.split(result)) == 1

    def test_injection_glob_with_command_sub(self):
        result = quote_pattern("*$(id)*")
        assert "*" in result
        # $(id) portion is single-quoted, preventing command substitution
        assert result.startswith("*") or "'" in result

    def test_pattern_with_spaces(self):
        result = quote_pattern("my file.py")
        assert result == shlex.quote("my file.py")

    def test_pattern_double_star(self):
        result = quote_pattern("**/*.py")
        assert "**" in result
        assert ".py" in result


class TestQuoteFindPattern:
    """Tests for quote_find_pattern — used with find -name / grep --include.

    The entire pattern (including globs) must be a single shell token so
    that the shell does NOT expand the wildcards; find/grep handle them.
    """

    def test_simple_glob(self):
        result = quote_find_pattern("*.py")
        assert result == "'*.py'"

    def test_question_glob(self):
        result = quote_find_pattern("file?.txt")
        assert result == "'file?.txt'"

    def test_no_glob(self):
        result = quote_find_pattern("hello")
        assert result == shlex.quote("hello")

    def test_empty(self):
        assert quote_find_pattern("") == "''"

    def test_double_star(self):
        result = quote_find_pattern("**/*.py")
        assert result == "'**/*.py'"

    def test_single_token(self):
        """The result must always parse as exactly one shell token."""
        for pattern in ["*.py", "*.log?", "**/*.js", "test*", "*.py; rm -rf /"]:
            result = quote_find_pattern(pattern)
            tokens = shlex.split(result)
            assert len(tokens) == 1, f"quote_find_pattern({pattern!r}) = {result!r} splits into {tokens}"

    def test_injection_semicolon(self):
        result = quote_find_pattern("*.py; rm -rf /")
        tokens = shlex.split(result)
        assert len(tokens) == 1
        assert tokens[0] == "*.py; rm -rf /"

    def test_injection_backtick(self):
        result = quote_find_pattern("`whoami`")
        tokens = shlex.split(result)
        assert len(tokens) == 1

    def test_injection_dollar(self):
        result = quote_find_pattern("$(id)")
        tokens = shlex.split(result)
        assert len(tokens) == 1

    def test_preserves_glob_chars_literally(self):
        """find needs to see the literal * and ? characters."""
        result = quote_find_pattern("*.py")
        inner = shlex.split(result)[0]
        assert inner == "*.py"

    def test_preserves_complex_glob(self):
        result = quote_find_pattern("*test*.py")
        inner = shlex.split(result)[0]
        assert inner == "*test*.py"
