# agentic_workflow
这个程序展示了如何在不依赖高级库的情况下，用原生 OpenAI SDK 实现 max_turns 功能。它包含了 Function Calling 的完整流程：

定义工具函数（实际执行逻辑）

定义工具描述（告诉 AI 有哪些工具）

循环调用 API（支持多轮工具调用）

执行工具并累积结果（自动化的工具调用循环）

返回最终回答（生成自然语言响应）

通过这个实现，您可以深入理解 Function Calling 的内部工作机制，并根据需要灵活定制。