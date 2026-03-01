"""Generators for system commands: ps, kill, df, free, uptime, whoami, network."""

from typing import List

from zev.llms.local.generators.base import CommandGenerator
from zev.llms.local.parser import ParsedQuery
from zev.llms.local.platform_utils import is_macos, ps_sort_cpu_flag, ps_sort_memory_flag
from zev.llms.local.sanitize import quote_path
from zev.llms.types import Command


class ProcessCommandGenerator(CommandGenerator):
    """Generate ps / pgrep commands for process listing."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []

        if parsed.process_name:
            name = quote_path(parsed.process_name)
            commands.append(Command(
                command=f"pgrep -fl {name}",
                short_explanation=f"Find processes matching '{parsed.process_name}'",
                is_dangerous=False,
            ))
            commands.append(Command(
                command=f"ps aux | grep {name} | grep -v grep",
                short_explanation=f"List processes matching '{parsed.process_name}' with details",
                is_dangerous=False,
            ))
        else:
            # General process listing
            if "memory" in parsed.raw_query or "ram" in parsed.raw_query or "mem" in parsed.raw_query:
                commands.append(Command(
                    command=ps_sort_memory_flag() + " | head -20",
                    short_explanation="Show top processes by memory usage",
                    is_dangerous=False,
                ))
            elif "cpu" in parsed.raw_query:
                commands.append(Command(
                    command=ps_sort_cpu_flag() + " | head -20",
                    short_explanation="Show top processes by CPU usage",
                    is_dangerous=False,
                ))
            else:
                commands.append(Command(
                    command="ps aux | head -20",
                    short_explanation="List running processes (top 20)",
                    is_dangerous=False,
                ))

            commands.append(Command(
                command=ps_sort_cpu_flag() + " | head -10",
                short_explanation="Show top 10 processes by CPU usage",
                is_dangerous=False,
            ))
            commands.append(Command(
                command=ps_sort_memory_flag() + " | head -10",
                short_explanation="Show top 10 processes by memory usage",
                is_dangerous=False,
            ))

        return commands[:3]


class KillCommandGenerator(CommandGenerator):
    """Generate kill / pkill commands."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []

        if parsed.process_name:
            name = quote_path(parsed.process_name)
            signal = parsed.signal or ""
            signal_flag = f" {signal}" if signal else ""

            # Preview first: find matching processes
            commands.append(Command(
                command=f"pgrep -fl {name}",
                short_explanation=f"Preview: find processes matching '{parsed.process_name}'",
                is_dangerous=False,
            ))

            commands.append(Command(
                command=f"pkill{signal_flag} -f {name}",
                short_explanation=f"Kill processes matching '{parsed.process_name}'",
                is_dangerous=True,
                dangerous_explanation=f"Terminates processes matching '{parsed.process_name}'",
            ))

            commands.append(Command(
                command=f"pkill{signal_flag} {name}",
                short_explanation=f"Kill processes named '{parsed.process_name}' (exact name match)",
                is_dangerous=True,
                dangerous_explanation=f"Terminates processes with the exact name '{parsed.process_name}'",
            ))
        else:
            # No process name, provide templates
            commands.append(Command(
                command="ps aux | head -20",
                short_explanation="List running processes to find PID",
                is_dangerous=False,
            ))
            commands.append(Command(
                command="kill PID",
                short_explanation="Send SIGTERM to process (replace PID)",
                is_dangerous=True,
                dangerous_explanation="Terminates the specified process",
            ))
            commands.append(Command(
                command="kill -9 PID",
                short_explanation="Force kill process (replace PID)",
                is_dangerous=True,
                dangerous_explanation="Forcefully terminates the process (SIGKILL, cannot be caught)",
            ))

        return commands[:3]


class DiskUsageCommandGenerator(CommandGenerator):
    """Generate df commands for disk space."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        return [
            Command(
                command="df -h",
                short_explanation="Show disk space usage in human-readable format",
                is_dangerous=False,
            ),
            Command(
                command="df -h .",
                short_explanation="Show disk space for the current filesystem",
                is_dangerous=False,
            ),
            Command(
                command="df -h | sort -k5 -rh",
                short_explanation="Show disk usage sorted by percentage used",
                is_dangerous=False,
            ),
        ]


class MemoryCommandGenerator(CommandGenerator):
    """Generate free / vm_stat commands for memory info."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []

        if is_macos():
            commands.append(Command(
                command="vm_stat",
                short_explanation="Show virtual memory statistics",
                is_dangerous=False,
            ))
            commands.append(Command(
                command="top -l 1 -s 0 | head -12",
                short_explanation="Show memory summary from top",
                is_dangerous=False,
            ))
            commands.append(Command(
                command="sysctl hw.memsize",
                short_explanation="Show total physical memory",
                is_dangerous=False,
            ))
        else:
            commands.append(Command(
                command="free -h",
                short_explanation="Show memory usage in human-readable format",
                is_dangerous=False,
            ))
            commands.append(Command(
                command="cat /proc/meminfo | head -5",
                short_explanation="Show detailed memory info from /proc",
                is_dangerous=False,
            ))
            commands.append(Command(
                command="vmstat -s | head -6",
                short_explanation="Show virtual memory statistics",
                is_dangerous=False,
            ))

        return commands[:3]


class UptimeCommandGenerator(CommandGenerator):
    """Generate uptime commands."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        return [
            Command(
                command="uptime",
                short_explanation="Show system uptime and load averages",
                is_dangerous=False,
            ),
            Command(
                command="who -b",
                short_explanation="Show last system boot time",
                is_dangerous=False,
            ),
        ]


class WhoamiCommandGenerator(CommandGenerator):
    """Generate user identity commands."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        return [
            Command(
                command="whoami",
                short_explanation="Show current username",
                is_dangerous=False,
            ),
            Command(
                command="id",
                short_explanation="Show user ID, group ID, and groups",
                is_dangerous=False,
            ),
        ]


class NetworkCommandGenerator(CommandGenerator):
    """Generate network info commands."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        raw = parsed.raw_query

        if "port" in raw:
            if is_macos():
                commands.append(Command(
                    command="lsof -iTCP -sTCP:LISTEN -P",
                    short_explanation="Show listening TCP ports",
                    is_dangerous=False,
                ))
            else:
                commands.append(Command(
                    command="ss -tlnp",
                    short_explanation="Show listening TCP ports with process info",
                    is_dangerous=False,
                ))
                commands.append(Command(
                    command="netstat -tlnp",
                    short_explanation="Show listening TCP ports (legacy)",
                    is_dangerous=False,
                ))
        elif "ip" in raw or "addr" in raw or "interface" in raw:
            if is_macos():
                commands.append(Command(
                    command="ifconfig",
                    short_explanation="Show network interfaces and IP addresses",
                    is_dangerous=False,
                ))
            else:
                commands.append(Command(
                    command="ip addr show",
                    short_explanation="Show network interfaces and IP addresses",
                    is_dangerous=False,
                ))
                commands.append(Command(
                    command="hostname -I",
                    short_explanation="Show all assigned IP addresses",
                    is_dangerous=False,
                ))
        else:
            if is_macos():
                commands.append(Command(
                    command="ifconfig",
                    short_explanation="Show network interfaces",
                    is_dangerous=False,
                ))
            else:
                commands.append(Command(
                    command="ip addr show",
                    short_explanation="Show network interfaces",
                    is_dangerous=False,
                ))

            commands.append(Command(
                command="ping -c 4 8.8.8.8",
                short_explanation="Test internet connectivity",
                is_dangerous=False,
            ))

        return commands[:3]


class SortCommandGenerator(CommandGenerator):
    """Generate sort commands for file listing by various criteria."""

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        commands: List[Command] = []
        base_path = quote_path(parsed.path) if parsed.path else "."

        if "size" in parsed.raw_query or "largest" in parsed.raw_query or "biggest" in parsed.raw_query:
            commands.append(Command(
                command=f"ls -lhS {base_path}",
                short_explanation=f"List files sorted by size (largest first)",
                is_dangerous=False,
            ))
        elif "time" in parsed.raw_query or "date" in parsed.raw_query or "recent" in parsed.raw_query or "modified" in parsed.raw_query:
            commands.append(Command(
                command=f"ls -lht {base_path}",
                short_explanation=f"List files sorted by modification time (newest first)",
                is_dangerous=False,
            ))
        else:
            commands.append(Command(
                command=f"ls -lh {base_path} | sort",
                short_explanation=f"List files sorted alphabetically",
                is_dangerous=False,
            ))

        commands.append(Command(
            command=f"ls -lhS {base_path}",
            short_explanation=f"List files sorted by size (largest first)",
            is_dangerous=False,
        ))

        commands.append(Command(
            command=f"ls -lht {base_path}",
            short_explanation=f"List files sorted by modification time",
            is_dangerous=False,
        ))

        return commands[:3]
