"""
TCAD Tools for Upsonic Agent - All operations via gpythonsh subprocess
Each function is decorated with proper docstrings for AI understanding
"""
import os
import json
import subprocess
from pathlib import Path

TOOLS_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "swb_tools", "tcad_ai_tools.py")
GPYTHONSH = "gpythonsh"


def _run_tool(project_path: str, command: str, *args: str, timeout: int = 120) -> str:
    """Run a TCAD tool command via gpythonsh"""
    cmd = [GPYTHONSH, TOOLS_SCRIPT, project_path, command] + list(args)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=project_path
        )
        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout}s"
    except Exception as e:
        return f"Error: {e}"


def create_tcad_tools(project_path: str):
    """Create TCAD tool functions bound to a specific project path"""

    def read_file(filepath: str) -> str:
        """Read the full content of a file. Use this to read .cmd files or any text file.
        Args: filepath - path to the file to read
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"Error: {e}"

    def write_file(filepath: str, content: str) -> str:
        """Write content to a file. Creates parent directories if needed.
        Args: filepath - path to write, content - text content to write
        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Wrote {len(content)} bytes to {filepath}"
        except Exception as e:
            return f"Error: {e}"

    def list_files(path: str = ".") -> str:
        """List all files and directories in a given path.
        Args: path - directory to list (default: current directory)
        """
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

    def get_project_info() -> str:
        """Get SWB project summary including tools, experiment count, parameter names, and variable names.
        ALWAYS call this FIRST to understand the project context before answering any question.
        Returns: JSON with project name, tools, experiment_count, param_names, var_names
        """
        return _run_tool(project_path, "get_project_info")

    def get_experiment_list() -> str:
        """Get ALL experiments with their parameter values. This shows the independent variables (parameters) for each experiment.
        Use this to understand what parameters vary across experiments.
        Returns: JSON array of experiments with index and params
        """
        return _run_tool(project_path, "get_experiment_list")

    def get_cmd_files() -> str:
        """Get the FULL content of all .cmd command files (SDE, SDEVICE, SPROCESS).
        This is CRITICAL for understanding the simulation setup, physical models, mesh settings, solver parameters.
        ALWAYS call this when asked about simulation settings, models, or configuration.
        Returns: JSON with filename -> content mapping
        """
        return _run_tool(project_path, "get_cmd_files")

    def get_param_value(exp_index: int, param_name: str) -> str:
        """Get a specific parameter value from a specific experiment.
        Args: exp_index - experiment number (0-based), param_name - name of the parameter
        """
        return _run_tool(project_path, "get_param_value", str(exp_index), param_name)

    def set_param_value(exp_index: int, param_name: str, new_value: str) -> str:
        """Modify a parameter value in a specific experiment and save the project.
        Args: exp_index - experiment number, param_name - parameter name, new_value - new value string
        """
        return _run_tool(project_path, "set_param_value", str(exp_index), param_name, new_value)

    def get_param_names() -> str:
        """Get all parameter names (independent variables) defined in the project.
        These are the variables that can be swept across experiments.
        """
        return _run_tool(project_path, "get_param_names")

    def get_experiment_status() -> str:
        """Get the current status of all experiments (running, completed, failed, etc).
        """
        return _run_tool(project_path, "get_experiment_status")

    def run_experiment(exp_index: int) -> str:
        """Run a specific experiment by index. This starts the simulation.
        Args: exp_index - experiment number to run
        """
        return _run_tool(project_path, "run_experiment", str(exp_index), timeout=300)

    def run_all_experiments() -> str:
        """Run ALL experiments in the project. This starts all simulations.
        """
        return _run_tool(project_path, "run_all_experiments", timeout=300)

    def add_experiment(params_json: str) -> str:
        """Add a new experiment with specified parameter values.
        Args: params_json - JSON string like '{"Ndop":"1e16","Temperature":"300"}'
        """
        return _run_tool(project_path, "add_experiment", params_json)

    def delete_experiment(exp_index: int) -> str:
        """Delete an experiment by index.
        Args: exp_index - experiment number to delete
        """
        return _run_tool(project_path, "delete_experiment", str(exp_index))

    def check_errors() -> str:
        """Check for errors in all experiment output files. Use this after running experiments to see if any failed.
        Returns: JSON array of errors or message if no errors
        """
        return _run_tool(project_path, "check_errors")

    def get_node_list() -> str:
        """Get all node IDs for all experiments in the SWB project tree.
        """
        return _run_tool(project_path, "get_node_list")

    def run_shell_command(command: str, timeout: int = 300) -> str:
        """Execute any shell command. Use for running Sentaurus tools like sde, sdevice, swb, gpythonsh, etc.
        Args: command - the shell command to execute, timeout - max seconds to wait
        """
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=project_path
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

    return {
        'read_file': read_file,
        'write_file': write_file,
        'list_files': list_files,
        'get_project_info': get_project_info,
        'get_experiment_list': get_experiment_list,
        'get_cmd_files': get_cmd_files,
        'get_param_value': get_param_value,
        'set_param_value': set_param_value,
        'get_param_names': get_param_names,
        'get_experiment_status': get_experiment_status,
        'run_experiment': run_experiment,
        'run_all_experiments': run_all_experiments,
        'add_experiment': add_experiment,
        'delete_experiment': delete_experiment,
        'check_errors': check_errors,
        'get_node_list': get_node_list,
        'run_shell_command': run_shell_command,
    }
