# Agentic Workflow - Function Calling 实现

## 📖 项目简介

本项目展示了两种不同的方式来实现 **Function Calling**（工具调用），帮助理解大语言模型如何将自然语言转换为可执行的工具调用。通过完整的代码示例，可以深入理解其内部工作机制，并根据需要灵活定制。

---

## 🎯 核心概念

### 什么是 Function Calling？

Function Calling 是一种让大语言模型（LLM）能够**调用外部工具/函数**的机制。LLM 不直接执行代码，而是**生成结构化的调用指令**，由应用程序执行具体的工具函数。

### 工作流程
用户输入 → LLM 分析 → 判断是否需要工具 → 返回调用指令
↓
应用程序执行工具 → 返回结果
↓
LLM 理解结果 → 生成自然语言回答


---

## ✨ 功能特点

- 🔧 **完整的 Function Calling 流程**
- 🔄 **支持多轮工具调用**（自定义 `max_turns`）
- 📊 **详细的执行日志输出**
- 🛡️ **防止无限循环**
- 📦 **支持多客户端切换**（DeepSeek、OpenAI、AISuite）
- 🎨 **自动生成工具描述**（通过装饰器注册）

---

## 📁 项目结构
agentic_workflow/
├── example.py # 原生 OpenAI SDK 实现
├── example2.py # DeepLearning.AI 课程库实现
├── main.py # 主程序入口（多客户端支持）
├── clients/ # 多客户端支持
│ ├── init.py
│ ├── base.py # 客户端基类
│ ├── deepseek.py # DeepSeek 客户端
│ ├── openai.py # OpenAI 客户端
│ └── aisuite.py # AISuite 客户端
├── tools/ # 工具层
│ ├── init.py
│ ├── registry.py # 工具注册器
│ ├── weather.py # 天气工具
│ ├── time.py # 时间工具
│ ├── genqrcode.py # 二维码工具
│ └── write_txt_file.py # 文件工具
└── README.md


---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 基础依赖
pip install openai requests

# 课程库（用于 example2.py）
pip install aisuite

# 二维码支持（可选）
pip install qrcode Pillow

# 设置环境变量
export DEEPSEEK_API_KEY="your-api-key"
# 或
export OPENAI_API_KEY="your-api-key"

# 运行原生实现
python example.py

# 运行课程库实现
python example2.py

# 运行主程序（多客户端支持）
python main.py