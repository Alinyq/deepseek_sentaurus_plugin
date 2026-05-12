"""
TCAD Tools for Upsonic Agent - SWB operations, file I/O, project management
Each function is designed to work with Upsonic's @tool decorator pattern
"""
import os
import json
import subprocess
from pathlib import Path


def get_project_path() -> str:
    """Get current working directory as project path"""
    return os.getcwd()


def read_file(filepath: str) -> str:
    """Read file content. Args: filepath - path to the file to read"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(filepath: str, content: str) -> str:
    """Write content to file. Args: filepath - path to write, content - text content"""
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} bytes to {filepath}"
    except Exception as e:
        return f"Error writing file: {e}"


def list_files(path: str = ".") -> str:
    """List files and directories. Args: path - directory to list (default: current)"""
    try:
        items = os.listdir(path)
        files = [f for f in items if os.path.isfile(os.path.join(path, f))]
        dirs = [d for d in items if os.path.isdir(os.path.join(path, d))]
        result = []
        if dirs:
            result.append("Dirs: " + ", ".join(sorted(dirs)))
        if files:
            result.append("Files: " + ", ".join(sorted(files)))
        return "\n".join(result) if result else "Empty"
    except Exception as e:
        return f"Error: {e}"


def run_command(command: str, timeout: int = 300) -> str:
    """Run shell command. Args: command - shell command to execute, timeout - max seconds"""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=get_project_path()
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


def get_project_info() -> str:
    """Get SWB project summary (tools, experiments count, params). Must be in project dir."""
    try:
        from swbpy2.gtree.Deck import Deck
        project = Deck(get_project_path())
        tree = project.getGtree()
        tools = [str(t) for t in tree.AllTools()]
        leaf_nodes = tree.AllLeafNodes()
        param_names = []
        for tool in tree.AllTools():
            param_names.extend(tree.ToolPnames(tool))
        return json.dumps({
            "tools": tools,
            "experiment_count": len(leaf_nodes),
            "param_names": param_names,
            "project_path": get_project_path()
        }, indent=2)
    except Exception as e:
        return f"Error: {e}"


def get_experiment_list() -> str:
    """Get list of all experiments with their parameters"""
    try:
        from swbpy2.gtree.Deck import Deck
        project = Deck(get_project_path())
        tree = project.getGtree()
        leaf_nodes = tree.AllLeafNodes()
        experiments = []
        for idx, node in enumerate(leaf_nodes):
            params = {}
            for tool in tree.AllTools():
                for pname in tree.ToolPnames(tool):
                    val = tree.NodePval(node)
                    if val:
                        params[pname] = val
            experiments.append({"index": idx, "params": params})
        return json.dumps(experiments, indent=2)
    except Exception as e:
        return f"Error: {e}"


def get_cmd_files() -> str:
    """Get content of all cmd files (*_dvs.cmd, *_des.cmd) in project"""
    try:
        import glob
        project_path = get_project_path()
        contents = {}
        for pattern in ["*_dvs.cmd", "*_des.cmd"]:
            for f in glob.glob(os.path.join(project_path, pattern)):
                with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
                    contents[os.path.basename(f)] = fh.read()
        if not contents:
            return "No cmd files found"
        return json.dumps(contents, indent=2)
    except Exception as e:
        return f"Error: {e}"


def get_param_value(exp_index: int, param_name: str) -> str:
    """Get parameter value. Args: exp_index - experiment index, param_name - parameter name"""
    try:
        from swbpy2.gtree.Deck import Deck
        project = Deck(get_project_path())
        tree = project.getGtree()
        leaf_nodes = tree.AllLeafNodes()
        if exp_index >= len(leaf_nodes):
            return f"Index out of range (max: {len(leaf_nodes)-1})"
        node = leaf_nodes[exp_index]
        val = tree.NodePval(node)
        return json.dumps({"exp": exp_index, "param": param_name, "value": val})
    except Exception as e:
        return f"Error: {e}"


def set_param_value(exp_index: int, param_name: str, new_value: str) -> str:
    """Set parameter value. Args: exp_index, param_name, new_value"""
    try:
        from swbpy2.gtree.Deck import Deck
        project = Deck(get_project_path())
        tree = project.getGtree()
        leaf_nodes = tree.AllLeafNodes()
        if exp_index >= len(leaf_nodes):
            return f"Index out of range"
        node = leaf_nodes[exp_index]
        tree.SetNodePval(node, param_name, new_value)
        project.save()
        return f"Set {param_name}={new_value} in exp {exp_index}"
    except Exception as e:
        return f"Error: {e}"


def run_experiment(exp_index: int) -> str:
    """Run specific experiment. Args: exp_index - experiment index to run"""
    try:
        from swbpy2.gtree.Deck import Deck
        project = Deck(get_project_path())
        project.run(expr=str(exp_index))
        return f"Started experiment {exp_index}"
    except Exception as e:
        return f"Error: {e}"


def run_all_experiments() -> str:
    """Run all experiments in the project"""
    try:
        from swbpy2.gtree.Deck import Deck
        project = Deck(get_project_path())
        project.run(expr="all")
        return "Started all experiments"
    except Exception as e:
        return f"Error: {e}"


def get_experiment_status() -> str:
    """Get status of all experiments from .status file"""
    status_file = os.path.join(get_project_path(), ".status")
    try:
        with open(status_file, 'r') as f:
            return f.read()
    except:
        return "No status file"


def check_errors() -> str:
    """Check for errors in all experiment output directories"""
    project_path = get_project_path()
    errors = []
    for d in os.listdir(project_path):
        if d.isdigit():
            err_file = os.path.join(project_path, d, f"c{d}.err")
            if os.path.exists(err_file):
                with open(err_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        errors.append(f"Exp {d}: {content}")
    return "\n".join(errors) if errors else "No errors found"


def get_project_tree() -> str:
    """Get project file tree structure"""
    path = get_project_path()
    result = []
    for root, dirs, files in os.walk(path):
        level = root.replace(path, '').count(os.sep)
        indent = '  ' * level
        result.append(f"{indent}{os.path.basename(root)}/")
        sub_indent = '  ' * (level + 1)
        for f in sorted(files):
            if not f.startswith('.'):
                size = os.path.getsize(os.path.join(root, f))
                result.append(f"{sub_indent}{f} ({size}B)")
    return "\n".join(result)


def add_experiment(params_json: str) -> str:
    """Add new experiment from JSON string of params. Args: params_json - '{"param1":"val1","param2":"val2"}'"""
    try:
        from swbpy2.gtree.Deck import Deck
        params = json.loads(params_json)
        project = Deck(get_project_path())
        tree = project.getGtree()
        param_names = []
        for tool in tree.AllTools():
            param_names.extend(tree.ToolPnames(tool))
        values = [params.get(n, "") for n in param_names]
        tree.AddPath(values)
        project.save()
        return f"Added experiment: {params_json}"
    except Exception as e:
        return f"Error: {e}"


def delete_experiment(exp_index: int) -> str:
    """Delete experiment by index. Args: exp_index - experiment index to delete"""
    try:
        from swbpy2.gtree.Deck import Deck
        project = Deck(get_project_path())
        tree = project.getGtree()
        leaf_nodes = tree.AllLeafNodes()
        if exp_index >= len(leaf_nodes):
            return f"Index out of range"
        node = leaf_nodes[exp_index]
        tree.DeleteNode(node)
        project.save()
        return f"Deleted experiment {exp_index}"
    except Exception as e:
        return f"Error: {e}"
