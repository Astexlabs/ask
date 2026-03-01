"""Local inference provider – no API key, no network, no LLM.

Uses the modular parser and command generator pipeline to convert natural
language queries into shell command candidates.
"""

from typing import Optional

from ask.llms.inference_provider_base import InferenceProvider
from ask.llms.local.generators.base import CommandGeneratorRegistry
from ask.llms.local.generators.discovery import (
    CountCommandGenerator,
    FindCommandGenerator,
    SizeCommandGenerator,
)
from ask.llms.local.generators.fallback import FallbackCommandGenerator
from ask.llms.local.generators.file_ops import (
    ArchiveCommandGenerator,
    ChownCommandGenerator,
    CopyCommandGenerator,
    DeleteCommandGenerator,
    MoveCommandGenerator,
    PermissionsCommandGenerator,
)
from ask.llms.local.generators.search import (
    GrepCommandGenerator,
    ReplaceCommandGenerator,
)
from ask.llms.local.generators.system import (
    DiskUsageCommandGenerator,
    KillCommandGenerator,
    MemoryCommandGenerator,
    NetworkCommandGenerator,
    ProcessCommandGenerator,
    SortCommandGenerator,
    UptimeCommandGenerator,
    WhoamiCommandGenerator,
)
from ask.llms.local.parser import QueryParser
from ask.llms.types import OptionsResponse


def _build_registry() -> CommandGeneratorRegistry:
    """Construct and populate the generator registry."""
    registry = CommandGeneratorRegistry()

    # Discovery
    find_gen = FindCommandGenerator()
    registry.register_many(["find"], find_gen)

    size_gen = SizeCommandGenerator()
    registry.register("size", size_gen)

    count_gen = CountCommandGenerator()
    registry.register("count", count_gen)

    # Search
    grep_gen = GrepCommandGenerator()
    registry.register("grep", grep_gen)

    replace_gen = ReplaceCommandGenerator()
    registry.register("replace", replace_gen)

    # File operations
    registry.register("delete", DeleteCommandGenerator())
    registry.register("copy", CopyCommandGenerator())
    registry.register("move", MoveCommandGenerator())
    registry.register("permissions", PermissionsCommandGenerator())
    registry.register("chown", ChownCommandGenerator())
    registry.register("archive", ArchiveCommandGenerator())

    # System
    registry.register("process", ProcessCommandGenerator())
    registry.register("kill", KillCommandGenerator())
    registry.register("disk_usage", DiskUsageCommandGenerator())
    registry.register("memory", MemoryCommandGenerator())
    registry.register("uptime", UptimeCommandGenerator())
    registry.register("whoami", WhoamiCommandGenerator())
    registry.register("network", NetworkCommandGenerator())
    registry.register("sort", SortCommandGenerator())

    # Fallback
    registry.set_fallback(FallbackCommandGenerator())

    return registry


class LocalProvider(InferenceProvider):
    """Offline provider that parses queries and generates shell commands locally."""

    def __init__(self) -> None:
        self.parser = QueryParser()
        self.registry = _build_registry()

    def get_options(self, prompt: str, context: str) -> Optional[OptionsResponse]:
        if not prompt or not prompt.strip():
            return OptionsResponse(
                commands=[],
                is_valid=False,
                explanation_if_not_valid="Please describe what you want to do.",
            )

        parsed = self.parser.parse(prompt)
        commands = self.registry.generate(parsed)

        if not commands:
            return OptionsResponse(
                commands=[],
                is_valid=False,
                explanation_if_not_valid=(
                    "Could not understand the query. "
                    "Try something like: 'find python files from the last hour' "
                    "or 'search for TODO in js files'."
                ),
            )

        return OptionsResponse(
            commands=commands,
            is_valid=True,
        )
