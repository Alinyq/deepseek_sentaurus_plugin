#!/bin/bash
# DeepSeek TCAD AI Assistant Launcher
PROJECT_PATH="$1"

# 使用 mamba tcad 环境（PyQt6）
eval "$(/home/tcad/miniforge-pypy3/bin/conda shell.bash hook)"
conda activate tcad

MAIN_SCRIPT="/home/tcad/work/deepseek_tcad_plugin/src/main.py"

if [ -z "$PROJECT_PATH" ]; then
    PROJECT_PATH="$(pwd)"
fi

if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0.0
fi

export HOME="/home/tcad"
export PATH="/home/tcad/.local/bin:$PATH"

exec python "$MAIN_SCRIPT" --project "$PROJECT_PATH"
