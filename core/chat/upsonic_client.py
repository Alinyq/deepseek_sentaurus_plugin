"""
Upsonic Client - 使用标准Upsonic Agent/Task方式 + 流式输出
"""
import os
import json
import asyncio
from upsonic import Agent, Task
from PyQt6.QtCore import QObject, pyqtSignal, QThread


class ConversationState:
    """管理多轮对话状态"""

    def __init__(self):
        self.system_prompt = ""
        self.all_tools = []

    def clear(self):
        self.all_tools = []


class StreamWorker(QThread):
    """流式输出工作线程"""

    token_received = pyqtSignal(str)
    response_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    tool_call_started = pyqtSignal(str)
    tool_call_result = pyqtSignal(str, str)

    def __init__(self, agent: Agent, task: Task, tools: list):
        super().__init__()
        self.agent = agent
        self.task = task
        self.tools = tools
        self.full_response = ""

    def run(self):
        """使用同步方式运行agent并捕获流式输出"""
        try:
            self.full_response = ""
            self.agent.add_tools(self.tools)

            # 使用print_do会自动打印到stdout，我们需要自己捕获
            # 所以改用do()方法 + 手动流式输出
            
            # Upsonic的stream方法返回generator
            if hasattr(self.agent, 'stream'):
                for chunk in self.agent.stream(self.task):
                    if chunk:
                        self.full_response += str(chunk)
                        self.token_received.emit(str(chunk))
            else:
                # 如果没有stream方法，使用do()
                result = self.agent.do(self.task)
                self.full_response = str(result)
                self.token_received.emit(self.full_response)

            self.response_complete.emit(self.full_response)

        except Exception as e:
            self.error_occurred.emit(f"执行错误: {str(e)}")


class UpsonicClient(QObject):
    """Upsonic客户端 - 使用Agent/Task方式 + 流式输出"""

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
        self.worker = None
        self._init_client()

    def _init_client(self):
        try:
            model_name = self.config.get('model', 'deepseek-chat')

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

            self.agent = Agent(
                model=model_name,
                name="TCAD Assistant",
                instructions=system_prompt,
                debug=False
            )

        except Exception as e:
            self.error_occurred.emit(f"初始化错误: {e}")

    def add_tools(self, tools: list):
        """添加Upsonic工具列表"""
        self.state.all_tools = tools

    def send_message(self, message: str):
        """发送消息（使用流式输出）"""
        if not self.agent:
            self.error_occurred.emit("Agent未初始化")
            return

        task = Task(description=message)

        self.worker = StreamWorker(
            self.agent,
            task,
            self.state.all_tools
        )
        self.worker.token_received.connect(self.token_received.emit)
        self.worker.response_complete.connect(self.response_complete.emit)
        self.worker.error_occurred.connect(self.error_occurred.emit)
        self.worker.start()

    def clear_history(self):
        self.state.clear()
