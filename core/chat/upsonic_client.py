"""
Upsonic Client Wrapper - Multi-turn conversation with streaming
"""
import os
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

try:
    from upsonic import Agent, Task
    from upsonic.models.openai import OpenAIChatModel
    from upsonic.providers.openai import OpenAIProvider
    UPSONIC_AVAILABLE = True
except ImportError:
    UPSONIC_AVAILABLE = False


class ConversationHistory:
    """Manage conversation history"""

    def __init__(self, max_turns: int = 20):
        self.messages = []
        self.max_turns = max_turns

    def add_user(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str):
        self.messages.append({"role": "assistant", "content": content})

    def add_system(self, content: str):
        self.messages.insert(0, {"role": "system", "content": content})

    def get_messages(self):
        return self.messages[-(self.max_turns * 2 + 1):]

    def clear(self):
        if self.messages and self.messages[0]["role"] == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []


class UpsonicClient(QObject):
    """Upsonic-based multi-turn conversation client"""

    token_received = pyqtSignal(str)
    response_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.project_path = config.get('project_path', os.getcwd())
        self.history = ConversationHistory()
        self.agent = None
        self._init_agent()

    def _init_agent(self):
        if not UPSONIC_AVAILABLE:
            self.error_occurred.emit("Upsonic not installed. Run: pip install upsonic")
            return

        try:
            model = OpenAIChatModel(
                model_name=self.config.get('model', 'deepseek-chat'),
                provider=OpenAIProvider(
                    api_key=self.config.get('api_key', ''),
                    base_url=self.config.get('base_url', 'https://api.deepseek.com/v1')
                )
            )

            self.agent = Agent(model=model, name="TCAD Assistant")

            system_prompt = """You are a Sentaurus TCAD simulation expert assistant with full project operation capabilities.

You have these tools:
- File operations: read_file, write_file, list_files
- Command execution: run_command (for sde, sdevice, swb commands)
- Project info: get_project_info, get_project_tree
- Experiment management: get_experiment_list, get_param_value, set_param_value
- Run experiments: run_experiment, run_all_experiments
- Status & errors: get_experiment_status, check_errors
- Project modification: add_experiment, delete_experiment
- Read cmd files: get_cmd_files

Always:
1. Check current project context before answering
2. Use tools to get real data instead of guessing
3. Respond in the same language as user
4. Format code/commands in markdown code blocks"""

            self.history.add_system(system_prompt)

            skill_path = self.config.get('skill_path')
            if skill_path and os.path.exists(skill_path):
                skill_file = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(skill_file):
                    with open(skill_file, 'r', encoding='utf-8') as f:
                        skill_content = f.read()[:8000]
                    self.history.add_system(f"TCAD Skill Reference (excerpt):\n{skill_content}")

        except Exception as e:
            self.error_occurred.emit(f"Init error: {e}")

    def add_tools(self, tools: list):
        if self.agent and tools:
            self.agent.tools = tools

    def send_message(self, message: str):
        if not self.agent:
            self.error_occurred.emit("Agent not initialized")
            return

        try:
            self.history.add_user(message)

            task = Task(description=message)

            result = self.agent.do(task)

            if hasattr(result, 'response'):
                response_text = result.response
            elif isinstance(result, str):
                response_text = result
            else:
                response_text = str(result)

            for char in response_text:
                self.token_received.emit(char)

            self.history.add_assistant(response_text)
            self.response_complete.emit(response_text)

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.error_occurred.emit(error_msg)

    def clear_history(self):
        self.history.clear()
