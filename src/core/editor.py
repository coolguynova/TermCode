import os
import shutil
from typing import Tuple, List, Dict

class EditorCore:
    """Manages reading and writing codebase assets safely to disk storage."""

    # Explicitly block known binary file formats from triggering decode loops
    BINARY_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', 
        '.tar', '.gz', '.db', '.sqlite', '.pyc', '.exe', '.bin', '.venv', '.git'
    }

    # Directory patterns to ignore when listing/searching
    IGNORE_DIRS = {'.venv', '.git', '__pycache__', 'node_modules', '.pytest_cache'}

    @staticmethod
    def read_file(file_path: str) -> Tuple[bool, str]:
        """Reads content from disk file safely, checking encoding constraints."""
        if not os.path.exists(file_path):
            return False, "Error: Selected path target does not exist."
        
        # Guard check against binary extensions
        _, ext = os.path.splitext(file_path.lower())
        if ext in EditorCore.BINARY_EXTENSIONS:
            return False, f"Binary Asset: Previews for '{ext}' files are disabled."
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return True, f.read()
        except UnicodeDecodeError:
            # Secondary fallback check: Try reading with system default configuration 
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    return True, f.read()
            except Exception as e:
                return False, f"Binary file preview error: GitPilot TermCode only parses UTF-8 text formats."
        except Exception as e:
            return False, f"System access denied: {str(e)}"

    @staticmethod
    def write_file(file_path: str, contents: str) -> Tuple[bool, str]:
        """Writes current text edits back down into non-volatile block storage."""
        try:
            # Make sure parent directories exist
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(contents)
            return True, "File sync finalized successfully."
        except Exception as e:
            return False, f"Failed writing assets to storage track: {str(e)}"

    @staticmethod
    def list_all_files(root_dir: str) -> List[str]:
        """Lists all non-binary files recursively in the workspace, relative to root."""
        file_list = []
        for root, dirs, files in os.walk(root_dir):
            # Prune ignored directories in-place
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
        """Searches for a text query across all non-binary workspace files."""
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
        """Creates an empty file at the given path."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("")
            return True, f"File created: {os.path.basename(file_path)}"
        except Exception as e:
            return False, f"Error creating file: {str(e)}"

    @staticmethod
    def create_directory(dir_path: str) -> Tuple[bool, str]:
        """Creates a directory at the given path."""
        try:
            os.makedirs(dir_path, exist_ok=True)
            return True, f"Directory created: {os.path.basename(dir_path)}"
        except Exception as e:
            return False, f"Error creating directory: {str(e)}"

    @staticmethod
    def delete_path(path: str) -> Tuple[bool, str]:
        """Deletes a file or directory at the given path."""
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