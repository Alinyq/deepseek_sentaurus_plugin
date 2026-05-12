#!/usr/bin/env python3
"""
Test tool calling with OpenAI streaming directly
"""
import os
import sys
import json
import configparser
from openai import OpenAI

# 读取配置
cfg_path = os.path.join(os.path.dirname(__file__), "config", "settings.ini")
config = configparser.ConfigParser()
config.read(cfg_path)

client = OpenAI(
    api_key=config.get('deepseek', 'api_key'),
    base_url=config.get('deepseek', 'base_url') + '/v1'
)

model = config.get('deepseek', 'model').split('/')[-1]
print(f"Model: {model}")

# 简单工具
def get_project_info():
    """获取项目基本信息"""
    return json.dumps({"name": "PN_Diode", "experiments": 7, "tools": ["SDE", "SDEVICE"]})

def get_experiment_list():
    """获取实验列表"""
    return json.dumps([{"idx": 0, "params": {"Ndop": "1e16"}}, {"idx": 1, "params": {"Ndop": "2e16"}}])

tools = [get_project_info, get_experiment_list]

# 构建schema
tool_schemas = []
for func in tools:
    import inspect
    sig = inspect.signature(func)
    schema = {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": (func.__doc__ or "").strip(),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
    for name, param in sig.parameters.items():
        schema["function"]["parameters"]["properties"][name] = {"type": "string"}
        if param.default == inspect.Parameter.empty:
            schema["function"]["parameters"]["required"].append(name)
    tool_schemas.append(schema)

print("Tool schemas:")
print(json.dumps(tool_schemas, indent=2))

# 发消息
messages = [
    {"role": "system", "content": "你是一个助手。请先调用get_project_info工具获取信息。"},
    {"role": "user", "content": "请帮我看看这个项目是什么"}
]

print("\n--- 开始流式调用 ---")

response = client.chat.completions.create(
    model=model,
    messages=messages,
    tools=tool_schemas,
    tool_choice="auto",
    stream=True
)

tool_calls = []
content = ""
for chunk in response:
    delta = chunk.choices[0].delta if chunk.choices else None
    if not delta:
        continue
    if delta.tool_calls:
        for tc in delta.tool_calls:
            idx = tc.index
            while len(tool_calls) <= idx:
                tool_calls.append({"id": "", "name": "", "arguments": ""})
            if tc.id:
                tool_calls[idx]["id"] = tc.id
            if tc.function and tc.function.name:
                tool_calls[idx]["name"] = tc.function.name
            if tc.function and tc.function.arguments:
                tool_calls[idx]["arguments"] += tc.function.arguments
    if delta.content:
        content += delta.content
        print(delta.content, end="", flush=True)

print("\n\n--- Tool calls ---")
print(json.dumps(tool_calls, indent=2))

if tool_calls:
    for tc in tool_calls:
        print(f"\n调用工具: {tc['name']}")
        print(f"参数: {tc['arguments']}")
        
        # 调用工具
        func = next(f for f in tools if f.__name__ == tc['name'])
        try:
            args = json.loads(tc['arguments']) if tc['arguments'] else {}
            print(f"解析后的参数: {args}")
            result = func(**args)
            print(f"结果: {result}")
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
