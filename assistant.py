from typing import List, Dict, Any, Optional
import json
from client import DeepSeekClient
from tools import global_registry
from config import Config

class Assistant:
    """AI 助手"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.from_env()
        self.client = DeepSeekClient(self.config)
        self.messages: List[Dict[str, Any]] = []
        self.tools = global_registry
        self.tool_definitions = self.tools.get_tool_definitions()
    
    def reset(self):
        """重置对话"""
        self.messages = []
    
    def add_message(self, role: str, content: str, **kwargs):
        """添加消息到对话历史"""
        message = {"role": role, "content": content, **kwargs}
        self.messages.append(message)
    
    def add_user_message(self, content: str):
        """添加用户消息"""
        self.add_message("user", content)
    
    def add_assistant_message(self, content: str, **kwargs):
        """添加助手消息"""
        self.add_message("assistant", content, **kwargs)
    
    def add_tool_result(self, tool_call_id: str, content: str):
        """添加工具执行结果"""
        self.add_message("tool", content, tool_call_id=tool_call_id)
    
    def process_tool_calls(self, tool_calls: List) -> List[Dict[str, Any]]:
        """
        处理工具调用
        """
        results = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            print(f"🔧 执行工具: {function_name}")
            print(f"📝 参数: {function_args}")
            
            # 执行工具
            try:
                result = self.tools.execute_tool(function_name, **function_args)
                print(f"📊 结果: {result}")
            except Exception as e:
                result = f"工具执行失败: {str(e)}"
                print(f"❌ 错误: {result}")
            
            results.append({
                "tool_call_id": tool_call.id,
                "content": result
            })
        
        return results
    
    def chat(self, user_input: str, verbose: bool = True) -> str:
        """
        对话主循环
        """
        # 添加用户消息
        self.add_user_message(user_input)
        
        if verbose:
            print("=" * 60)
            print(f"📤 用户: {user_input}")
            print("=" * 60)
        
        # 最多循环 max_turns 次
        for turn in range(self.config.max_turns):
            if verbose:
                print(f"\n🔄 第 {turn + 1} 轮对话")
            
            # 调用 API
            response = self.client.chat_completion(
                messages=self.messages,
                tools=self.tool_definitions if self.tool_definitions else None
            )
            
            assistant_message = self.client.get_response_message(response)
            
            # 检查是否有工具调用
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                if verbose:
                    print(f"🤔 助手决定调用工具")
                    for tc in assistant_message.tool_calls:
                        print(f"   ├─ {tc.function.name}")
                
                # 添加助手的响应
                self.messages.append(assistant_message.model_dump())
                
                # 处理工具调用
                tool_results = self.process_tool_calls(assistant_message.tool_calls)
                
                # 添加工具结果
                for result in tool_results:
                    self.add_tool_result(result["tool_call_id"], result["content"])
                
                # 继续循环，让模型处理工具结果
                continue
            
            # 没有工具调用，获取最终答案
            content = self.client.get_content(response)
            if content:
                if verbose:
                    print(f"\n📢 助手: {content}")
                return content
            
            # 如果既没有工具调用也没有内容，退出
            break
        
        return "达到最大轮数限制，未能完成回答。"
    
    def chat_simple(self, user_input: str) -> str:
        """
        简单对话（使用 max_turns 参数，由 SDK 自动处理）
        """
        self.add_user_message(user_input)
        
        response = self.client.client.chat.completions.create(
            model=self.config.model,
            messages=self.messages,
            tools=self.tool_definitions,
            max_turns=self.config.max_turns
        )
        
        content = response.choices[0].message.content
        self.add_assistant_message(content)
        return content