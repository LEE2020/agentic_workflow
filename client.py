from openai import OpenAI
from typing import List, Dict, Any, Optional
from config import Config

class DeepSeekClient:
    """DeepSeek API 客户端"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.from_env()
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        发送聊天请求
        """
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            tools=tools or [],
            tool_choice=tool_choice,
            temperature=temperature or self.config.temperature,
        )
        return response
    
    def get_response_message(self, response) -> Dict[str, Any]:
        """提取响应消息"""
        return response.choices[0].message
    
    def get_tool_calls(self, response) -> List[Dict[str, Any]]:
        """提取工具调用"""
        message = self.get_response_message(response)
        return message.tool_calls if hasattr(message, 'tool_calls') else []
    
    def get_content(self, response) -> Optional[str]:
        """提取响应内容"""
        message = self.get_response_message(response)
        return message.content