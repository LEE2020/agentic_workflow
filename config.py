import json
import os
from openai import OpenAI

# 配置
API_KEY = "your-deepseek-api-key"
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"

# 初始化客户端
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)