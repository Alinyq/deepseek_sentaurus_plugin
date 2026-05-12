#!/usr/bin/env gpythonsh
# -*- coding: utf-8 -*-
"""
SWB Project Info Extractor - 通过 gpythonsh 获取实验信息
用法: gpythonsh get_swb_info.py <project_path> [mode]
  mode: basic (默认), full (含cmd文件内容)
"""
import sys
import os
import json
import glob
import re

project_path = sys.argv[1] if len(sys.argv) > 1 else "./"
mode = sys.argv[2] if len(sys.argv) > 2 else "full"

os.chdir(project_path)

from swbpy2.gtree.Deck import Deck

project = Deck(project_path)
tree = project.getGtree()

tools = tree.AllTools()
param_names = []
for tool in tools:
    param_names = param_names + tree.ToolPnames(tool)
var_names = tree.AllVarNames()
leaf_nodes = tree.AllLeafNodes()

experiments = []
for exp_idx, leaf_node in enumerate(leaf_nodes):
    nodes = tree.NodeAncestors(leaf_node)[::-1] + [leaf_node]
    param_values = []
    for node in nodes:
        value = tree.NodePval(node)
        if value:
            param_values.append(value)
    param_dict = {}
    if len(param_names) == len(param_values):
        for i, name in enumerate(param_names):
            param_dict[name] = param_values[i]
    var_dict = {}
    if var_names:
        try:
            for var_name in var_names:
                value, timestep, step = tree.VarValue(nodes[-1], var_name)
                var_dict[var_name] = value
        except Exception:
            pass
    experiments.append({
        'index': exp_idx,
        'params': param_dict,
        'variables': var_dict
    })

result = {
    'tools': [str(t) for t in tools],
    'param_names': param_names,
    'var_names': var_names,
    'experiments': experiments
}

if mode == "full":
    cmd_contents = {}
    for pattern in ["*_dvs.cmd", "*_des.cmd"]:
        for cmd_file in glob.glob(os.path.join(project_path, pattern)):
            fname = os.path.basename(cmd_file)
            try:
                with open(cmd_file, 'r', encoding='utf-8', errors='ignore') as f:
                    cmd_contents[fname] = f.read()
            except Exception:
                pass
    result['cmd_files'] = cmd_contents

    gtree_file = os.path.join(project_path, "gtree.dat")
    if os.path.exists(gtree_file):
        try:
            with open(gtree_file, 'r') as f:
                result['gtree_content'] = f.read()
        except Exception:
            pass

    gtooldb_file = os.path.join(project_path, "gtooldb.tcl")
    if os.path.exists(gtooldb_file):
        try:
            with open(gtooldb_file, 'r') as f:
                result['gtooldb_content'] = f.read()
        except Exception:
            pass

print(json.dumps(result, ensure_ascii=False))
