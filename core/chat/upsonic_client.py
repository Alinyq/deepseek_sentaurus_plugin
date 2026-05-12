"""
Upsonic Client - 使用标准Upsonic Agent/Task方式
支持流式输出展示工具调用过程
"""
import os
import json
from upsonic import Agent, Task
from PyQt6.QtCore import QObject, pyqtSignal


class ConversationState:
    """管理多轮对话状态"""

    def __init__(self):
        self.system_prompt = ""
        self.history = []
        self.all_tools = []

    def clear(self):
        self.history = []


class UpsonicClient(QObject):
    """Upsonic客户端 - 使用Agent/Task方式管理工具和多轮对话"""

    token_received = pyqtSignal(str)
    response_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    tool_call_started = pyqtSignal(str)
    tool_call_result = pyqtSignal(str, str)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.project_path = config.get('project_path', os.getcwd())
        self.state = ConversationState()
        self.agent = None
        self._init_client()

    def _init_client(self):
        try:
            model_name = self.config.get('model', 'deepseek-chat')
            self.agent = Agent(
                model=model_name,
                name="TCAD Assistant"
            )

            system_prompt = f"""你是一个Sentaurus TCAD仿真专家助手。当前项目路径: {self.project_path}

你必须按以下流程处理用户的任何问题：
1. 首先调用 get_project_info 工具获取项目基本信息
2. 然后调用 get_experiment_list 获取所有实验和参数
3. 然后调用 get_cmd_files 获取命令文件内容
4. 基于获取的真实数据回答用户问题

重要规则：
1. 回答任何问题前，必须先调用工具获取真实数据
2. 绝对不要凭猜测或记忆回答
3. 用中文回复用户
4. 代码和命令使用markdown格式"""

            self.state.system_prompt = system_prompt

        except Exception as e:
            self.error_occurred.emit(f"初始化错误: {e}")

    def add_tools(self, tools: list):
        """添加Upsonic工具列表"""
        self.state.all_tools = tools

    def send_message(self, message: str):
        """发送消息（同步调用，完成后发射信号）"""
        try:
            task_description = message

            task = Task(
                description=task_description,
                tools=self.state.all_tools
            )

            self.tool_call_started.emit("正在处理请求...")

            result = self.agent.do(task)

            full_response = str(result)
            self.token_received.emit(full_response)
            self.response_complete.emit(full_response)

        except Exception as e:
            error_msg = f"错误: {str(e)}"
            self.error_occurred.emit(error_msg)

    def clear_history(self):
        self.state.clear()
