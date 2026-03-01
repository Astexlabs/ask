import os
import sys
from pathlib import Path

import dotenv
from rich import print as rprint
from rich.console import Console

from ask.command_history import CommandHistory
from ask.command_selector import show_options
from ask.config import config
from ask.config.setup import run_setup
from ask.config.tui import run_config_tui
from ask.constants import CONFIG_FILE_NAME, LLMProviders
from ask.llms.llm import get_inference_provider
from ask.utils import get_env_context, get_input_string, show_help

command_history = CommandHistory()


def setup():
    run_setup()


def _is_local_mode() -> bool:
    """Check whether local mode is active (from config or env)."""
    return (
        config.llm_provider == LLMProviders.LOCAL
        or os.environ.get("LLM_PROVIDER") == LLMProviders.LOCAL
    )


def _ensure_default_local_config(config_path: Path) -> None:
    """Create a minimal .askrc with LLM_PROVIDER=local so the app doesn't
    crash with 'Invalid LLM provider: None' on first run without setup."""
    config_path.write_text("LLM_PROVIDER=local\n", encoding="utf-8")
    dotenv.load_dotenv(config_path, override=True)
    config.reload()


def _show_local_banner() -> None:
    """Print a stylised Local Mode banner."""
    rprint(
        "\n[bold cyan]"
        "  ╭──────────────────────────────────────╮\n"
        "  │     ask · [yellow]Local Mode[/yellow] (offline)      │\n"
        "  │  No API key required — powered by    │\n"
        "  │  local string parsing                │\n"
        "  ╰──────────────────────────────────────╯"
        "[/bold cyan]\n"
    )


def get_options(words: str):
    context = get_env_context()
    console = Console()

    is_local = _is_local_mode()

    if is_local:
        # Local parsing is instantaneous — no spinner needed
        inference_provider = get_inference_provider()
        response = inference_provider.get_options(prompt=words, context=context)
        command_history.save_options(words, response)
    else:
        rprint(f"")
        with console.status(
            f"[bold blue]Thinking... [grey39](running query using {config.llm_provider} backend)", spinner="dots"
        ):
            inference_provider = get_inference_provider()
            response = inference_provider.get_options(prompt=words, context=context)
            command_history.save_options(words, response)

    if response is None:
        return

    if not response.is_valid:
        print(response.explanation_if_not_valid)
        return

    if not response.commands:
        print("No commands available")
        return

    # Respect MAX_COMMANDS setting
    try:
        limit = int(config.max_commands)
    except (ValueError, TypeError):
        limit = 3
    commands = response.commands[:limit] if limit > 0 else response.commands

    show_options(commands)


def run_no_prompt():
    if _is_local_mode():
        _show_local_banner()
    input = get_input_string("input", "Describe what you want to do:", required=False, help_text="(-h for help)")
    if handle_special_case(input):
        return
    get_options(input)


def handle_special_case(args):
    if not args:
        return False

    if isinstance(args, str):
        args = args.split()

    if len(args) > 1:
        return False

    command = args[0].lower()

    if command == "--setup" or command == "-s":
        setup()
        return True

    if command == "--config" or command == "-c":
        run_config_tui()
        return True

    if command == "--version" or command == "-v":
        print("ask version: 0.8.1")
        return True

    if command == "--recent" or command == "-r":
        command_history.show_history()
        return True

    if command == "--help" or command == "-h":
        show_help()
        return True

    return False


def app():
    # check if .askrc exists or if setting up again
    config_path = Path.home() / CONFIG_FILE_NAME
    args = [arg.strip() for arg in sys.argv[1:]]

    if not config_path.exists():
        # First run: if --setup was passed, run the interactive setup wizard.
        # If --config was passed, create a default config then open the TUI.
        # Otherwise, create a default local-mode config so the app works
        # out-of-the-box without crashing.
        is_setup = len(args) == 1 and args[0] in ("--setup", "-s")
        is_config = len(args) == 1 and args[0] in ("--config", "-c")
        if is_setup:
            run_setup()
            print("Setup complete...\n")
            return
        elif is_config:
            _ensure_default_local_config(config_path)
            # Fall through so handle_special_case picks up --config
        else:
            _ensure_default_local_config(config_path)
            rprint(
                "[dim]No config found — defaulting to [bold]Local Mode[/bold]. "
                "Run [bold]ask --setup[/bold] or [bold]ask --config[/bold] to configure.[/dim]\n"
            )

    if handle_special_case(args):
        return

    dotenv.load_dotenv(config_path, override=True)

    if not args:
        run_no_prompt()
        return

    # Strip any trailing question marks from the input
    query = " ".join(args).rstrip("?")
    get_options(query)


if __name__ == "__main__":
    app()
