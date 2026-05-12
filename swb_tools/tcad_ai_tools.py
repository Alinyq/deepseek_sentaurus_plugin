#!/usr/bin/env gpythonsh
# -*- coding: utf-8 -*-
"""
TCAD AI Tools - Command line interface for gpythonsh
Usage: gpythonsh swb_tools/tcad_ai_tools.py <project_path> <command> [args...]

Commands:
  get_project_info              - Get project summary (tools, experiments, params)
  get_experiment_list           - Get all experiments with parameters
  get_cmd_files                 - Get content of all .cmd files
  get_param_value <exp_idx> <param_name>  - Get parameter value
  set_param_value <exp_idx> <param_name> <new_value>  - Set parameter value
  get_param_names               - Get all parameter names
  get_var_names                 - Get all variable names
  get_experiment_status         - Get status of all experiments
  run_experiment <exp_idx>      - Run specific experiment
  run_all_experiments           - Run all experiments
  add_experiment <params_json>  - Add experiment from JSON
  delete_experiment <exp_idx>   - Delete experiment
  check_errors                  - Check experiment errors
  get_node_list                 - Get all node IDs
"""
import sys
import os
import json
import glob
import re

if len(sys.argv) < 3:
    print("Usage: gpythonsh tcad_ai_tools.py <project_path> <command> [args...]")
    sys.exit(1)

project_path = sys.argv[1]
command = sys.argv[2]
args = sys.argv[3:]

os.chdir(project_path)

from swbpy2.gtree.Deck import Deck

project = Deck(project_path)
tree = project.getGtree()


def get_project_info():
    tools = [str(t) for t in tree.AllTools()]
    leaf_nodes = tree.AllLeafNodes()
    param_names = []
    for tool in tree.AllTools():
        param_names.extend(tree.ToolPnames(tool))
    return json.dumps({
        "project_name": os.path.basename(os.path.abspath(project_path)),
        "project_path": project_path,
        "tools": tools,
        "experiment_count": len(leaf_nodes),
        "param_names": param_names,
        "var_names": tree.AllVarNames()
    }, indent=2)


def get_experiment_list():
    leaf_nodes = tree.AllLeafNodes()
    param_names = []
    for tool in tree.AllTools():
        param_names.extend(tree.ToolPnames(tool))
    experiments = []
    for idx, node in enumerate(leaf_nodes):
        nodes = tree.NodeAncestors(node)[::-1] + [node]
        params = {}
        for n in nodes:
            val = tree.NodePval(n)
            if val:
                params.update(val)
        experiments.append({"index": idx, "params": params})
    return json.dumps(experiments, indent=2)


def get_cmd_files():
    contents = {}
    for pattern in ["*_dvs.cmd", "*_des.cmd"]:
        for f in glob.glob(os.path.join(project_path, pattern)):
            if not re.search(r'\d_', os.path.basename(f)):
                with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
                    contents[os.path.basename(f)] = fh.read()
    return json.dumps(contents if contents else {"message": "No cmd files found"}, indent=2)


def get_param_value(exp_idx, param_name):
    leaf_nodes = tree.AllLeafNodes()
    if int(exp_idx) >= len(leaf_nodes):
        return json.dumps({"error": f"Index out of range (max: {len(leaf_nodes)-1})"})
    node = leaf_nodes[int(exp_idx)]
    nodes = tree.NodeAncestors(node)[::-1] + [node]
    result = {}
    for n in nodes:
        val = tree.NodePval(n)
        if val and param_name in val:
            result[param_name] = val[param_name]
    return json.dumps({"exp": int(exp_idx), "param": param_name, "value": result.get(param_name, "NOT_FOUND")})


def set_param_value(exp_idx, param_name, new_value):
    leaf_nodes = tree.AllLeafNodes()
    if int(exp_idx) >= len(leaf_nodes):
        return json.dumps({"error": "Index out of range"})
    node = leaf_nodes[int(exp_idx)]
    tree.SetNodePval(node, param_name, new_value)
    project.save()
    return json.dumps({"status": "OK", "exp": int(exp_idx), "param": param_name, "new_value": new_value})


def get_param_names():
    names = []
    for tool in tree.AllTools():
        names.extend(tree.ToolPnames(tool))
    return json.dumps(names, indent=2)


def get_var_names():
    return json.dumps(tree.AllVarNames(), indent=2)


def get_experiment_status():
    status = project.status()
    return json.dumps(status, indent=2, default=str)


def run_experiment(exp_idx):
    project.run(expr=str(exp_idx))
    return json.dumps({"status": "started", "experiment": int(exp_idx)})


def run_all_experiments():
    project.run(expr="all")
    return json.dumps({"status": "started", "experiments": "all"})


def add_experiment(params_json):
    params = json.loads(params_json)
    param_names = []
    for tool in tree.AllTools():
        param_names.extend(tree.ToolPnames(tool))
    values = [params.get(n, "") for n in param_names]
    tree.AddPath(values)
    project.save()
    return json.dumps({"status": "OK", "added": params})


def delete_experiment(exp_idx):
    leaf_nodes = tree.AllLeafNodes()
    if int(exp_idx) >= len(leaf_nodes):
        return json.dumps({"error": "Index out of range"})
    node = leaf_nodes[int(exp_idx)]
    tree.DeleteNode(node)
    project.save()
    return json.dumps({"status": "OK", "deleted": int(exp_idx)})


def check_errors():
    errors = []
    for d in os.listdir(project_path):
        if d.isdigit():
            err_file = os.path.join(project_path, d, f"c{d}.err")
            if os.path.exists(err_file):
                with open(err_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        errors.append({"experiment": d, "errors": content})
    return json.dumps(errors if errors else [{"message": "No errors found"}], indent=2)


def get_node_list():
    leaf_nodes = tree.AllLeafNodes()
    result = []
    for idx, node in enumerate(leaf_nodes):
        nodes = tree.NodeAncestors(node)[::-1] + [node]
        result.append({"index": idx, "nodes": [str(n) for n in nodes]})
    return json.dumps(result, indent=2)


commands = {
    "get_project_info": lambda: get_project_info(),
    "get_experiment_list": lambda: get_experiment_list(),
    "get_cmd_files": lambda: get_cmd_files(),
    "get_param_value": lambda: get_param_value(args[0], args[1]),
    "set_param_value": lambda: set_param_value(args[0], args[1], args[2]),
    "get_param_names": lambda: get_param_names(),
    "get_var_names": lambda: get_var_names(),
    "get_experiment_status": lambda: get_experiment_status(),
    "run_experiment": lambda: run_experiment(args[0]),
    "run_all_experiments": lambda: run_all_experiments(),
    "add_experiment": lambda: add_experiment(args[0]),
    "delete_experiment": lambda: delete_experiment(args[0]),
    "check_errors": lambda: check_errors(),
    "get_node_list": lambda: get_node_list(),
}

if command not in commands:
    print(json.dumps({"error": f"Unknown command: {command}. Available: {list(commands.keys())}"}))
    sys.exit(1)

try:
    result = commands[command]()
    print(result)
except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)
