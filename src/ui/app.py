import os
import re
from typing import Optional, List, Dict, Tuple
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DirectoryTree, TextArea, Label, Button, Input, OptionList
from textual.widgets.option_list import Option
from textual.containers import Horizontal, Vertical, Container
from textual.screen import ModalScreen
from textual import on, work, events
from src.core.editor import EditorCore
from src.ui.command_palette import CommandPaletteModal

class InteractiveLabel(Label):
    """A label that can receive focus and hover styles in Textual."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.can_focus = True

class TermCodeApp(App):
    """A developer-focused, high-performance terminal layout mapping VS Code workflows."""
    
    CSS_PATH = Path(__file__).parent / "styles.css"

    BINDINGS = [
        ("ctrl+b", "toggle_sidebar", "Toggle Sidebar"),
        ("ctrl+p", "open_command_palette", "Command Palette / Go to File"),
        ("ctrl+f", "toggle_find_replace", "Find & Replace"),
        ("ctrl+s", "save_active_file", "Save File"),
        ("ctrl+w", "close_active_tab", "Close Tab"),
        ("ctrl+q", "quit", "Exit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        # Dict mapping file_path -> text_area_id
        self.open_files: Dict[str, str] = {}
        # Dict mapping text_area_id -> file_path
        self.id_to_path: Dict[str, str] = {}
        self.active_file_path: Optional[str] = None
        self.file_id_counter = 0
        self.workspace_root = "."
        self.search_results_data: List[Dict[str, str]] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main_layout"):
            # 1. Activity Bar (VS Code style thin sidebar launcher)
            with Vertical(id="activity_bar"):
                yield InteractiveLabel("📁\nExp", id="btn_explorer", classes="activity_btn active")
                yield InteractiveLabel("🔍\nSrc", id="btn_search", classes="activity_btn")

            # 2. Side Panel Container
            with Vertical(id="side_panel"):
                # Explorer Panel (default view)
                with Vertical(id="explorer_panel"):
                    with Horizontal(id="explorer_actions"):
                        yield Button("📄+ File", id="btn_new_file", classes="action_btn")
                        yield Button("📁+ Folder", id="btn_new_folder", classes="action_btn")
                        yield Button("🗑️ Delete", id="btn_delete_path", classes="action_btn delete_btn")
                    yield DirectoryTree(self.workspace_root, id="dir_tree")
                
                # Search Panel (hidden initially)
                with Vertical(id="search_panel", classes="hidden"):
                    yield Label("Search Workspace:")
                    yield Input(placeholder="Search text...", id="search_input")
                    yield OptionList(id="search_results")

            # 3. Main Workspace Container
            with Vertical(id="workspace_container"):
                # Tab Bar
                yield Horizontal(id="tab_bar")

                # Find & Replace Panel (hidden initially)
                with Horizontal(id="find_replace_panel", classes="hidden"):
                    yield Input(placeholder="Find...", id="find_input")
                    yield Input(placeholder="Replace...", id="replace_input")
                    yield Button("Find Next", id="btn_find_next")
                    yield Button("Replace", id="btn_replace")
                    yield Button("Replace All", id="btn_replace_all")

                # Editor Panel Container
                with Container(id="editor_pane"):
                    # We will dynamically spawn/remove text areas here and toggle display
                    yield Label("TermCode Editor | Open or create a file to start coding", id="placeholder_label")

        # 4. Custom status bar (replaces default status bar for more detail)
        yield Label("TermCode Standby | Ctrl+P for Command Palette", id="custom_status_bar")

    def on_mount(self) -> None:
        self.query_one("#dir_tree").focus()

    # --- Sidebar and Activity Bar Operations ---

    @on(events.Click, "#btn_explorer")
    def show_explorer(self) -> None:
        self.query_one("#explorer_panel").remove_class("hidden")
        self.query_one("#search_panel").add_class("hidden")
        self.query_one("#btn_explorer").add_class("active")
        self.query_one("#btn_search").remove_class("active")
        self.query_one("#dir_tree").focus()

    @on(events.Click, "#btn_search")
    def show_search(self) -> None:
        self.query_one("#explorer_panel").add_class("hidden")
        self.query_one("#search_panel").remove_class("hidden")
        self.query_one("#btn_explorer").remove_class("active")
        self.query_one("#btn_search").add_class("active")
        self.query_one("#search_input").focus()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#side_panel")
        sidebar.display = not sidebar.display
        if sidebar.display:
            # Focus current active sidebar widget
            if not self.query_one("#explorer_panel").has_class("hidden"):
                self.query_one("#dir_tree").focus()
            else:
                self.query_one("#search_input").focus()

    # --- Explorer File Operations ---

    @on(Button.Pressed, "#btn_new_file")
    def create_new_file_prompt(self) -> None:
        self._prompt_input("Create File", "Enter new file path (relative):", self._execute_create_file)

    @on(Button.Pressed, "#btn_new_folder")
    def create_new_folder_prompt(self) -> None:
        self._prompt_input("Create Folder", "Enter new directory path (relative):", self._execute_create_folder)

    @on(Button.Pressed, "#btn_delete_path")
    def delete_selected_path(self) -> None:
        tree = self.query_one("#dir_tree")
        if not tree.cursor_node or not tree.cursor_node.data:
            self.notify("No path selected.", severity="warning")
            return
        
        path = str(tree.cursor_node.data.path)
        success, msg = EditorCore.delete_path(path)
        if success:
            self.notify(msg)
            tree.reload()
            # If the deleted file was open, close its tab
            if path in self.open_files:
                self._close_tab_by_path(path)
        else:
            self.notify(msg, severity="error")

    def _prompt_input(self, title: str, label: str, callback) -> None:
        class InputModal(ModalScreen[Optional[str]]):
            DEFAULT_CSS = """
            InputModal {
                align: center middle;
                background: black 50%;
            }
            #input_modal_container {
                width: 50;
                height: 8;
                background: #1e1e24;
                border: solid #007acc;
                padding: 1;
            }
            """
            def compose(self) -> ComposeResult:
                with Vertical(id="input_modal_container"):
                    yield Label(label)
                    yield Input(id="modal_text_input")
            def on_mount(self) -> None:
                self.query_one(Input).focus()
            @on(Input.Submitted)
            def on_submit(self, event: Input.Submitted) -> None:
                self.dismiss(event.value)
        
        def handle_result(result: Optional[str]) -> None:
            if result:
                callback(result)

        self.push_screen(InputModal(), handle_result)

    def _execute_create_file(self, rel_path: str) -> None:
        full_path = os.path.join(self.workspace_root, rel_path)
        success, msg = EditorCore.create_file(full_path)
        if success:
            self.notify(msg)
            self.query_one("#dir_tree").reload()
            self.open_file(full_path)
        else:
            self.notify(msg, severity="error")

    def _execute_create_folder(self, rel_path: str) -> None:
        full_path = os.path.join(self.workspace_root, rel_path)
        success, msg = EditorCore.create_directory(full_path)
        if success:
            self.notify(msg)
            self.query_one("#dir_tree").reload()
        else:
            self.notify(msg, severity="error")

    # --- Workspace Searching ---

    @on(Input.Changed, "#search_input")
    def on_search_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip()
        results_list = self.query_one("#search_results")
        results_list.clear_options()
        self.search_results_data = []
        
        if len(query) < 2:
            return

        results = EditorCore.search_in_workspace(self.workspace_root, query)
        for res in results:
            option_text = f"{res['file']}:{res['line_num']} - {res['content']}"
            results_list.add_option(Option(option_text))
            self.search_results_data.append(res)

    @on(OptionList.OptionSelected, "#search_results")
    def on_search_result_selected(self, event: OptionList.OptionSelected) -> None:
        if event.index < len(self.search_results_data):
            res = self.search_results_data[event.index]
            full_path = os.path.join(self.workspace_root, res["file"])
            self.open_file(full_path, line=int(res["line_num"]))

    # --- Editor & Tab Management ---

    def open_file(self, path: str, line: Optional[int] = None) -> None:
        """Opens a file, creates/switches to its tab, and focuses the editor."""
        abs_path = os.path.abspath(path)
        
        # Hide placeholder label
        self.query_one("#placeholder_label").display = False

        if abs_path in self.open_files:
            file_id = self.open_files[abs_path]
            self._switch_to_tab(file_id)
            if line is not None:
                text_area = self.query_one(f"#{file_id}", TextArea)
                text_area.cursor_location = (line - 1, 0)
                text_area.scroll_to_line(line - 1)
            return

        success, content = EditorCore.read_file(abs_path)
        if not success:
            self.notify(content, severity="error")
            return

        # Generate a unique ID for Textual widget
        self.file_id_counter += 1
        file_id = f"editor_file_{self.file_id_counter}"
        
        self.open_files[abs_path] = file_id
        self.id_to_path[file_id] = abs_path
        
        # Determine language
        _, ext = os.path.splitext(abs_path.lower())
        mapping = {
            ".py": "python", ".json": "json", ".md": "markdown",
            ".toml": "toml", ".yaml": "yaml", ".yml": "yaml",
            ".html": "html", ".css": "css", ".js": "javascript"
        }
        lang = mapping.get(ext, "python")

        # Spawn the new TextArea widget inside the editor pane
        new_text_area = TextArea(content, language=lang, theme="vscode_dark", id=file_id)
        self.query_one("#editor_pane").mount(new_text_area)
        
        # Re-build tabs bar
        self._rebuild_tabs()
        self._switch_to_tab(file_id)

        if line is not None:
            new_text_area.cursor_location = (line - 1, 0)
            new_text_area.scroll_to_line(line - 1)

    def _rebuild_tabs(self) -> None:
        tab_bar = self.query_one("#tab_bar")
        # Remove all existing tabs
        for child in list(tab_bar.children):
            child.remove()
        
        for path, file_id in self.open_files.items():
            filename = os.path.basename(path)
            tab_classes = "tab"
            if self.active_file_path == path:
                tab_classes += " active_tab"
            
            btn_name = InteractiveLabel(filename, classes="tab_name_btn")
            btn_name.file_id = file_id
            
            btn_close = InteractiveLabel("×", classes="tab_close_btn")
            btn_close.file_id = file_id
            
            # Mount a tab container (let Textual auto-generate unique ID)
            tab_bar.mount(
                Horizontal(
                    btn_name,
                    btn_close,
                    classes=tab_classes
                )
            )

    def _switch_to_tab(self, file_id: str) -> None:
        path = self.id_to_path.get(file_id)
        if not path:
            return
        
        self.active_file_path = path

        # Hide all text areas except the active one
        for fid in self.open_files.values():
            widget = self.query_one(f"#{fid}")
            widget.display = (fid == file_id)

        self._rebuild_tabs()
        
        # Focus the active text area
        active_widget = self.query_one(f"#{file_id}", TextArea)
        active_widget.focus()

        # Update status bar
        self._update_status_bar(active_widget)

    def _close_tab_by_path(self, path: str) -> None:
        file_id = self.open_files.get(path)
        if not file_id:
            return
        
        # Remove text area widget
        self.query_one(f"#{file_id}").remove()
        
        # Clean up tracking
        del self.open_files[path]
        del self.id_to_path[file_id]

        if self.active_file_path == path:
            if self.open_files:
                # Switch to first remaining tab
                next_path = list(self.open_files.keys())[0]
                self._switch_to_tab(self.open_files[next_path])
            else:
                self.active_file_path = None
                self.query_one("#placeholder_label").display = True
                self.query_one("#custom_status_bar").update("TermCode Standby")
        
        self._rebuild_tabs()

    def action_close_active_tab(self) -> None:
        if self.active_file_path:
            self._close_tab_by_path(self.active_file_path)

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        # Standard buttons (explorer actions, find & replace) are handled here
        pass

    @on(events.Click)
    def on_click(self, event: events.Click) -> None:
        target = event.widget
        # Check if the clicked target (or one of its ancestors) is a tab label
        while target is not None and target != self:
            if hasattr(target, "file_id"):
                file_id = target.file_id
                if "tab_name_btn" in target.classes:
                    self._switch_to_tab(file_id)
                elif "tab_close_btn" in target.classes:
                    path = self.id_to_path.get(file_id)
                    if path:
                        self._close_tab_by_path(path)
                break
            target = target.parent

    @on(DirectoryTree.FileSelected)
    def on_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        event.stop()
        self.open_file(str(event.path))

    # --- Status Bar Telemetry ---

    def _update_status_bar(self, text_area: TextArea) -> None:
        if not self.active_file_path:
            self.query_one("#custom_status_bar").update("TermCode Standby")
            return
        
        row, col = text_area.cursor_location
        lang = text_area.language or "plain-text"
        filename = os.path.basename(self.active_file_path)
        self.query_one("#custom_status_bar").update(
            f"📝 {filename}  |  Language: {lang.upper()}  |  Ln {row + 1}, Col {col + 1}  |  {self.active_file_path}"
        )

    @on(TextArea.SelectionChanged)
    def on_cursor_moved(self, event: TextArea.SelectionChanged) -> None:
        self._update_status_bar(event.control)

    # --- Command Palette Modal Action ---

    def action_open_command_palette(self) -> None:
        # Get all workspace files
        files = EditorCore.list_all_files(self.workspace_root)
        # Standard actions/commands
        commands = [
            ("Save File (Ctrl+S)", "save"),
            ("Close Tab (Ctrl+W)", "close_tab"),
            ("Toggle Sidebar (Ctrl+B)", "toggle_sidebar"),
            ("Find & Replace (Ctrl+F)", "find_replace"),
            ("Search Workspace", "search_workspace"),
            ("Create New File", "new_file"),
            ("Create New Folder", "new_folder"),
            ("Exit TermCode", "quit")
        ]

        def handle_palette_result(result: Optional[Tuple[str, str]]) -> None:
            if not result:
                return
            
            res_type, val = result
            if res_type == "file":
                self.open_file(val)
            elif res_type == "command":
                if val == "save":
                    self.action_save_active_file()
                elif val == "close_tab":
                    self.action_close_active_tab()
                elif val == "toggle_sidebar":
                    self.action_toggle_sidebar()
                elif val == "find_replace":
                    self.action_toggle_find_replace()
                elif val == "search_workspace":
                    self.show_search()
                elif val == "new_file":
                    self.create_new_file_prompt()
                elif val == "new_folder":
                    self.create_new_folder_prompt()
                elif val == "quit":
                    self.action_quit()

        self.push_screen(CommandPaletteModal(files, commands), handle_palette_result)

    # --- Find & Replace Panel ---

    def action_toggle_find_replace(self) -> None:
        panel = self.query_one("#find_replace_panel")
        panel.display = not panel.display
        if panel.display:
            self.query_one("#find_input").focus()

    @on(Button.Pressed, "#btn_find_next")
    @on(Input.Submitted, "#find_input")
    def find_next(self) -> None:
        if not self.active_file_path:
            return
        
        file_id = self.open_files[self.active_file_path]
        text_area = self.query_one(f"#{file_id}", TextArea)
        search_term = self.query_one("#find_input").value
        
        if not search_term:
            return

        text = text_area.text
        cursor_idx = text_area.document.cursor_to_index(text_area.cursor_location)
        
        # Search from current cursor forward
        match_idx = text.lower().find(search_term.lower(), cursor_idx + 1)
        if match_idx == -1:
            # Wrap around search
            match_idx = text.lower().find(search_term.lower())
            
        if match_idx != -1:
            start_coord = text_area.document.index_to_location(match_idx)
            end_coord = text_area.document.index_to_location(match_idx + len(search_term))
            text_area.cursor_location = start_coord
            text_area.selection = (start_coord, end_coord)
            text_area.focus()
        else:
            self.notify("No matches found", severity="warning")

    @on(Button.Pressed, "#btn_replace")
    def replace_occurrence(self) -> None:
        if not self.active_file_path:
            return
        
        file_id = self.open_files[self.active_file_path]
        text_area = self.query_one(f"#{file_id}", TextArea)
        search_term = self.query_one("#find_input").value
        replace_term = self.query_one("#replace_input").value

        # If there's a selection matching the search term, replace it
        if text_area.selected_text.lower() == search_term.lower():
            text_area.replace(replace_term, text_area.selection[0], text_area.selection[1])
            self.find_next()
        else:
            self.find_next()

    @on(Button.Pressed, "#btn_replace_all")
    def replace_all_occurrences(self) -> None:
        if not self.active_file_path:
            return
        
        file_id = self.open_files[self.active_file_path]
        text_area = self.query_one(f"#{file_id}", TextArea)
        search_term = self.query_one("#find_input").value
        replace_term = self.query_one("#replace_input").value

        if not search_term:
            return

        # Perform a global replacement of text
        old_text = text_area.text
        # Keep track of cursor position
        curr_loc = text_area.cursor_location
        
        # Perform a case-insensitive global replacement of text matching search behavior
        escaped_search = re.escape(search_term)
        # Use re.sub with IGNORECASE to replace case-insensitively
        new_text = re.sub(escaped_search, lambda m: replace_term, old_text, flags=re.IGNORECASE)
        text_area.text = new_text
        text_area.cursor_location = curr_loc
        self.notify("All matches replaced")

    # --- Save & Close File ---

    def action_save_active_file(self) -> None:
        if not self.active_file_path:
            self.notify("No active file to save.", severity="warning")
            return

        file_id = self.open_files[self.active_file_path]
        text_area = self.query_one(f"#{file_id}", TextArea)
        
        success, feedback = EditorCore.write_file(self.active_file_path, text_area.text)
        if success:
            self.notify(feedback)
        else:
            self.notify(feedback, severity="error")

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            panel = self.query_one("#find_replace_panel")
            if panel.display:
                panel.display = False
                if self.active_file_path:
                    file_id = self.open_files[self.active_file_path]
                    self.query_one(f"#{file_id}", TextArea).focus()
                event.prevent_default()

if __name__ == "__main__":
    app = TermCodeApp()
    app.run()