import shutil
import subprocess
import sys
from subprocess import run as run_command
from typing import List

import questionary
from rich import print as rprint

from ask.llms.types import Command

_SELECT_STYLE = questionary.Style(
    [
        ("answer", "fg:#61afef"),
        ("question", "bold"),
        ("instruction", "fg:#98c379"),
    ]
)


def _copy_to_clipboard(text: str) -> bool:
    """Copy text to the system clipboard without relying on pyperclip's platform detection.

    Tries clipboard backends in order of preference for the current platform,
    then falls back to pyperclip as a last resort.  Returns True on success.
    """
    if sys.platform == "darwin":
        candidates = [["pbcopy"]]
    elif sys.platform == "win32":
        candidates = [["clip"]]
    else:
        candidates = [
            ["wl-copy"],
            ["xclip", "-selection", "clipboard"],
            ["xsel", "--clipboard", "--input"],
        ]

    for cmd in candidates:
        if shutil.which(cmd[0]) is None:
            continue
        try:
            proc = subprocess.run(
                cmd,
                input=text.encode(),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return proc.returncode == 0
        except Exception:
            continue

    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def show_options(commands: List[Command]):
    options = assemble_options(commands)
    selected = display_options(options)
    handle_selected_option(selected)


def assemble_options(commands: List[Command]):
    options = [questionary.Choice(cmd.command, description=cmd.short_explanation, value=cmd) for cmd in commands]
    options.append(questionary.Choice("Cancel"))
    options.append(questionary.Separator())
    return options


def display_options(options: List[questionary.Choice]):
    selected = questionary.select(
        "Select command:",
        choices=options,
        use_shortcuts=True,
        style=_SELECT_STYLE,
    ).ask()
    return selected


def handle_selected_option(selected):
    if not selected or selected == "Cancel":
        return

    print("")
    if selected.dangerous_explanation:
        rprint(f"[red]Warning: {selected.dangerous_explanation}[/red]\n")

    if _copy_to_clipboard(selected.command):
        rprint("[green]>[/green] Copied to clipboard")
    else:
        rprint("[dim]Could not copy to clipboard — install wl-clipboard (Wayland) or xclip/xsel (X11)[/dim]")

    rprint(f"\n  [bold cyan]{selected.command}[/bold cyan]\n")

    action = questionary.select(
        "Run this command?",
        choices=[
            questionary.Choice("Run", value="run"),
            questionary.Choice("Done", value="done"),
        ],
        style=_SELECT_STYLE,
    ).ask()

    if action == "run":
        if selected.is_dangerous:
            confirm = questionary.confirm(
                "This command is potentially dangerous. Are you sure?",
                default=False,
            ).ask()
            if not confirm:
                rprint("[dim]Cancelled.[/dim]")
                return
        rprint("[dim]Running...[/dim]")
        run_command(selected.command, shell=True)
