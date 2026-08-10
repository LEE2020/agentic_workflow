"""
工具包
"""
from .registry import registry
from .genqrcode import generate_qr_code
from .write_txt_file import write_txt_file
from .weather import get_weather_from_ip, get_weather_by_city
from .time import get_current_time
__version__ = "1.0.0"
# 导出所有工具函数
__all__ = [
    'generate_qr_code',
    'write_txt_file',
    'get_weather_from_ip',
    'get_weather_by_city',
    'get_current_time'
]

# 调试：打印注册状态
print(f"🔧 tools 包加载完成，已注册 {len(registry.get_functions())} 个工具")
for func in registry.get_functions():
    print(f"  ✅ {func.__name__}")

def get_tools():
    """获取所有工具描述（用于 API 调用）"""
    return registry.get_tools()


# 便捷函数：获取所有工具函数
def get_functions():
    """获取所有工具函数"""
    return registry.get_functions()


# 便捷函数：执行工具
def run_tool(tool_name: str, arguments: dict):
    """执行工具"""
    return registry.execute(tool_name, arguments)


