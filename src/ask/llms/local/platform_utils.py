"""Cross-platform utility for GNU vs BSD command flag differences."""

import platform as _platform
from typing import Dict


def is_macos() -> bool:
    return _platform.system() == "Darwin"


def is_linux() -> bool:
    return _platform.system() == "Linux"


def stat_mod_time_flag() -> str:
    """Return the stat flag for modification time (epoch seconds)."""
    if is_macos():
        return 'stat -f "%m %N"'
    return 'stat --format="%Y %n"'


def stat_size_flag() -> str:
    """Return the stat flag for file size in bytes."""
    if is_macos():
        return 'stat -f "%z %N"'
    return 'stat --format="%s %n"'


def find_mtime_flag(minutes: int) -> str:
    """Return find -mmin flag. Both GNU and BSD use the same syntax."""
    return f"-mmin -{minutes}"


def find_mtime_days_flag(days: int) -> str:
    """Return find -mtime flag. Both GNU and BSD use the same syntax."""
    return f"-mtime -{days}"


def ps_sort_memory_flag() -> str:
    """Return ps flags for sorting by memory."""
    if is_macos():
        return "ps aux -m"
    return "ps aux --sort=-%mem"


def ps_sort_cpu_flag() -> str:
    """Return ps flags for sorting by CPU."""
    if is_macos():
        return "ps aux -r"
    return "ps aux --sort=-%cpu"


def du_human_sort_flags() -> str:
    """Return du flags for human-readable sorted output."""
    if is_macos():
        return "du -sh"
    return "du -sh"


def xargs_null_flag() -> str:
    """Return xargs null-delimiter flag (POSIX-compatible)."""
    return "xargs -0"


def get_platform_info() -> Dict[str, str]:
    """Return a dict of platform info for context."""
    return {
        "system": _platform.system(),
        "release": _platform.release(),
        "machine": _platform.machine(),
    }
