#!/bin/bash
# Reinitialize plugin with managed Python in plugin directory
PLUGIN_DIR="/home/tcad/work/deepseek_tcad_plugin"

echo "=== Reinitializing Python Environment ==="

# Remove old venv
rm -rf "${PLUGIN_DIR}/.venv"

# Create venv with managed Python (downloaded and stored in plugin dir)
cd "${PLUGIN_DIR}"
/home/tcad/.local/bin/uv venv .venv --python 3.14 --python-preference managed

# Install dependencies
/home/tcad/.local/bin/uv pip install requests pillow

PYTHON_PATH="${PLUGIN_DIR}/.venv/bin/python"
echo "Python path: ${PYTHON_PATH}"

# Check if python binary is in plugin venv
ls -la "${PLUGIN_DIR}/.venv/bin/python"
file "${PLUGIN_DIR}/.venv/bin/python"

# Test python
${PYTHON_PATH} --version

echo "=== Updating Tool Definition ==="
cat > /home/tcad/STDB/tooldb_tcad << EOF
# tool: deepseek_tcad
set WB_tool(deepseek_tcad,category) utility
set WB_tool(deepseek_tcad,visual_category) utility
set WB_tool(deepseek_tcad,acronym) ai
set WB_tool(deepseek_tcad,after) all
set WB_binaries(tool,deepseek_tcad) ${PYTHON_PATH}
set Icon(deepseek_tcad) \$app_data(icon_dir)/deepseek.gif
set WB_tool(deepseek_tcad,setup) { os_ln_rel @commands@ n@node@_ai.py "@pwdout@/@nodedir@" }
set WB_tool(deepseek_tcad,epilogue) { extract_vars "\$nodedir" @stdout@ @node@ }
set WB_tool(deepseek_tcad,cmd_line) "n@node@_ai.py"
set WB_tool(deepseek_tcad,input) [list commands pref]
set WB_tool(deepseek_tcad,input,commands,label)  "DeepSeek AI Commands..."
set WB_tool(deepseek_tcad,input,commands,editor)  text
set WB_tool(deepseek_tcad,input,commands,file)   @tool_label@_ai.py
set WB_tool(deepseek_tcad,input,pref,file)  @tool_label@_ai.prf
set WB_tool(deepseek_tcad,input,pref,label)  "Preferences..."
set WB_tool(deepseek_tcad,input,pref,editor)  pref
set WB_tool(deepseek_tcad,output) [list]
set WB_tool(deepseek_tcad,output,files) "n@node@_* pp@node@_* *_n@node@_*"
set WB_tool(deepseek_tcad,exec_dependency) strict
set WB_tool(deepseek_tcad,available) { return 1 }
lappend WB_tool(all) deepseek_tcad
EOF

echo "=== Updating Node Launcher ==="
PROJECT_DIR="/home/tcad/work/auto_sentaurus_project/PN_Diode_Project"
cat > "${PROJECT_DIR}/deepseek_tcad_ai.py" << EOF
#!/${PYTHON_PATH}
import sys, os, subprocess
subprocess.Popen([sys.executable, "${PLUGIN_DIR}/src/main.py", "--project", os.getcwd()],
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
print("DeepSeek AI Assistant launched!")
EOF

echo "=== Updating Launcher ==="
cat > "${PLUGIN_DIR}/swb_tools/launchers/launch_deepseek.sh" << EOF
#!/bin/bash
PROJECT_PATH="\$1"
PYTHON_PATH="${PYTHON_PATH}"
MAIN_SCRIPT="${PLUGIN_DIR}/src/main.py"

if [ -z "\$PROJECT_PATH" ]; then
    PROJECT_PATH="\$(pwd)"
fi

if [ -z "\$DISPLAY" ]; then
    export DISPLAY=:0.0
fi

export HOME="/home/tcad"
export PATH="/home/tcad/.local/bin:\$PATH"

exec "\$PYTHON_PATH" "\$MAIN_SCRIPT" --project "\$PROJECT_PATH"
EOF

chmod +x "${PLUGIN_DIR}/swb_tools/launchers/launch_deepseek.sh"

echo ""
echo "=== Done ==="
echo "Python: ${PYTHON_PATH}"
echo "Tool registered"
