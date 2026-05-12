#!/usr/bin/env python3
"""Test upsonic @tool decorated function with OpenAI tool calling"""
import os, sys, json, configparser
from openai import OpenAI
from upsonic.tools import tool
import inspect

cfg = os.path.join(os.path.dirname(__file__), "config", "settings.ini")
config = configparser.ConfigParser()
config.read(cfg)

client = OpenAI(
    api_key=config.get('deepseek', 'api_key'),
    base_url=config.get('deepseek', 'base_url') + '/v1'
)
model = config.get('deepseek', 'model').split('/')[-1]

@tool
def get_project_info():
    """获取项目基本信息"""
    return json.dumps({"name": "PN_Diode", "experiments": 7, "tools": ["SDE", "SDEVICE"]})

@tool
def get_experiment_list():
    """获取实验列表"""
    return json.dumps([{"idx": 0, "params": {"Ndop": "1e16"}}, {"idx": 1, "params": {"Ndop": "2e16"}}])

tools = [get_project_info, get_experiment_list]

# 检查工具信息
for t in tools:
    print(f"\n=== Tool: {t} ===")
    print(f"Type: {type(t)}")
    print(f"Dir: {[a for a in dir(t) if not a.startswith('_')]}")
    
    if hasattr(t, 'func'):
        func = t.func
        print(f"t.func type: {type(func)}")
        print(f"t.func name: {func.__name__}")
        print(f"t.func doc: {func.__doc__}")
        print(f"t.func sig: {inspect.signature(func)}")
        
        if hasattr(func, '__wrapped__'):
            wrapped = func.__wrapped__
            print(f"t.func.__wrapped__ sig: {inspect.signature(wrapped)}")
            print(f"t.func.__wrapped__ name: {wrapped.__name__}")

# 构建schema - 模拟upsonic_client中的逻辑
tool_schemas = []
for t in tools:
    func = t.func if hasattr(t, 'func') else t
    if hasattr(func, '__wrapped__'):
        func = func.__wrapped__
    
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
    
    tool_schemas.append(schema)

print("\n=== Schemas ===")
print(json.dumps(tool_schemas, indent=2, ensure_ascii=False))

# 测试调用
messages = [
    {"role": "system", "content": "请先调用get_project_info工具。"},
    {"role": "user", "content": "看看这个项目"}
]

print("\n--- Calling API ---")
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

print(f"\n\nTool calls: {json.dumps(tool_calls, indent=2)}")

if tool_calls:
    for tc in tool_calls:
        tool_name = tc["name"]
        try:
            args = json.loads(tc["arguments"]) if tc["arguments"] else {}
        except:
            args = {}
        
        print(f"\n调用: {tool_name}, args: {args}")
        
        # 找到对应的工具
        found = False
        for t in tools:
            func = t.func if hasattr(t, 'func') else t
            if hasattr(func, '__wrapped__'):
                func = func.__wrapped__
            if func.__name__ == tool_name:
                sig = inspect.signature(func)
                valid_params = set(sig.parameters.keys())
                filtered_args = {k: v for k, v in args.items() if k in valid_params}
                print(f"Filtered args: {filtered_args}")
                result = func(**filtered_args)
                print(f"Result: {result}")
                found = True
                break
        
        if not found:
            print(f"Tool {tool_name} not found!")
