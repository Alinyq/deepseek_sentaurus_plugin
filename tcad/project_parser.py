#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCAD Project Parser - Parse SWB project structure
"""

import os
import json
import glob
import re
import subprocess

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GET_INFO_SCRIPT = os.path.join(PLUGIN_DIR, "swb_tools", "get_swb_info.py")


class TCADProjectParser:
    """Parser for Sentaurus Workbench projects"""
    
    def __init__(self, project_path):
        self.project_path = project_path
        
    def parse_all(self):
        """Parse entire project (含cmd文件、实验信息等完整内容)"""
        swb_info = self._parse_swb_project("full")
        info = {
            "project_path": self.project_path,
            "structure_files": self.find_structure_files(),
            "simulation_files": self.find_simulation_files(),
            "result_files": self.find_result_files(),
            "parameters": self.get_parameters()
        }
        if swb_info:
            info["swb_experiments"] = swb_info.get("experiments", [])
            info["tools"] = swb_info.get("tools", [])
            info["param_names"] = swb_info.get("param_names", [])
            info["var_names"] = swb_info.get("var_names", [])
            info["cmd_files"] = swb_info.get("cmd_files", {})
            info["gtree_content"] = swb_info.get("gtree_content", "")
            info["gtooldb_content"] = swb_info.get("gtooldb_content", "")
        return info
    
    def find_structure_files(self):
        """Find SDE structure files (*_dvs.cmd)"""
        pattern = os.path.join(self.project_path, "*_dvs.cmd")
        files = glob.glob(pattern)
        return [os.path.basename(f) for f in files]
    
    def find_simulation_files(self):
        """Find SDEVICE simulation files (*_des.cmd)"""
        pattern = os.path.join(self.project_path, "*_des.cmd")
        files = glob.glob(pattern)
        return [os.path.basename(f) for f in files]
    
    def find_result_files(self):
        """Find result files (*.plt, *.log, *.tdr)"""
        plt_files = glob.glob(os.path.join(self.project_path, "*.plt"))
        log_files = glob.glob(os.path.join(self.project_path, "*.log"))
        tdr_files = glob.glob(os.path.join(self.project_path, "*.tdr"))
        return {
            "plt": [os.path.basename(f) for f in plt_files],
            "log": [os.path.basename(f) for f in log_files],
            "tdr": [os.path.basename(f) for f in tdr_files]
        }
    
    def get_parameters(self):
        """Get project parameters from gtree.dat"""
        gtree_file = os.path.join(self.project_path, "gtree.dat")
        if not os.path.exists(gtree_file):
            return "未找到 gtree.dat"
            
        try:
            with open(gtree_file, 'r') as f:
                content = f.read()
            return content
        except Exception as e:
            return f"读取 gtree.dat 错误：{str(e)}"
    
    def _parse_gtree(self):
        """解析 gtree.dat 获取节点信息"""
        gtree_file = os.path.join(self.project_path, "gtree.dat")
        if not os.path.exists(gtree_file):
            return None
        
        nodes = []
        try:
            with open(gtree_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split()
                    if len(parts) >= 3 and parts[1] in ('sde', 'sdevice', 'sprocess', 'svisual', 'inspect'):
                        nodes.append({
                            'name': parts[0],
                            'tool': parts[1],
                            'description': parts[2] if len(parts) > 2 else ''
                        })
        except Exception:
            pass
        return nodes
    
    def _parse_gtooldb(self):
        """解析 gtooldb.tcl 获取工具配置"""
        gtooldb_file = os.path.join(self.project_path, "gtooldb.tcl")
        if not os.path.exists(gtooldb_file):
            return None
        
        tools = {}
        try:
            with open(gtooldb_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('set WB_tool('):
                        m = re.match(r'set WB_tool\((\w+),(\w+)\)\s+"([^"]*)"', line)
                        if m:
                            tool_name = m.group(1)
                            key = m.group(2)
                            value = m.group(3)
                            if tool_name not in tools:
                                tools[tool_name] = {}
                            tools[tool_name][key] = value
        except Exception:
            pass
        return tools
    
    def _parse_cmd_files(self, pattern):
        """解析命令文件获取关键信息"""
        files = glob.glob(os.path.join(self.project_path, pattern))
        info = {}
        for f in files:
            name = os.path.basename(f)
            try:
                with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                
                file_info = {'electrodes': [], 'physics': [], 'solve_steps': []}
                
                # 提取电极
                electrode_section = re.search(r'Electrode\s*\{(.*?)\}', content, re.DOTALL)
                if electrode_section:
                    electrodes = re.findall(r'Name="(\w+)"', electrode_section.group(1))
                    file_info['electrodes'] = electrodes
                
                # 提取物理模型
                physics_section = re.search(r'Physics\s*\{(.*?)\}', content, re.DOTALL)
                if physics_section:
                    models = re.findall(r'(\w+)\s*\(', physics_section.group(1))
                    file_info['physics'] = list(set(models))
                
                # 提取求解步骤
                solve_steps = re.findall(r'Goal\s*\{.*?Voltage=\s*([-\d.]+)', content)
                if solve_steps:
                    file_info['solve_steps'] = solve_steps
                
                info[name] = file_info
            except Exception:
                pass
        return info
    
    def _parse_experiment_outputs(self):
        """扫描 outputs/ 子目录，获取每个实验的结果文件"""
        outputs_dir = os.path.join(self.project_path, "outputs")
        if not os.path.exists(outputs_dir):
            return None
        
        experiments = {}
        # SWB 的 outputs 目录下每个实验一个子目录（如 outputs/0/, outputs/1/）
        for exp_dir_name in sorted(os.listdir(outputs_dir), key=lambda x: int(x) if x.isdigit() else 0):
            exp_dir = os.path.join(outputs_dir, exp_dir_name)
            if not os.path.isdir(exp_dir):
                continue
            
            exp_info = {"dir": exp_dir_name, "files": {"plt": [], "log": [], "tdr": [], "err": [], "out": []}}
            
            for f in os.listdir(exp_dir):
                full_path = os.path.join(exp_dir, f)
                if not os.path.isfile(full_path):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext == ".plt":
                    exp_info["files"]["plt"].append(f)
                elif ext == ".log":
                    exp_info["files"]["log"].append(f)
                elif ext == ".tdr":
                    exp_info["files"]["tdr"].append(f)
                elif ext == ".err":
                    exp_info["files"]["err"].append(f)
                elif ext == ".out":
                    exp_info["files"]["out"].append(f)
                elif f == ".cell":
                    # 读取实验元数据
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as fp:
                            exp_info["cell_info"] = fp.read()
                    except Exception:
                        pass
            
            # 只记录有结果文件的实验
            has_results = any(exp_info["files"][k] for k in exp_info["files"])
            if has_results:
                experiments[exp_dir_name] = exp_info
        
        return experiments if experiments else None
    
    def _read_log_summary(self, log_path, max_lines=30):
        """读取日志的关键信息"""
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            summary = []
            content = ''.join(lines)
            
            # 检查是否成功
            if 'ERROR' in content or 'error' in content:
                errors = [l.strip() for l in lines if 'ERROR' in l or 'error' in l]
                for err in errors[:5]:
                    summary.append(f"    [错误] {err}")
            
            if 'Finished' in content or 'finished' in content:
                summary.append(f"    [完成] 仿真已执行完毕")
            
            # 显示最后几行
            if lines:
                summary.append(f"    最后几行:")
                for line in lines[-5:]:
                    summary.append(f"      {line.strip()}")
            
            return '\n'.join(summary)
        except Exception as e:
            return f"    读取错误: {e}"
    
    def _parse_swb_project(self, mode="basic"):
        """通过gpythonsh执行脚本，获取swbpy2解析的实验信息"""
        try:
            if not os.path.exists(GET_INFO_SCRIPT):
                return {"error": f"脚本不存在: {GET_INFO_SCRIPT}"}
            result = subprocess.run(
                ["gpythonsh", GET_INFO_SCRIPT, self.project_path, mode],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
            else:
                stderr = result.stderr.strip() if result.stderr else "(无stderr)"
                stdout = result.stdout.strip() if result.stdout else "(无stdout)"
                return {"error": f"gpythonsh执行失败 (rc={result.returncode})\nstdout: {stdout}\nstderr: {stderr}"}
        except subprocess.TimeoutExpired:
            return {"error": "gpythonsh执行超时"}
        except Exception as e:
            return {"error": f"执行异常: {e}"}
    
    def parse_results(self):
        """解析仿真结果 - 使用swbpy2读取实验数据（含cmd文件内容）"""
        results = []
        results.append(f"=== 项目路径 ===")
        results.append(f"  {self.project_path}")
        results.append("")
        
        # 使用full模式获取cmd文件内容
        swb_info = self._parse_swb_project("full")
        
        if swb_info and "error" not in swb_info:
            results.append(f"=== 仿真流程 ===")
            results.append(f"  工具节点: {', '.join(swb_info['tools'])}")
            results.append("")
            
            results.append(f"=== 参数列表 ===")
            results.append(f"  {', '.join(swb_info['param_names'])}")
            results.append("")
            
            results.append(f"=== 结果变量 ===")
            results.append(f"  {', '.join(swb_info['var_names'])}")
            results.append("")
            
            # 显示cmd文件内容
            if 'cmd_files' in swb_info and swb_info['cmd_files']:
                results.append(f"=== 仿真命令文件 ===")
                for fname, content in swb_info['cmd_files'].items():
                    results.append(f"\n--- {fname} ---")
                    results.append(content)
                results.append("")
            
            # 显示gtree.dat
            if 'gtree_content' in swb_info and swb_info['gtree_content']:
                results.append(f"=== 项目树 (gtree.dat) ===")
                results.append(swb_info['gtree_content'])
                results.append("")
            
            # 显示gtooldb.tcl
            if 'gtooldb_content' in swb_info and swb_info['gtooldb_content']:
                results.append(f"=== 工具数据库 (gtooldb.tcl) ===")
                results.append(swb_info['gtooldb_content'])
                results.append("")
            
            results.append(f"=== 实验结果 (共 {len(swb_info['experiments'])} 个实验) ===")
            results.append("")
            
            for exp in swb_info['experiments']:
                results.append(f"--- 实验 {exp['index']} ---")
                
                # 显示参数值
                if exp['params']:
                    results.append(f"  参数配置:")
                    for name, value in exp['params'].items():
                        results.append(f"    {name} = {value}")
                
                # 显示仿真结果变量
                if exp['variables']:
                    results.append(f"  仿真结果:")
                    for name, value in exp['variables'].items():
                        results.append(f"    {name} = {value}")
                else:
                    results.append(f"  [未运行] 此实验尚未执行仿真")
                
                results.append("")
        else:
            if swb_info and "error" in swb_info:
                results.append(f"=== 检测失败 ===")
                results.append(f"  {swb_info['error']}")
                results.append("")
            results.append(f"=== [文件扫描模式] ===")
            results.append(f"  使用文件扫描方式检测项目信息")
            results.append("")
            
            nodes = self._parse_gtree()
            if nodes:
                results.append(f"=== 仿真流程节点 ===")
                for node in nodes:
                    results.append(f"  [{node['tool']}] {node['name']}")
                results.append("")
            
            # 扫描outputs目录
            experiments = self._parse_experiment_outputs()
            if experiments:
                results.append(f"=== 实验结果 (共 {len(experiments)} 个实验) ===")
                results.append("")
                
                for exp_id, exp_info in sorted(experiments.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
                    results.append(f"--- 实验 {exp_id} ---")
                    
                    if "cell_info" in exp_info:
                        try:
                            cell_data = json.loads(exp_info["cell_info"])
                            if "experiment" in cell_data:
                                results.append(f"  实验编号: {cell_data['experiment']}")
                        except Exception:
                            pass
                    
                    for ftype, files in exp_info["files"].items():
                        if files:
                            type_names = {"plt": "电流/电压数据", "log": "日志", "tdr": "结构数据", "err": "错误", "out": "输出"}
                            results.append(f"  {type_names.get(ftype, ftype)}: {', '.join(files)}")
                    
                    exp_dir = exp_info["dir"]
                    for log_file in exp_info["files"]["log"][:1]:
                        log_path = os.path.join(self.project_path, "outputs", exp_dir, log_file)
                        results.append(f"  日志摘要:")
                        results.append(self._read_log_summary(log_path))
                    
                    results.append("")
            else:
                results.append("=== 未找到实验结果 ===")
                results.append("  尚未运行仿真，或结果文件不在 outputs/ 目录下")
                results.append("")
        
        return '\n'.join(results)
