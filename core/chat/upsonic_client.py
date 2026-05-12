"""
Upsonic Client Wrapper - Multi-turn conversation with proper streaming
Uses OpenAI streaming API directly for real-time token output
"""
import os
import json
from openai import OpenAI
from PyQt6.QtCore import QObject, pyqtSignal


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
    """OpenAI-based streaming client with tool support"""

    token_received = pyqtSignal(str)
    response_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    tool_call_started = pyqtSignal(str)
    tool_call_result = pyqtSignal(str, str)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.project_path = config.get('project_path', os.getcwd())
        self.history = ConversationHistory()
        self.tools = []
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            self.client = OpenAI(
                api_key=self.config.get('api_key', ''),
                base_url=self.config.get('base_url', 'https://api.deepseek.com/v1')
            )

            model_name = self.config.get('model', 'deepseek-chat')
            self.model_name = model_name if '/' not in model_name else model_name.split('/')[-1]

            system_prompt = f"""你是一个Sentaurus TCAD仿真专家助手。当前项目路径: {self.project_path}

你必须按以下流程处理用户的任何问题：
1. 首先调用 get_project_info 工具获取项目基本信息
2. 然后调用 get_experiment_list 获取所有实验和参数
3. 然后调用 get_cmd_files 获取命令文件内容
4. 基于获取的真实数据回答用户问题

你有以下工具可以使用：
- get_project_info: 获取SWB项目摘要（工具、实验数、参数名）
- get_experiment_list: 获取所有实验及其参数值（自变量）
- get_cmd_files: 获取所有.cmd命令文件内容（SDE/SDEVICE/SPROCESS配置）
- get_param_names: 获取所有参数名
- get_param_value: 获取特定实验的特定参数值
- set_param_value: 修改实验参数值
- get_experiment_status: 获取实验状态
- run_experiment: 运行特定实验
- run_all_experiments: 运行所有实验
- check_errors: 检查实验错误
- add_experiment: 添加新实验
- delete_experiment: 删除实验
- get_node_list: 获取所有节点ID
- read_file: 读取文件内容
- write_file: 写入文件
- list_files: 列出目录内容
- run_shell_command: 执行shell命令

重要规则：
1. 回答任何问题前，必须先调用工具获取真实数据
2. 绝对不要凭猜测或记忆回答
3. 用中文回复用户
4. 代码和命令使用markdown格式"""

            self.history.add_system(system_prompt)

            skill_path = self.config.get('skill_path')
            if skill_path and os.path.exists(skill_path):
                skill_file = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(skill_file):
                    with open(skill_file, 'r', encoding='utf-8') as f:
                        skill_content = f.read()[:5000]
                    self.history.add_system(f"TCAD技能参考:\n{skill_content}")

        except Exception as e:
            self.error_occurred.emit(f"初始化错误: {e}")

    def add_tools(self, tools: list):
        """Add tools (list of decorated functions from upsonic.tools.tool)"""
        self.tools = tools

    def _build_tool_schemas(self):
        """Convert tools to OpenAI function schemas"""
        schemas = []
        for t in self.tools:
            func = t.func if hasattr(t, 'func') else t
            if hasattr(func, '__wrapped__'):
                func = func.__wrapped__
            
            import inspect
            sig = inspect.signature(func)
            
            schema = {
                "type": "function",
                "function": {
                    "name": func.__name__,
                    "description": (func.__doc__ or "").strip().split('\n')[0],
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }

            for name, param in sig.parameters.items():
                schema["function"]["parameters"]["properties"][name] = {
                    "type": "string",
                    "description": ""
                }
                if param.default == inspect.Parameter.empty:
                    schema["function"]["parameters"]["required"].append(name)

            schemas.append(schema)
        return schemas

    def _call_tool(self, tool_name: str, args: dict) -> str:
        """Call a tool by name with arguments, filtering invalid params"""
        for t in self.tools:
            func = t.func if hasattr(t, 'func') else t
            if hasattr(func, '__wrapped__'):
                func = func.__wrapped__
            if func.__name__ == tool_name:
                try:
                    import inspect
                    sig = inspect.signature(func)
                    valid_params = set(sig.parameters.keys())
                    filtered_args = {k: v for k, v in args.items() if k in valid_params}
                    result = func(**filtered_args)
                    return str(result)
                except Exception as e:
                    return f"工具执行错误: {e}"
        return f"未知工具: {tool_name}"

    def send_message(self, message: str):
        """Send message with streaming and tool support"""
        if not self.client:
            self.error_occurred.emit("客户端未初始化")
            return

        try:
            self.history.add_user(message)

            for attempt in range(5):
                messages = self.history.get_messages()
                tool_schemas = self._build_tool_schemas()

                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=tool_schemas if tool_schemas else None,
                    tool_choice="auto",
                    stream=True,
                    temperature=0.7,
                    max_tokens=4096
                )

                tool_calls = []
                content_parts = []
                has_tool_calls = False

                for chunk in response:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if not delta:
                        continue

                    if delta.tool_calls:
                        has_tool_calls = True
                        for tc in delta.tool_calls:
                            if tc.index is not None:
                                while len(tool_calls) <= tc.index:
                                    tool_calls.append({"id": "", "name": "", "arguments": ""})
                                if tc.id:
                                    tool_calls[tc.index]["id"] = tc.id
                                if tc.function and tc.function.name:
                                    tool_calls[tc.index]["name"] = tc.function.name
                                if tc.function and tc.function.arguments:
                                    tool_calls[tc.index]["arguments"] += tc.function.arguments

                    if delta.content:
                        content_parts.append(delta.content)
                        self.token_received.emit(delta.content)

                if has_tool_calls:
                    self.history.messages.append({
                        "role": "assistant",
                        "tool_calls": tool_calls
                    })

                    for tc in tool_calls:
                        tool_name = tc["name"]
                        try:
                            args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                        except:
                            args = {}

                        self.tool_call_started.emit(f"调用工具: {tool_name}")

                        result = self._call_tool(tool_name, args)
                        self.tool_call_result.emit(tool_name, result)

                        self.history.messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result
                        })
                else:
                    full_response = ''.join(content_parts)
                    self.history.add_assistant(full_response)
                    self.response_complete.emit(full_response)
                    return

        except Exception as e:
            error_msg = f"错误: {str(e)}"
            self.error_occurred.emit(error_msg)

    def clear_history(self):
        self.history.clear()
