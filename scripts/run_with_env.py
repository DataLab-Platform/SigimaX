# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""Run a command with environment variables loaded from a .env file.

This script automatically detects the best Python interpreter to use:

1. ``PYTHON`` variable in ``.env`` file (e.g. for WinPython distributions)
2. A local virtual environment (``.venv*`` directory in the project root)
3. Falls back to ``sys.executable`` (the Python that launched this script)

This ensures that VS Code tasks always use the correct Python environment
regardless of which interpreter is configured globally or in VS Code.
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys
from pathlib import Path


def _find_venv_python(project_root: Path) -> str | None:
    """Find a Python executable in a ``.venv*`` directory.

    Searches for directories matching ``.venv*`` in the project root and
    returns the first valid Python executable found.

    Args:
        project_root: The root directory of the project.

    Returns:
        Absolute path to the venv Python executable, or None if not found.
    """
    # Sort to prefer ".venv" over ".venv-xyz" etc.
    venv_dirs = sorted(glob.glob(str(project_root / ".venv*")))
    for venv_dir in venv_dirs:
        venv_path = Path(venv_dir)
        if not venv_path.is_dir():
            continue
        result = _get_venv_python(venv_path)
        if result:
            return result
    return None


def _get_venv_python(venv_dir: Path) -> str | None:
    """Get the Python executable from a specific venv directory.

    Args:
        venv_dir: Path to the virtual environment directory.

    Returns:
        Absolute path to the Python executable, or None if not found.
    """
    if not venv_dir.is_dir():
        return None
    # Windows: Scripts/python.exe — Unix: bin/python
    candidates = [
        venv_dir / "Scripts" / "python.exe",
        venv_dir / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    return None


def resolve_python(project_root: Path) -> str:
    """Resolve the best Python interpreter for the project.

    Priority order:

    1. ``PYTHON`` environment variable (set in ``.env`` or externally)
    2. ``VENV_DIR`` environment variable (explicit venv directory)
    3. ``.venv*`` directory in *project_root* (auto-discovery)
    4. ``sys.executable`` (the interpreter running this script)

    Args:
        project_root: The root directory of the project.

    Returns:
        Absolute path to the Python executable to use.
    """
    # 1. Explicit PYTHON variable (e.g. WinPython distribution)
    python_env = os.environ.get("PYTHON")
    if python_env:
        python_path = Path(python_env)
        if python_path.is_file():
            resolved = str(python_path.resolve())
            print(f"  🐍 Using PYTHON from .env: {resolved}")
            return resolved
        print(f"  ⚠️  PYTHON variable set but not found: {python_env}")

    # 2. Explicit VENV_DIR variable (e.g. for multiple local venvs)
    venv_dir_env = os.environ.get("VENV_DIR")
    if venv_dir_env:
        venv_dir = Path(venv_dir_env)
        if not venv_dir.is_absolute():
            venv_dir = project_root / venv_dir
        venv_python = _get_venv_python(venv_dir)
        if venv_python:
            print(f"  🐍 Using VENV_DIR from .env: {venv_python}")
            return venv_python
        print(f"  ⚠️  VENV_DIR set but no Python found in: {venv_dir}")

    # 3. Auto-discover local venv
    venv_python = _find_venv_python(project_root)
    if venv_python:
        print(f"  🐍 Using venv Python: {venv_python}")
        return venv_python

    # 4. Fallback
    print(f"  🐍 Using caller Python: {sys.executable}")
    return sys.executable


def load_env_file(env_path: str | None = None) -> None:
    """Load environment variables from a .env file."""
    if env_path is None:
        env_path = Path.cwd() / ".env"
    if not Path(env_path).is_file():
        raise FileNotFoundError(f"Environment file not found: {env_path}")
    print(f"Loading environment variables from: {env_path}")
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()
            print(f"  Loaded variable: {key.strip()}={value.strip()}")


def execute_command(command: list[str], python_exe: str) -> int:
    """Execute a command, replacing ``python`` placeholders.

    Any argument that is the bare word ``python`` or that points to a Python
    executable (checked via filename) is replaced by *python_exe* so that the
    subprocess uses the resolved interpreter rather than the global one.

    Args:
        command: The command and its arguments.
        python_exe: The resolved Python interpreter path.

    Returns:
        The subprocess exit code.
    """
    resolved: list[str] = []
    for arg in command:
        if arg.lower() == "python" or (
            Path(arg).name.lower().startswith("python")
            and Path(arg).is_file()
            and arg.lower() != python_exe.lower()
        ):
            resolved.append(python_exe)
        else:
            resolved.append(arg)
    print("Executing command:")
    print(" ".join(resolved))
    print("")
    result = subprocess.call(resolved)
    print(f"Process exited with code {result}")
    return result


def main() -> None:
    """Main function to load environment variables and execute a command."""
    if len(sys.argv) < 2:
        print("Usage: python run_with_env.py <command> [args ...]")
        sys.exit(1)
    print("🏃 Running with environment variables")
    project_root = Path.cwd()
    load_env_file()
    python_exe = resolve_python(project_root)
    return execute_command(sys.argv[1:], python_exe)


if __name__ == "__main__":
    main()
