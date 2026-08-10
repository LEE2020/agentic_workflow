import requests
from .registry import registry

@registry.register
def get_current_time():
    """
    获取当前时间
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")