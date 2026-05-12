# Sentaurus TCAD AI 插件 - 部署指南

## 版本信息

- **插件版本**: v1.0.0
- **Sentaurus 版本**: W-2024.09
- **Python 环境**: mamba tcad (GUI) + gpythonsh/swbpy2 (数据获取)

---

## 文件清单

```
deepseek_sentaurus_plugin_v1.0.0/
├── config/                          # 配置文件目录
│   └── settings.ini.example         # API配置示例（需复制为settings.ini）
├── core/                            # 核心模块
│   ├── __init__.py
│   └── deepseek_client.py           # DeepSeek API客户端（SSE流式）
├── src/                             # 主程序
│   └── main.py                      # PyQt6 GUI主程序
├── swb_tools/                       # SWB集成工具
│   ├── launchers/
│   │   └── launch_deepseek.sh       # SWB启动脚本
│   ├── deepseek_tcad_ai.py          # SWB节点启动器
│   ├── get_swb_info.py              # gpythonsh实验数据获取脚本
│   └── reinit_plugin.sh             # 插件重新初始化脚本
├── tcad/                            # TCAD工具模块
│   ├── __init__.py
│   ├── file_reader.py               # 文件读取工具
│   └── project_parser.py            # SWB项目解析器
├── release_resources/               # 部署资源
│   ├── tooldb/
│   │   └── tooldb_tcad              # Sentaurus用户工具数据库
│   └── icons/
│       └── deepseek.gif             # SWB工具图标（需自备）
├── .gitignore
├── README.md
└── DEPLOY_GUIDE.md                  # 本文件
```

---

## 部署步骤

### 1. 环境准备

确保远程机器已安装：

- **Sentaurus TCAD** W-2024.09 (路径: `/usr/synopsys/sentaurus/W-2024.09/`)
- **mamba/conda** 环境 `tcad` (包含 PyQt6)
- **gpythonsh** (Sentaurus内置Python，含swbpy2模块)

### 2. 部署插件代码

```bash
# 在远程机器上
mkdir -p /home/tcad/work/deepseek_tcad_plugin
cd /home/tcad/work/deepseek_tcad_plugin

# 上传插件文件（从本地机器）
scp -r deepseek_sentaurus_plugin_v1.0.0/* tcad@<远程IP>:/home/tcad/work/deepseek_tcad_plugin/
```

### 3. 配置API

```bash
cd /home/tcad/work/deepseek_tcad_plugin

# 创建配置文件
cp config/settings.ini.example config/settings.ini

# 编辑配置文件，填入DeepSeek API密钥
nano config/settings.ini
```

**settings.ini 内容：**

```ini
[deepseek]
api_key = sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
base_url = https://api.deepseek.com
model = deepseek-chat
max_tokens = 4000
temperature = 0.7
```

### 4. 部署SWB工具数据库

```bash
# 复制tooldb_tcad到Sentaurus工具数据库目录
cp release_resources/tooldb/tooldb_tcad /home/tcad/STDB/tooldb_tcad

# 如果tooldb_tcad已存在，先备份
cp /home/tcad/STDB/tooldb_tcad /home/tcad/STDB/tooldb_tcad.bak  # 备份
cp release_resources/tooldb/tooldb_tcad /home/tcad/STDB/tooldb_tcad
```

### 5. 部署工具图标（可选）

```bash
# 将deepseek.gif图标复制到Sentaurus图标目录
cp release_resources/icons/deepseek.gif /usr/synopsys/sentaurus/W-2024.09/tcad/current/lib/glib2/icons/
```

### 6. 部署到SWB项目

```bash
# 在每个需要AI助手的SWB项目中部署启动器
# 示例项目：/home/tcad/work/auto_sentaurus_project/PN_Diode_Project/

cd /home/tcad/work/auto_sentaurus_project/PN_Diode_Project/

# 复制启动器
cp /home/tcad/work/deepseek_tcad_plugin/swb_tools/deepseek_tcad_ai.py ./
cp /home/tcad/work/deepseek_tcad_plugin/swb_tools/launchers/launch_deepseek.sh ./

# 确保可执行权限
chmod +x launch_deepseek.sh
```

---

## 验证部署

### 测试插件启动

```bash
# 方式1：直接启动GUI
cd /home/tcad/work/deepseek_tcad_plugin
source activate tcad
python src/main.py
```

### 测试SWB集成

```bash
# 1. 打开SWB
swb &

# 2. 在SWB中应能看到 "ai" (deepseek_tcad) 工具

# 3. 添加一个AI节点测试
```

### 测试数据获取

```bash
# 测试gpythonsh数据获取脚本
cd /home/tcad/work/auto_sentaurus_project/PN_Diode_Project/
gpythonsh /home/tcad/work/deepseek_tcad_plugin/swb_tools/get_swb_info.py ./ full
```

---

## 四大功能说明

### 1. 代码审查

- AI分析SDE/SDEVICE/SPROCESS命令文件
- 识别潜在问题和优化建议

### 2. 结果分析

- 通过gpythonsh+swbpy2自动获取SWB项目完整信息
- 读取实验、参数、变量、cmd文件内容
- AI基于完整上下文进行分析

### 3. 参数优化

- AI读取完整项目配置
- 提供物理模型、网格划分、求解器参数优化建议

### 4. 报告生成

- 自动生成TCAD仿真报告
- 包含项目配置、仿真结果、分析建议

---

## 常见问题

### Q: 启动GUI报错找不到PyQt6？

A: 确保在mamba tcad环境中运行：
```bash
conda activate tcad
python src/main.py
```

### Q: SWB中看不到ai工具？

A: 检查tooldb_tcad是否正确部署：
```bash
cat /home/tcad/STDB/tooldb_tcad | grep deepseek
```

### Q: get_swb_info.py获取不到实验数据？

A: 确保在SWB项目目录下运行，且项目已保存：
```bash
cd /path/to/your/swb_project
gpythonsh /home/tcad/work/deepseek_tcad_plugin/swb_tools/get_swb_info.py ./ full
```

---

## 远程连接信息（参考）

| 项目 | 值 |
|------|-----|
| SSH地址 | tcad@192.168.142.134 |
| 远程用户 | tcad |
| Sentaurus路径 | /usr/synopsys/sentaurus/W-2024.09/ |
| 工具数据库 | /home/tcad/STDB/tooldb_tcad |
| SWB图标目录 | /usr/synopsys/sentaurus/W-2024.09/tcad/current/lib/glib2/icons/ |
| 插件部署路径 | /home/tcad/work/deepseek_tcad_plugin/ |
| 测试项目路径 | /home/tcad/work/auto_sentaurus_project/PN_Diode_Project/ |

---

## 版本历史

### v1.0.0 (2024-05-12)

- 初始版本发布
- 支持代码审查、结果分析、参数优化、报告生成
- 双环境架构（GUI + gpythonsh）
- SWB集成工具数据库
- 支持DeepSeek API
