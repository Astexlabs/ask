from subprocess import run as run_command
from typing import List

import pyperclip
import questionary
from rich import print as rprint

from zev.llms.types import Command

_SELECT_STYLE = questionary.Style(
    [
        ("answer", "fg:#61afef"),
        ("question", "bold"),
        ("instruction", "fg:#98c379"),
    ]
)


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

    # Try clipboard silently — never block on failure
    clipboard_ok = False
    try:
        pyperclip.copy(selected.command)
        clipboard_ok = True
    except pyperclip.PyperclipException:
        pass

    if clipboard_ok:
        rprint("[green]>[/green] Copied to clipboard")
    else:
        rprint("[dim]Could not copy to clipboard[/dim]")

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
