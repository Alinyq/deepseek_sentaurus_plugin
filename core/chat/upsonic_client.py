"""
Upsonic Client - 使用标准Upsonic Agent/Task方式 + 流式输出 + 多轮对话记忆 + Skills
"""
import os
import asyncio
from upsonic import Agent, Task
from upsonic.models.openai import OpenAIChatModel
from upsonic.providers.openai import OpenAIProvider
from upsonic.skills import Skills, LocalSkills
from PyQt6.QtCore import QObject, pyqtSignal, QThread


class AgentWorker(QObject):
    """Agent执行工作对象，运行在独立线程中"""

    token_received = pyqtSignal(str)
    response_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, agent: Agent, task: Task, tools: list):
        super().__init__()
        self.agent = agent
        self.task = task
        self.tools = tools

    async def _async_run(self):
        """异步执行agent，使用流式输出"""
        import sys
        os.environ["TCAD_PROJECT_PATH"] = self.agent._tcad_project_path
        print(f"[DEBUG] Project path: {os.environ['TCAD_PROJECT_PATH']}", flush=True, file=sys.stderr)
        print(f"[DEBUG] Adding tools: {len(self.tools)}", flush=True, file=sys.stderr)
        self.agent.add_tools(self.tools)
        print(f"[DEBUG] Agent messages count before: {len(getattr(self.agent, 'messages', []))}", flush=True, file=sys.stderr)
        print(f"[DEBUG] Calling agent.astream()...", flush=True, file=sys.stderr)
        
        full_response = ""
        async for chunk in self.agent.astream(self.task):
            if chunk:
                chunk_str = str(chunk)
                full_response += chunk_str
                self.token_received.emit(chunk_str)
        
        print(f"[DEBUG] Agent messages count after: {len(getattr(self.agent, 'messages', []))}", flush=True, file=sys.stderr)
        print(f"[DEBUG] Stream complete: {len(full_response)} chars", flush=True, file=sys.stderr)
        self.response_complete.emit(full_response)

    def run(self):
        """在独立事件循环中执行agent"""
        import sys
        print(f"[DEBUG] Worker starting...", flush=True, file=sys.stderr)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            loop.run_until_complete(self._async_run())
            loop.run_until_complete(asyncio.sleep(0.1))
            loop.close()
            print(f"[DEBUG] Worker finished", flush=True, file=sys.stderr)

        except Exception as e:
            import traceback
            error_msg = f"执行错误: {str(e)}\n{traceback.format_exc()}"
            print(f"[DEBUG] Error: {error_msg}", flush=True, file=sys.stderr)
            self.error_occurred.emit(error_msg)


class ConversationState:
    """管理多轮对话状态"""

    def __init__(self):
        self.all_tools = []

    def clear(self):
        self.all_tools = []


class UpsonicClient(QObject):
    """Upsonic客户端 - 使用Agent/Task方式"""

    token_received = pyqtSignal(str)
    response_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.project_path = config.get('project_path', os.getcwd())
        self.state = ConversationState()
        self.agent = None
        self.worker = None
        self.thread = None
        self._init_client()

    def _init_client(self):
        """初始化Agent"""
        self._create_agent()

    def _create_agent(self):
        """创建Agent实例"""
        try:
            api_key = self.config.get('api_key', '')
            base_url = self.config.get('base_url', 'https://api.deepseek.com')
            model_name = self.config.get('model', 'deepseek-chat')

            system_prompt = f"""你是一个Sentaurus TCAD仿真专家助手。当前项目路径: {self.project_path}

可用工具：你拥有一系列TCAD相关的工具来读取项目信息、管理实验、查看文件等。

知识技能库：你已加载 `sentaurus-tcad` 专业技能包，其中包含：
- SDE/SDEVICE/SPROCESS/SWB 快速指南和完整官方手册
- SWB Python API 参考文档（基于 swbpy2）
- 完整的工程文件模板和创建流程指南
- 常用脚本（工程创建、仿真执行等）
当你需要编写仿真代码、生成命令文件、配置SWB项目或解决仿真问题时，请调用技能工具（如 get_skill_instructions, get_skill_reference, get_skill_script 等）获取专业指导和模板。

行为指南：
1. 根据用户的问题，智能地选择是否需要调用工具来获取真实数据
2. 如果用户的问题涉及具体的项目信息、实验数据、文件内容等，请先调用相应的工具获取真实数据后再回答
3. 如果上下文中已经有足够的信息，可以直接回答，不需要重复调用工具
4. 利用你的对话记忆，在多轮对话中记住之前获取的信息，避免重复调用相同的工具
5. 绝对不要凭猜测或记忆（非工具获取的）回答关于具体数据的问题
6. 用中文回复用户
7. 代码和命令使用markdown格式"""

            model = OpenAIChatModel(
                model_name=model_name,
                provider=OpenAIProvider(
                    api_key=api_key,
                    base_url=base_url
                )
            )

            plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            skills_path = os.path.join(plugin_dir, 'skills', 'sentaurus-tcad')

            skills = Skills(loaders=[LocalSkills(skills_path)]) if os.path.exists(skills_path) else Skills(loaders=[])

            self.agent = Agent(
                model=model,
                name="TCAD Assistant",
                instructions=system_prompt,
                skills=skills,
                debug=False
            )
            self.agent._tcad_project_path = self.project_path

        except Exception as e:
            import traceback
            error_msg = f"初始化错误: {e}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)

    def add_tools(self, tools: list):
        """添加Upsonic工具列表"""
        self.state.all_tools = tools

    def send_message(self, message: str):
        """发送消息"""
        if not self.agent:
            self.error_occurred.emit("Agent未初始化")
            return

        self.agent._tcad_project_path = self.project_path
        os.environ["TCAD_PROJECT_PATH"] = self.project_path

        task = Task(description=message)

        self.thread = QThread()
        self.worker = AgentWorker(self.agent, task, self.state.all_tools)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.token_received.connect(self.token_received.emit)
        self.worker.response_complete.connect(self.response_complete.emit)
        self.worker.error_occurred.connect(self.error_occurred.emit)

        self.worker.response_complete.connect(self.thread.quit)
        self.worker.error_occurred.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def clear_history(self):
        """清空对话历史 - 重新创建Agent实例以清空记忆"""
        self.state.clear()
        self._create_agent()
        self.add_tools(self.state.all_tools)
