"""Interactive TUI for ask --config.

Presents the full list of configurable settings in a Rich table, lets the
user pick a setting to edit, masks API keys on display, and persists
changes to ~/.askrc immediately.
"""

from typing import List, Optional

import questionary
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ask.config import (
    CONFIG_LABELS,
    GENERAL_KEYS,
    PROVIDER_KEYS,
    SECRET_KEYS,
    config,
    mask_secret,
)
from ask.constants import (
    DEFAULT_HISTORY_SIZE,
    DEFAULT_MAX_COMMANDS,
    GEMINI_DEFAULT_MODEL,
    LLMProviders,
    OPENAI_DEFAULT_MODEL,
)

_STYLE = questionary.Style(
    [
        ("answer", "fg:#61afef"),
        ("question", "bold"),
        ("instruction", "fg:#98c379"),
    ]
)

# Available providers for the provider-switch menu
_PROVIDER_CHOICES = [
    questionary.Choice("OpenAI", value=LLMProviders.OPENAI),
    questionary.Choice("Ollama", value=LLMProviders.OLLAMA),
    questionary.Choice("Gemini", value=LLMProviders.GEMINI),
    questionary.Choice("Azure OpenAI", value=LLMProviders.AZURE_OPENAI),
    questionary.Choice("Local (offline)", value=LLMProviders.LOCAL),
]

# Model presets per provider (for select-style editing)
_MODEL_OPTIONS = {
    "OPENAI_MODEL": [
        questionary.Choice("gpt-4o-mini", value="gpt-4o-mini"),
        questionary.Choice("gpt-4o", value="gpt-4o"),
    ],
    "GEMINI_MODEL": [
        questionary.Choice("gemini-2.0-flash", value="gemini-2.0-flash"),
        questionary.Choice("gemini-1.5-flash", value="gemini-1.5-flash"),
    ],
}


def _display_value(key: str, value: Optional[str]) -> str:
    """Return the display string for a config value, masking secrets."""
    if not value:
        return "[dim](not set)[/dim]"
    if key in SECRET_KEYS:
        return mask_secret(value)
    return value


def _build_settings_table() -> Table:
    """Build a Rich Table showing every relevant setting."""
    table = Table(
        title="",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        pad_edge=True,
        expand=True,
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("Setting", style="bold")
    table.add_column("Value", overflow="fold")

    row_keys = _get_visible_keys()
    for idx, key in enumerate(row_keys, 1):
        label = CONFIG_LABELS.get(key, key)
        raw = config.vals.get(key) or ""
        display = _display_value(key, raw)
        table.add_row(str(idx), label, display)

    return table


def _get_visible_keys() -> List[str]:
    """Return the ordered list of config keys to display in the TUI."""
    keys: List[str] = ["LLM_PROVIDER"]

    provider = config.llm_provider or ""
    provider_specific = PROVIDER_KEYS.get(provider, [])
    keys.extend(provider_specific)

    keys.extend(GENERAL_KEYS)
    return keys


def _prompt_new_value(key: str) -> Optional[str]:
    """Prompt the user for a new value for the given config key.

    Returns the new value, or None if the user cancelled.
    """
    label = CONFIG_LABELS.get(key, key)
    current = config.vals.get(key) or ""

    # Provider picker
    if key == "LLM_PROVIDER":
        result = questionary.select(
            f"Select {label}:",
            choices=_PROVIDER_CHOICES,
            style=_STYLE,
        ).ask()
        return result

    # Model picker (if presets exist)
    if key in _MODEL_OPTIONS:
        choices = list(_MODEL_OPTIONS[key])
        choices.append(questionary.Choice("Custom...", value="__custom__"))
        result = questionary.select(
            f"Select {label}:",
            choices=choices,
            style=_STYLE,
        ).ask()
        if result == "__custom__":
            return questionary.text(
                f"Enter custom {label}:",
                default=current,
                style=_STYLE,
            ).ask()
        return result

    # Secret keys — show masked current value as instruction, don't echo it
    # as the default (so they have to paste the whole key fresh)
    if key in SECRET_KEYS:
        masked = mask_secret(current) if current else "(not set)"
        result = questionary.text(
            f"Enter {label}:",
            instruction=f"current: {masked}",
            style=_STYLE,
        ).ask()
        # If user pressed enter without typing, keep current value
        if result is not None and result.strip() == "":
            return current
        return result

    # Default: free-text input
    result = questionary.text(
        f"Enter {label}:",
        default=current,
        style=_STYLE,
    ).ask()
    return result


def _on_provider_changed(old_provider: str, new_provider: str) -> None:
    """When the provider changes, prompt for the new provider's required keys."""
    new_keys = PROVIDER_KEYS.get(new_provider, [])
    if not new_keys:
        return

    rprint(f"\n[bold]Configure {new_provider} settings:[/bold]")
    for key in new_keys:
        value = _prompt_new_value(key)
        if value is not None:
            config.set_val(key, value)


def run_config_tui() -> None:
    """Main entry point for the interactive config TUI."""
    console = Console()

    rprint("")
    rprint(
        Panel(
            "[bold cyan]ask[/bold cyan] [dim]—[/dim] [bold]Settings[/bold]",
            subtitle="[dim]Edit any setting below, changes save instantly[/dim]",
            border_style="cyan",
            expand=False,
            padding=(0, 2),
        )
    )

    while True:
        rprint("")
        console.print(_build_settings_table())
        rprint("")

        visible_keys = _get_visible_keys()
        choices = [
            questionary.Choice(CONFIG_LABELS.get(k, k), value=k)
            for k in visible_keys
        ]
        choices.append(questionary.Separator())
        choices.append(questionary.Choice("Done", value="__done__"))

        selected_key = questionary.select(
            "Edit a setting:",
            choices=choices,
            style=_STYLE,
        ).ask()

        if selected_key is None or selected_key == "__done__":
            rprint("[green]>[/green] Settings saved.\n")
            config.reload()
            return

        old_value = config.vals.get(selected_key, "")
        new_value = _prompt_new_value(selected_key)

        if new_value is None:
            # User cancelled this edit
            continue

        config.set_val(selected_key, new_value)

        # If provider changed, prompt for new provider's settings
        if selected_key == "LLM_PROVIDER" and new_value != old_value:
            _on_provider_changed(old_value or "", new_value)

        label = CONFIG_LABELS.get(selected_key, selected_key)
        if selected_key in SECRET_KEYS:
            rprint(f"[green]>[/green] {label} updated to {mask_secret(new_value)}")
        else:
            rprint(f"[green]>[/green] {label} updated to [bold]{new_value}[/bold]")
