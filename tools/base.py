import inspect
import json
from typing import Callable, Dict, Any, List, Optional
from functools import wraps

class Tool:
    """工具基类"""
    
    def __init__(self, func: Callable):
        self.func = func
        self.name = func.__name__
        self.description = func.__doc__ or f"调用 {self.name} 函数"
        self.tool_def = self._generate_tool_def()
    
    def _generate_tool_def(self) -> Dict[str, Any]:
        """生成工具描述"""
        sig = inspect.signature(self.func)
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # 推断参数类型
            param_type = self._infer_type(param.annotation)
            
            properties[param_name] = {
                "type": param_type,
                "description": f"参数 {param_name}"
            }
            
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
    
    def _infer_type(self, annotation) -> str:
        """推断参数类型"""
        if annotation == int:
            return "integer"
        elif annotation == float:
            return "number"
        elif annotation == bool:
            return "boolean"
        elif annotation == list:
            return "array"
        elif annotation == dict:
            return "object"
        else:
            return "string"
    
    def execute(self, **kwargs) -> Any:
        """执行工具函数"""
        return self.func(**kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """返回工具描述字典"""
        return self.tool_def


def tool_function(func: Callable) -> Callable:
    """
    装饰器：将函数标记为工具
    """
    tool = Tool(func)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    # 将工具信息附加到函数
    wrapper._tool = tool
    wrapper._tool_def = tool.to_dict()
    
    return wrapper


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
    
    def register(self, func: Callable) -> Callable:
        """注册工具"""
        tool = Tool(func)
        self._tools[tool.name] = tool
        return func
    
    def register_decorator(self):
        """返回一个注册装饰器"""
        def decorator(func: Callable) -> Callable:
            return self.register(func)
        return decorator
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[Tool]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取所有工具定义"""
        return [tool.to_dict() for tool in self._tools.values()]
    
    def execute_tool(self, name: str, **kwargs) -> Any:
        """执行工具"""
        tool = self.get_tool(name)
        if tool:
            return tool.execute(**kwargs)
        raise ValueError(f"工具 {name} 未找到")


# 创建全局工具注册表
global_registry = ToolRegistry()