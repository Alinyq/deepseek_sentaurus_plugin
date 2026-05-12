"""
TCAD AI Tools - 使用 @tool 装饰器创建Upsonic工具
所有工具通过gpythonsh运行tcad_ai_tools.py来操作SWB项目
"""
import subprocess
import os
import json
from upsonic.tools import tool


@tool
def get_project_info() -> str:
    """获取SWB项目摘要信息，包括工具、实验数量、参数名和变量名。
    返回JSON格式数据，包含project_name、tools、experiment_count、param_names、var_names。
    
    Returns:
        JSON字符串，包含项目基本信息
    """
    return _run_tool("get_project_info")


@tool
def get_experiment_list() -> str:
    """获取所有实验列表，显示每个实验的索引、名称和参数值。
    参数就是实验的自变量，可用于了解实验设计。
    
    Returns:
        JSON字符串，包含实验列表及参数
    """
    return _run_tool("get_experiment_list")


@tool
def get_cmd_files() -> str:
    """获取所有.cmd命令文件的完整内容（SDE、SDEVICE、SPROCESS等）。
    这些文件包含仿真设置、物理模型、网格配置、求解器参数等关键信息。
    
    Returns:
        JSON字符串，键为文件名，值为文件内容
    """
    return _run_tool("get_cmd_files")


@tool
def get_param_names() -> str:
    """获取所有参数（自变量）的名称列表。
    
    Returns:
        JSON字符串，包含参数名列表
    """
    return _run_tool("get_param_names")


@tool
def get_var_names() -> str:
    """获取所有变量（因变量/输出量）的名称列表。
    
    Returns:
        JSON字符串，包含变量名列表
    """
    return _run_tool("get_var_names")


@tool
def get_param_value(experiment_index: int, param_name: str) -> str:
    """获取指定实验的特定参数值。
    
    Args:
        experiment_index: 实验索引号
        param_name: 参数名称
    
    Returns:
        JSON字符串，包含参数值
    """
    return _run_tool("get_param_value", str(experiment_index), param_name)


@tool
def set_param_value(experiment_index: int, param_name: str, value: str) -> str:
    """修改指定实验的特定参数值。
    
    Args:
        experiment_index: 实验索引号
        param_name: 参数名称
        value: 新的参数值
    
    Returns:
        JSON字符串，包含操作结果
    """
    return _run_tool("set_param_value", str(experiment_index), param_name, value)


@tool
def get_experiment_status() -> str:
    """获取所有实验的状态（等待中、运行中、完成、错误）。
    
    Returns:
        JSON字符串，包含实验状态列表
    """
    return _run_tool("get_experiment_status")


@tool
def run_experiment(experiment_index: int) -> str:
    """运行指定的单个实验。
    
    Args:
        experiment_index: 实验索引号
    
    Returns:
        JSON字符串，包含运行结果
    """
    return _run_tool("run_experiment", str(experiment_index))


@tool
def run_all_experiments() -> str:
    """运行所有实验。
    
    Returns:
        JSON字符串，包含运行结果
    """
    return _run_tool("run_all_experiments")


@tool
def add_experiment(name: str, parameter_values: str) -> str:
    """添加新的实验。
    
    Args:
        name: 实验名称
        parameter_values: 参数值字典的JSON字符串
    
    Returns:
        JSON字符串，包含新实验的索引
    """
    return _run_tool("add_experiment", name, parameter_values)


@tool
def delete_experiment(experiment_index: int) -> str:
    """删除指定的实验。
    
    Args:
        experiment_index: 实验索引号
    
    Returns:
        JSON字符串，包含操作结果
    """
    return _run_tool("delete_experiment", str(experiment_index))


@tool
def check_errors() -> str:
    """检查所有实验的错误信息。
    返回包含错误的实验及其错误详情。
    
    Returns:
        JSON字符串，包含错误信息
    """
    return _run_tool("check_errors")


@tool
def get_node_list() -> str:
    """获取所有节点ID列表。
    
    Returns:
        JSON字符串，包含节点ID列表
    """
    return _run_tool("get_node_list")


@tool
def read_file(file_path: str) -> str:
    """读取指定文件的内容。
    
    Args:
        file_path: 文件的绝对路径
    
    Returns:
        文件内容字符串
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"读取文件失败: {e}"


@tool
def write_file(file_path: str, content: str) -> str:
    """写入内容到指定文件。
    
    Args:
        file_path: 文件的绝对路径
        content: 要写入的内容
    
    Returns:
        操作结果
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"文件写入成功: {file_path}"
    except Exception as e:
        return f"写入文件失败: {e}"


@tool
def list_files(dir_path: str) -> str:
    """列出目录内容。
    
    Args:
        dir_path: 目录的绝对路径
    
    Returns:
        目录内容列表
    """
    try:
        items = os.listdir(dir_path)
        return json.dumps({"directory": dir_path, "items": items})
    except Exception as e:
        return f"列出目录失败: {e}"


def _run_tool(command: str, *args) -> str:
    """通过gpythonsh运行TCAD AI工具
    所有SWB操作都通过tcad_ai_tools.py脚本执行
    """
    project_path = os.environ.get("TCAD_PROJECT_PATH", os.getcwd())
    script_path = os.path.join(os.path.dirname(__file__), "..", "..", "swb_tools", "tcad_ai_tools.py")
    
    cmd = ["gpythonsh", script_path, project_path, command] + list(args)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"工具执行失败: {result.stderr.strip()}"
    except Exception as e:
        return f"工具调用失败: {e}"
