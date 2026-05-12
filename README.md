# DeepSeek TCAD AI Assistant

Sentaurus TCAD 仿真 AI 助手插件，基于 DeepSeek AI 大模型，为半导体器件仿真提供智能分析和参数优化建议。

## 功能特性

### 1. 代码审查（智能仿真描述）
- 自动检测 SDE/SDEVICE/SPROCESS/SWB 命令文件
- AI 自动分析仿真脚本内容，生成中文描述
- 智能识别电极配置、物理模型、求解序列

### 2. 结果分析
- **自动检测结果文件**：通过 `gpythonsh + swbpy2` 自动获取 SWB 项目完整信息
  - 获取所有实验节点、参数配置、仿真结果变量
  - 读取 `.cmd` 命令文件内容、`gtree.dat`、`gtooldb.tcl`
  - 支持扫描 `outputs/` 目录获取各实验结果文件
- AI 根据完整项目信息生成分析报告
- 支持自定义附加要求

### 3. 参数优化
- 用户输入目标性能和可调参数
- AI 读取完整项目配置（实验数据、命令文件、参数值等）
- 提供参数推荐范围、优化策略、预期性能提升

### 4. 报告生成
- 基于项目全部信息自动生成 TCAD 仿真报告
- 动态生成当前日期
- 支持自定义附加要求

## 项目架构

```
deepseek_tcad_plugin/           # 插件根目录
├── config/
│   └── settings.ini            # API 配置（需自行创建）
├── core/
│   ├── __init__.py
│   └── deepseek_client.py      # DeepSeek API 客户端
├── src/
│   └── main.py                 # PyQt6 GUI 主程序
├── swb_tools/
│   ├── launchers/
│   │   └── launch_deepseek.sh  # 启动脚本
│   ├── deepseek_tcad_ai.py     # SWB 节点启动器
│   ├── get_swb_info.py         # gpythonsh 实验数据获取脚本
│   └── reinit_plugin.sh       # 插件重新初始化脚本
├── tcad/
│   ├── __init__.py
│   ├── file_reader.py          # 文件读取工具
│   └── project_parser.py       # SWB 项目解析器
├── .gitignore
├── README.md
├── 使用说明书.md               # 详细安装使用说明书
└── 中文乱码处理.md             # 中文显示问题解决方案
```

## 安装部署

### 环境要求
- Python 3.8+ (mamba tcad 环境)
- PyQt6
- DeepSeek API Key
- Sentaurus TCAD (swbpy2)

### 部署步骤

```bash
# 1. 克隆项目
git clone https://github.com/YOUR_USERNAME/deepseek_tcad_plugin.git
cd deepseek_tcad_plugin

# 2. 配置 API Key
mkdir -p config
cat > config/settings.ini << EOF
[api]
base_url = https://api.deepseek.com
api_key = YOUR_API_KEY
model = deepseek-chat
EOF

# 3. 设置权限
chmod +x swb_tools/launchers/launch_deepseek.sh
chmod +x swb_tools/reinit_plugin.sh
```

### SWB 节点集成

将 `swb_tools/deepseek_tcad_ai.py` 复制到 SWB 项目目录下运行。

## 技术架构

### 数据获取流程

```
GUI (mamba tcad env)
    ↓
project_parser.py (subprocess)
    ↓
gpythonsh get_swb_info.py <project_path> <mode>
    ↓
swbpy2 (Deck, tree API)
    ↓
JSON result → GUI 显示 / AI 分析
```

### 关键设计

- **双环境架构**：GUI 使用 mamba tcad 环境（PyQt6），实验数据通过 `gpythonsh` 获取（swbpy2）
- **subprocess 桥接**：通过 `subprocess.run()` 调用 `gpythonsh` 脚本，实现跨环境数据传递
- **双模式解析**：full 模式（含命令文件内容）用于结果分析/参数优化/报告生成；basic 模式（仅实验信息）用于快速查询

## 配置文件

`config/settings.ini` 需要手动创建：

```ini
[api]
base_url = https://api.deepseek.com
api_key = YOUR_API_KEY
model = deepseek-chat
```

## 使用说明

详见 [使用说明书.md](使用说明书.md)

## 常见问题

详见 [中文乱码处理.md](中文乱码处理.md)

## License

MIT License
