import inspect
from typing import get_type_hints, Callable, Dict, List, Any
def function_to_tool_enhanced(func):
    """
    增强版：将 Python 函数转换为工具描述
    支持类型注解、默认值、文档字符串解析
    """
    import inspect
    from typing import get_type_hints, Optional
    # 基本信息
    name = func.__name__
    description = func.__doc__ or f"调用 {name} 函数"
    description = description.strip()
    
    # 获取类型提示
    type_hints = get_type_hints(func)
    
    # 解析参数
    sig = inspect.signature(func)
    properties = {}
    required = []
    
    # 类型映射
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        Optional[str]: "string",
        Optional[int]: "integer",
        Optional[float]: "number",
        Optional[bool]: "boolean",
        Optional[list]: "array",
        Optional[dict]: "object",
    }
    
    for param_name, param in sig.parameters.items():
        if param_name == 'self':
            continue
        
        # 获取参数类型
        param_type = type_map.get(type_hints.get(param_name, str), "string")
        
        # 构建参数描述
        param_description = f"参数 {param_name}"
        
        # 如果有默认值，添加到描述中
        if param.default != inspect.Parameter.empty:
            param_description += f" (默认: {param.default})"
        
        properties[param_name] = {
            "type": param_type,
            "description": param_description
        }
        
        # 没有默认值则为必需
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
    
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }

# ============================================
# 工具注册器（类似装饰器模式）
# ============================================
class ToolRegistry:
    """工具注册管理器"""
    
    def __init__(self):
        self._tools = []
        self._functions = []
        self._tool_map: Dict[str, Callable] = {}
    
    def register(self, func):
        """注册工具函数"""
        self._functions.append(func)
        self._tools.append(function_to_tool_enhanced(func))
        self._tool_map[func.__name__] = func
        return func
    
    def get_tools(self):
        """获取所有工具描述"""
        return self._tools
    
    def get_functions(self):
        """获取所有工具函数"""
        return self._functions

    def get_tool_map(self) -> Dict[str, Callable]:
        """获取工具映射 {name: function}"""
        return self._tool_map

    def execute(self, tool_name: str, arguments: dict):
        """执行工具"""
        if tool_name in self._tool_map:
            return self._tool_map[tool_name](**arguments)
        return f"未知工具: {tool_name}"
    
    
# 创建全局注册器实例
registry = ToolRegistry()
