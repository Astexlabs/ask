"""Tests for the modular query parser and individual extractors."""

import pytest

from ask.llms.local.parser import (
    ActionExtractor,
    CountExtractor,
    DepthExtractor,
    DestinationExtractor,
    FileTypeExtractor,
    ParsedQuery,
    PathExtractor,
    ProcessExtractor,
    QueryParser,
    SearchPatternExtractor,
    SizeExtractor,
    TimeWindowExtractor,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract(extractor_class, query: str) -> ParsedQuery:
    """Run a single extractor against a query and return the ParsedQuery."""
    parsed = ParsedQuery(raw_query=query.lower(), raw_query_original=query)
    extractor_class().extract(query.lower(), query, parsed)
    return parsed


# ---------------------------------------------------------------------------
# ActionExtractor
# ---------------------------------------------------------------------------

class TestActionExtractor:
    def test_find_files(self):
        p = _extract(ActionExtractor, "find all python files")
        assert p.action == "find"

    def test_look_for(self):
        p = _extract(ActionExtractor, "look for log files")
        assert p.action == "find"

    def test_search_inside(self):
        p = _extract(ActionExtractor, "search for 'TODO' inside files")
        assert p.action == "grep"

    def test_grep_action(self):
        p = _extract(ActionExtractor, "grep for errors in the log")
        assert p.action == "grep"

    def test_delete(self):
        p = _extract(ActionExtractor, "delete all tmp files")
        assert p.action == "delete"

    def test_remove(self):
        p = _extract(ActionExtractor, "remove old log files")
        assert p.action == "delete"

    def test_copy(self):
        p = _extract(ActionExtractor, "copy files to backup")
        assert p.action == "copy"

    def test_move(self):
        p = _extract(ActionExtractor, "move images to /tmp")
        assert p.action == "move"

    def test_replace(self):
        p = _extract(ActionExtractor, "replace foo with bar")
        assert p.action == "replace"

    def test_size(self):
        p = _extract(ActionExtractor, "find largest items")
        assert p.action == "size"

    def test_disk_usage_action(self):
        p = _extract(ActionExtractor, "show disk usage")
        assert p.action == "disk_usage"

    def test_count(self):
        p = _extract(ActionExtractor, "count all py files")
        assert p.action == "count"

    def test_process(self):
        p = _extract(ActionExtractor, "show running processes")
        assert p.action == "process"

    def test_kill(self):
        p = _extract(ActionExtractor, "kill the python process")
        assert p.action == "kill"

    def test_kill_before_process(self):
        p = _extract(ActionExtractor, "kill the node process")
        assert p.action == "kill"

    def test_permissions(self):
        p = _extract(ActionExtractor, "make script.sh executable")
        assert p.action == "permissions"

    def test_archive(self):
        p = _extract(ActionExtractor, "tar the project folder")
        assert p.action == "archive"

    def test_network(self):
        p = _extract(ActionExtractor, "show network interfaces")
        assert p.action == "network"

    def test_disk_usage(self):
        p = _extract(ActionExtractor, "check disk space")
        assert p.action == "disk_usage"

    def test_memory(self):
        p = _extract(ActionExtractor, "show memory usage")
        assert p.action == "memory"

    def test_no_action(self):
        p = _extract(ActionExtractor, "hello world")
        assert p.action is None

    def test_list_files(self):
        p = _extract(ActionExtractor, "list all files in /tmp")
        assert p.action == "find"

    def test_recent_triggers_find(self):
        p = _extract(ActionExtractor, "recently modified log files")
        assert p.action == "find"

    def test_contains_triggers_grep(self):
        p = _extract(ActionExtractor, "files containing error")
        assert p.action == "grep"


# ---------------------------------------------------------------------------
# FileTypeExtractor
# ---------------------------------------------------------------------------

class TestFileTypeExtractor:
    def test_py_extension(self):
        p = _extract(FileTypeExtractor, "find .py files")
        assert "py" in p.file_types

    def test_python_keyword(self):
        p = _extract(FileTypeExtractor, "find python files")
        assert "py" in p.file_types

    def test_javascript_keyword(self):
        p = _extract(FileTypeExtractor, "search javascript files")
        assert "js" in p.file_types

    def test_multiple_types(self):
        p = _extract(FileTypeExtractor, "find .py and .js files")
        assert "py" in p.file_types
        assert "js" in p.file_types

    def test_typescript(self):
        p = _extract(FileTypeExtractor, "look for typescript files")
        assert "ts" in p.file_types

    def test_log_files(self):
        p = _extract(FileTypeExtractor, "find log files")
        assert "log" in p.file_types

    def test_no_file_type(self):
        p = _extract(FileTypeExtractor, "find large files")
        assert p.file_types == []

    def test_golang_maps_to_go(self):
        p = _extract(FileTypeExtractor, "find golang files")
        assert "go" in p.file_types

    def test_markdown_maps_to_md(self):
        p = _extract(FileTypeExtractor, "find markdown files")
        assert "md" in p.file_types

    def test_shell_maps_to_sh(self):
        p = _extract(FileTypeExtractor, "find shell files")
        assert "sh" in p.file_types

    def test_no_duplicates(self):
        p = _extract(FileTypeExtractor, "find py python files")
        assert p.file_types.count("py") == 1


# ---------------------------------------------------------------------------
# TimeWindowExtractor
# ---------------------------------------------------------------------------

class TestTimeWindowExtractor:
    def test_last_hour(self):
        p = _extract(TimeWindowExtractor, "files from the last hour")
        assert p.time_minutes == 60

    def test_last_30_minutes(self):
        p = _extract(TimeWindowExtractor, "modified in the last 30 minutes")
        assert p.time_minutes == 30

    def test_last_2_days(self):
        p = _extract(TimeWindowExtractor, "changed in the last 2 days")
        assert p.time_days == 2

    def test_5_hours_ago(self):
        p = _extract(TimeWindowExtractor, "files 5 hours ago")
        assert p.time_minutes == 300

    def test_today(self):
        p = _extract(TimeWindowExtractor, "files modified today")
        assert p.time_minutes == 1440

    def test_yesterday(self):
        p = _extract(TimeWindowExtractor, "files from yesterday")
        assert p.time_days == 2

    def test_this_week(self):
        p = _extract(TimeWindowExtractor, "files modified this week")
        assert p.time_days == 7

    def test_last_day(self):
        p = _extract(TimeWindowExtractor, "files from the last day")
        assert p.time_days == 1

    def test_no_time(self):
        p = _extract(TimeWindowExtractor, "find python files")
        assert p.time_minutes is None
        assert p.time_days is None

    def test_past_10_minutes(self):
        p = _extract(TimeWindowExtractor, "past 10 minutes")
        assert p.time_minutes == 10


# ---------------------------------------------------------------------------
# PathExtractor
# ---------------------------------------------------------------------------

class TestPathExtractor:
    def test_absolute_path(self):
        p = _extract(PathExtractor, "find files in /var/log")
        assert p.path == "/var/log"

    def test_home_path(self):
        p = _extract(PathExtractor, "search ~/Documents")
        assert p.path == "~/Documents"

    def test_relative_path(self):
        p = _extract(PathExtractor, "find in ./src")
        assert p.path == "./src"

    def test_current_directory(self):
        p = _extract(PathExtractor, "find in the current directory")
        assert p.path == "."

    def test_home_directory(self):
        p = _extract(PathExtractor, "look in the home directory")
        assert p.path == "~"

    def test_no_path(self):
        p = _extract(PathExtractor, "find python files")
        assert p.path is None

    def test_from_path(self):
        p = _extract(PathExtractor, "files from /tmp/data")
        assert p.path == "/tmp/data"


# ---------------------------------------------------------------------------
# SearchPatternExtractor
# ---------------------------------------------------------------------------

class TestSearchPatternExtractor:
    def test_quoted_string(self):
        p = _extract(SearchPatternExtractor, "search for 'TODO' in files")
        # The extractor reads from query_original for quotes
        assert p.search_pattern == "todo"
        assert p.search_pattern_original == "TODO"

    def test_double_quoted(self):
        p = _extract(SearchPatternExtractor, 'search for "ImportError" in py files')
        assert p.search_pattern_original == "ImportError"
        assert p.search_pattern == "importerror"

    def test_named_pattern(self):
        p = _extract(SearchPatternExtractor, "find files named config.yaml")
        assert p.name_pattern == "config.yaml"

    def test_matching_pattern(self):
        p = _extract(SearchPatternExtractor, "find files matching *.log")
        assert p.name_pattern == "*.log"

    def test_no_pattern(self):
        p = _extract(SearchPatternExtractor, "find python files")
        assert p.search_pattern is None
        assert p.name_pattern is None


# ---------------------------------------------------------------------------
# SizeExtractor
# ---------------------------------------------------------------------------

class TestSizeExtractor:
    def test_larger_than(self):
        p = _extract(SizeExtractor, "files larger than 10MB")
        assert p.size_constraint == "+10M"

    def test_smaller_than(self):
        p = _extract(SizeExtractor, "files smaller than 1G")
        assert p.size_constraint == "-1G"

    def test_over(self):
        p = _extract(SizeExtractor, "files over 500K")
        assert p.size_constraint == "+500k"

    def test_no_size(self):
        p = _extract(SizeExtractor, "find python files")
        assert p.size_constraint is None


# ---------------------------------------------------------------------------
# DepthExtractor
# ---------------------------------------------------------------------------

class TestDepthExtractor:
    def test_explicit_depth(self):
        p = _extract(DepthExtractor, "find files depth 3")
        assert p.depth == 3

    def test_non_recursive(self):
        p = _extract(DepthExtractor, "non-recursive file listing")
        assert p.depth == 1

    def test_top_level(self):
        p = _extract(DepthExtractor, "top-level files only")
        assert p.depth == 1

    def test_levels(self):
        p = _extract(DepthExtractor, "search 2 levels deep")
        assert p.depth == 2

    def test_no_depth(self):
        p = _extract(DepthExtractor, "find python files")
        assert p.depth is None


# ---------------------------------------------------------------------------
# ProcessExtractor
# ---------------------------------------------------------------------------

class TestProcessExtractor:
    def test_kill_process(self):
        p = _extract(ProcessExtractor, "kill python")
        assert p.process_name == "python"

    def test_stop_process(self):
        p = _extract(ProcessExtractor, "stop the nginx process")
        assert p.process_name == "nginx"

    def test_signal_extraction(self):
        p = _extract(ProcessExtractor, "kill python sigterm")
        assert p.process_name == "python"
        assert p.signal == "SIGTERM"

    def test_no_process(self):
        p = _extract(ProcessExtractor, "find files")
        assert p.process_name is None


# ---------------------------------------------------------------------------
# CountExtractor
# ---------------------------------------------------------------------------

class TestCountExtractor:
    def test_top_n(self):
        p = _extract(CountExtractor, "top 10 largest files")
        assert p.count == 10

    def test_first_n(self):
        p = _extract(CountExtractor, "first 5 results")
        assert p.count == 5

    def test_n_largest(self):
        p = _extract(CountExtractor, "20 largest files")
        assert p.count == 20

    def test_no_count(self):
        p = _extract(CountExtractor, "find files")
        assert p.count is None


# ---------------------------------------------------------------------------
# DestinationExtractor
# ---------------------------------------------------------------------------

class TestDestinationExtractor:
    def test_to_path(self):
        p = _extract(DestinationExtractor, "copy files to /backup")
        assert p.destination == "/backup"

    def test_into_path(self):
        p = _extract(DestinationExtractor, "move into ~/archive")
        assert p.destination == "~/archive"

    def test_no_destination(self):
        p = _extract(DestinationExtractor, "find python files")
        assert p.destination is None


# ---------------------------------------------------------------------------
# QueryParser (full pipeline)
# ---------------------------------------------------------------------------

class TestQueryParser:
    def setup_method(self):
        self.parser = QueryParser()

    def test_find_py_last_hour(self):
        p = self.parser.parse("find all py files from the last hour")
        assert p.action == "find"
        assert "py" in p.file_types
        assert p.time_minutes == 60

    def test_grep_todo_in_js(self):
        p = self.parser.parse("search for 'TODO' in js files")
        assert p.action == "grep"
        assert "js" in p.file_types
        assert p.search_pattern == "todo"
        assert p.search_pattern_original == "TODO"

    def test_delete_log_older_2_days(self):
        p = self.parser.parse("delete log files from the last 2 days in /var/log")
        assert p.action == "delete"
        assert "log" in p.file_types
        assert p.time_days == 2
        assert p.path == "/var/log"

    def test_copy_to_backup(self):
        p = self.parser.parse("copy .py files to /backup")
        assert p.action == "copy"
        assert "py" in p.file_types
        assert p.destination == "/backup"

    def test_large_files(self):
        p = self.parser.parse("find files larger than 100MB")
        assert p.action == "find"
        assert p.size_constraint == "+100M"

    def test_kill_process(self):
        p = self.parser.parse("kill the node process")
        assert p.action == "kill"
        assert p.process_name == "node"

    def test_raw_query_preserved(self):
        p = self.parser.parse("  Find ALL .PY files  ")
        assert p.raw_query == "find all .py files"
        assert p.raw_query_original == "Find ALL .PY files"

    def test_empty_query(self):
        p = self.parser.parse("")
        assert p.action is None

    def test_disk_space(self):
        p = self.parser.parse("check disk space")
        assert p.action == "disk_usage"

    def test_show_memory(self):
        p = self.parser.parse("show memory usage")
        assert p.action == "memory"

    def test_count_py_files(self):
        p = self.parser.parse("how many python files are there")
        assert p.action == "count"
        assert "py" in p.file_types

    def test_show_processes(self):
        p = self.parser.parse("show running processes")
        assert p.action == "process"

    def test_network_ports(self):
        p = self.parser.parse("show listening ports")
        assert p.action == "network"

    def test_archive_folder(self):
        p = self.parser.parse("compress the ./src folder")
        assert p.action == "archive"
