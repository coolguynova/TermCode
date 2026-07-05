import os
import shutil
from typing import Tuple, List, Dict

class EditorCore:
    """Helper for reading, writing, and manipulating files in the workspace."""

    # Block known binary formats
    BINARY_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', 
        '.tar', '.gz', '.db', '.sqlite', '.pyc', '.exe', '.bin', '.venv', '.git'
    }

    # Ignore when listing/searching
    IGNORE_DIRS = {'.venv', '.git', '__pycache__', 'node_modules', '.pytest_cache'}

    @staticmethod
    def read_file(file_path: str) -> Tuple[bool, str]:
        """Read text content from a file, checking binary exclusions and encoding."""
        if not os.path.exists(file_path):
            return False, "Error: File does not exist."
        
        _, ext = os.path.splitext(file_path.lower())
        if ext in EditorCore.BINARY_EXTENSIONS:
            return False, f"Binary file: preview for '{ext}' files is disabled."
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return True, f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    return True, f.read()
            except Exception as e:
                return False, f"Failed to parse text format: {str(e)}"
        except Exception as e:
            return False, f"Access denied: {str(e)}"

    @staticmethod
    def write_file(file_path: str, contents: str) -> Tuple[bool, str]:
        """Write contents to file, creating parent folders if they don't exist."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(contents)
            return True, "File saved successfully."
        except Exception as e:
            return False, f"Failed writing to storage: {str(e)}"

    @staticmethod
    def list_all_files(root_dir: str) -> List[str]:
        """Recursively list all relative text file paths in the workspace."""
        file_list = []
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in EditorCore.IGNORE_DIRS]
            
            for file in files:
                _, ext = os.path.splitext(file.lower())
                if ext in EditorCore.BINARY_EXTENSIONS:
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, root_dir)
                file_list.append(rel_path)
        return sorted(file_list)

    @staticmethod
    def search_in_workspace(root_dir: str, query: str) -> List[Dict[str, str]]:
        """Perform a case-insensitive search for a query string across the workspace."""
        results = []
        if not query:
            return results
            
        files = EditorCore.list_all_files(root_dir)
        for rel_path in files:
            full_path = os.path.join(root_dir, rel_path)
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if query.lower() in line.lower():
                            results.append({
                                "file": rel_path,
                                "line_num": i,
                                "content": line.strip()
                            })
            except Exception:
                continue
        return results

    @staticmethod
    def create_file(file_path: str) -> Tuple[bool, str]:
        """Create an empty file at the destination path."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("")
            return True, f"Created file: {os.path.basename(file_path)}"
        except Exception as e:
            return False, f"Error creating file: {str(e)}"

    @staticmethod
    def create_directory(dir_path: str) -> Tuple[bool, str]:
        """Create a new folder at the destination path."""
        try:
            os.makedirs(dir_path, exist_ok=True)
            return True, f"Created directory: {os.path.basename(dir_path)}"
        except Exception as e:
            return False, f"Error creating directory: {str(e)}"

    @staticmethod
    def delete_path(path: str) -> Tuple[bool, str]:
        """Delete a file or directory at the destination path."""
        try:
            if not os.path.exists(path):
                return False, "Path does not exist"
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return True, f"Deleted: {os.path.basename(path)}"
        except Exception as e:
            return False, f"Error deleting path: {str(e)}"