# agentic_workflow
这个 example.py 程序展示了如何在不依赖高级库的情况下，用原生 OpenAI SDK 实现 Turning functions into tools功能。它包含了完整流程：

定义工具函数（实际执行逻辑）

定义工具描述（告诉 AI 有哪些工具）

循环调用 API（支持多轮工具调用）

执行工具并累积结果（自动化的工具调用循环）

返回最终回答（生成自然语言响应）

通过这个实现，您可以深入理解 Function Calling 的内部工作机制，并根据需要灵活定制。

Function Calling 的核心机制
工具注册：将函数描述为 JSON Schema

意图识别：LLM 判断是否需要工具

工具选择：LLM 选择最合适的工具

参数生成：LLM 生成调用参数

外部执行：应用程序执行工具

结果整合：LLM 根据结果生成回答

2. 使用 deeplearning.ai的课程中的库来实现 Turning functions into tools ,example2.py