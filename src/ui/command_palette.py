from typing import List, Tuple, Optional
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList
from textual.widgets.option_list import Option
from textual.containers import Vertical
from textual import on, events
import os

class CommandPaletteModal(ModalScreen[Optional[Tuple[str, str]]]):
    """Modal dialog displaying commands or fuzzy-searched project files."""

    DEFAULT_CSS = """
    CommandPaletteModal {
        align: center middle;
        background: black 50%;
    }

    #palette_container {
        width: 80;
        max-width: 90%;
        height: 20;
        background: #1e1e24;
        border: solid #007acc;
        padding: 0;
    }

    #palette_input {
        background: #252526;
        color: #e4e4e7;
        border: tall transparent;
        height: 3;
        margin: 0;
    }

    #palette_input:focus {
        border: tall #007acc;
    }

    #palette_options {
        background: #1e1e24;
        border: none;
        height: 1fr;
    }
    """

    def __init__(self, files: List[str], commands: List[Tuple[str, str]]) -> None:
        super().__init__()
        self.files = files
        self.commands = commands
        self.option_values: List[Tuple[str, str]] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="palette_container"):
            yield Input(placeholder="Search files, or type '>' for commands...", id="palette_input")
            yield OptionList(id="palette_options")

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        self._update_options("")

    def _update_options(self, search_text: str) -> None:
        option_list = self.query_one(OptionList)
        option_list.clear_options()
        self.option_values = []

        if search_text.startswith(">"):
            # Filter editor commands
            query = search_text[1:].strip().lower()
            for cmd_name, action in self.commands:
                if not query or query in cmd_name.lower():
                    option_list.add_option(Option(f"⚙️  {cmd_name}"))
                    self.option_values.append(("command", action))
        else:
            # Filter files list
            query = search_text.strip().lower()
            for file_path in self.files:
                if not query or query in file_path.lower():
                    filename = os.path.basename(file_path)
                    option_list.add_option(Option(f"📄  {filename} — {file_path}"))
                    self.option_values.append(("file", file_path))

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        self._update_options(event.value)

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        option_list = self.query_one(OptionList)
        if option_list.option_count > 0:
            index = option_list.highlighted
            if index is not None and index < len(self.option_values):
                self.dismiss(self.option_values[index])
            else:
                self.dismiss(None)
        else:
            self.dismiss(None)

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.index < len(self.option_values):
            self.dismiss(self.option_values[event.index])
        else:
            self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        option_list = self.query_one(OptionList)
        if option_list.option_count == 0:
            if event.key == "escape":
                event.prevent_default()
                self.dismiss(None)
            return
            
        if event.key == "down":
            event.prevent_default()
            current = option_list.highlighted
            if current is None:
                option_list.highlighted = 0
            else:
                option_list.highlighted = (current + 1) % option_list.option_count
        elif event.key == "up":
            event.prevent_default()
            current = option_list.highlighted
            if current is None:
                option_list.highlighted = option_list.option_count - 1
            else:
                option_list.highlighted = (current - 1) % option_list.option_count
        elif event.key == "escape":
            event.prevent_default()
            self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
