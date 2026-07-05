# TermCode

A developer-focused terminal editor layout mapping VS Code workflows, built with Python and Textual.

## Features
- **Activity Bar & Switchable Sidebar**: Easily toggle between File Explorer and Workspace Search.
- **Dynamic File Tabs**: Multi-tab editing workspace.
- **Command Palette (`Ctrl+P`)**: Search files or type `>` to execute editor commands.
- **Find & Replace Panel (`Ctrl+F`)**: Real-time searching and text replacement.
- **Custom Aesthetic Stylesheet**: Sleek VS Code-inspired dark interface.

## How to Run

### Method 1: Local Runner Script
Run the wrapper script from the project directory:

**On Linux/macOS:**
```bash
./termcode
```

**On Windows (Command Prompt):**
```cmd
termcode.cmd
```

**On Windows (PowerShell):**
```powershell
.\termcode.ps1
```

### Method 2: Global CLI Command (Recommended)

#### Option A: Symlink (Linux/macOS)
You can link the runner script directly to your user bin path (already done for you!):
```bash
ln -sf "$(pwd)/termcode" ~/.local/bin/termcode
```

#### Option B: Editable Pip Installation
Install the application globally in editable mode:
```bash
pip install -e .
```

Once linked/installed, you can launch TermCode from any directory using:
```bash
termcode
```
*(On Windows, pip automatically generates a native `termcode.exe` wrapper inside your Python Scripts folder so this works exactly the same!)*
