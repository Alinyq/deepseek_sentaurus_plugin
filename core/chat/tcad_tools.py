"""
TCAD Tools for Upsonic Agent - All operations via gpythonsh subprocess
Each tool function calls tcad_ai_tools.py through gpythonsh
"""
import os
import json
import subprocess
from pathlib import Path

TOOLS_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "swb_tools", "tcad_ai_tools.py")
GPYTHONSH = "gpythonsh"


def _run_tool(project_path: str, command: str, *args: str, timeout: int = 120) -> str:
    """Run a TCAD tool command via gpythonsh and return JSON result"""
    cmd = [GPYTHONSH, TOOLS_SCRIPT, project_path, command] + list(args)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=project_path
        )
        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout}s"
    except Exception as e:
        return f"Error: {e}"


def get_project_path() -> str:
    """Get current working directory"""
    return os.getcwd()


def read_file(filepath: str) -> str:
    """Read file content. Args: filepath"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"


def write_file(filepath: str, content: str) -> str:
    """Write content to file. Args: filepath, content"""
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Wrote {len(content)} bytes to {filepath}"
    except Exception as e:
        return f"Error: {e}"


def list_files(path: str = ".") -> str:
    """List files and directories. Args: path (default: current)"""
    try:
        items = os.listdir(path)
        files = sorted([f for f in items if os.path.isfile(os.path.join(path, f)) and not f.startswith('.')])
        dirs = sorted([d for d in items if os.path.isdir(os.path.join(path, d)) and not d.startswith('.')])
        result = []
        if dirs:
            result.append("Dirs: " + ", ".join(dirs))
        if files:
            result.append("Files: " + ", ".join(files))
        return "\n".join(result) if result else "Empty"
    except Exception as e:
        return f"Error: {e}"


def get_project_info(project_path: str = ".") -> str:
    """Get SWB project summary. Args: project_path"""
    if project_path == ".":
        project_path = os.getcwd()
    return _run_tool(project_path, "get_project_info")


def get_experiment_list(project_path: str = ".") -> str:
    """Get all experiments with params. Args: project_path"""
    if project_path == ".":
        project_path = os.getcwd()
    return _run_tool(project_path, "get_experiment_list")


def get_cmd_files(project_path: str = ".") -> str:
    """Get content of .cmd files. Args: project_path"""
    if project_path == ".":
        project_path = os.getcwd()
    return _run_tool(project_path, "get_cmd_files")


def get_param_value(project_path: str, exp_index: int, param_name: str) -> str:
    """Get parameter value. Args: project_path, exp_index, param_name"""
    return _run_tool(project_path, "get_param_value", str(exp_index), param_name)


def set_param_value(project_path: str, exp_index: int, param_name: str, new_value: str) -> str:
    """Set parameter value. Args: project_path, exp_index, param_name, new_value"""
    return _run_tool(project_path, "set_param_value", str(exp_index), param_name, new_value)


def get_param_names(project_path: str = ".") -> str:
    """Get all parameter names. Args: project_path"""
    if project_path == ".":
        project_path = os.getcwd()
    return _run_tool(project_path, "get_param_names")


def get_experiment_status(project_path: str = ".") -> str:
    """Get experiment status. Args: project_path"""
    if project_path == ".":
        project_path = os.getcwd()
    return _run_tool(project_path, "get_experiment_status")


def run_experiment(project_path: str, exp_index: int) -> str:
    """Run specific experiment. Args: project_path, exp_index"""
    return _run_tool(project_path, "run_experiment", str(exp_index), timeout=300)


def run_all_experiments(project_path: str) -> str:
    """Run all experiments. Args: project_path"""
    return _run_tool(project_path, "run_all_experiments", timeout=300)


def add_experiment(project_path: str, params_json: str) -> str:
    """Add experiment from JSON. Args: project_path, params_json"""
    return _run_tool(project_path, "add_experiment", params_json)


def delete_experiment(project_path: str, exp_index: int) -> str:
    """Delete experiment. Args: project_path, exp_index"""
    return _run_tool(project_path, "delete_experiment", str(exp_index))


def check_errors(project_path: str = ".") -> str:
    """Check experiment errors. Args: project_path"""
    if project_path == ".":
        project_path = os.getcwd()
    return _run_tool(project_path, "check_errors")


def get_node_list(project_path: str = ".") -> str:
    """Get all node IDs. Args: project_path"""
    if project_path == ".":
        project_path = os.getcwd()
    return _run_tool(project_path, "get_node_list")


def run_shell_command(command: str, timeout: int = 300) -> str:
    """Run shell command. Args: command, timeout"""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=os.getcwd()
        )
        output = []
        if result.stdout.strip():
            output.append(result.stdout.strip())
        if result.stderr.strip():
            output.append(f"[STDERR] {result.stderr.strip()}")
        output.append(f"[exit: {result.returncode}]")
        return "\n".join(output)
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout}s"
    except Exception as e:
        return f"Error: {e}"
