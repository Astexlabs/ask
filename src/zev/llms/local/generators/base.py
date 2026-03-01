"""Base command generator and registry."""

from typing import Dict, List, Optional, Type

from zev.llms.local.parser import ParsedQuery
from zev.llms.types import Command


class CommandGenerator:
    """Base class for all command generators.

    Subclasses must implement ``generate(parsed)`` which returns a list of
    ``Command`` objects (may be empty if this generator doesn't apply).
    """

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        raise NotImplementedError


class CommandGeneratorRegistry:
    """Maps action names to generator instances and dispatches generation."""

    def __init__(self) -> None:
        self._action_map: Dict[str, CommandGenerator] = {}
        self._fallback: Optional[CommandGenerator] = None

    def register(self, action: str, generator: CommandGenerator) -> None:
        self._action_map[action] = generator

    def register_many(self, actions: List[str], generator: CommandGenerator) -> None:
        for action in actions:
            self._action_map[action] = generator

    def set_fallback(self, generator: CommandGenerator) -> None:
        self._fallback = generator

    def generate(self, parsed: ParsedQuery) -> List[Command]:
        if parsed.action and parsed.action in self._action_map:
            commands = self._action_map[parsed.action].generate(parsed)
            if commands:
                return commands

        # If no action matched or generator returned nothing, try fallback
        if self._fallback is not None:
            return self._fallback.generate(parsed)

        return []
