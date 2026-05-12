#!/home/tcad/work/deepseek_tcad_plugin/.venv/bin/python
# -*- coding: utf-8 -*-
"""
DeepSeek TCAD AI Assistant - Node Launcher
This file should be placed in your SWB project directory.
When running the node in SWB, this script launches the GUI.
"""
import sys
import os
import subprocess

project_dir = os.getcwd()
main_script = "/home/tcad/work/deepseek_tcad_plugin/src/main.py"

if __name__ == "__main__":
    env = os.environ.copy()
    env["DISPLAY"] = ":0.0"
    env["HOME"] = "/home/tcad"
    
    subprocess.Popen([
        sys.executable,
        main_script,
        "--project", project_dir
    ], env=env, start_new_session=True)
    print("DeepSeek AI Assistant launched!")
