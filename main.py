import os
from config import Config
from assistant import Assistant

def main():
    """主程序"""
    
    # 设置 API Key
    os.environ["DEEPSEEK_API_KEY"] = "your-api-key-here"
    
    # 创建配置
    config = Config(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        model="deepseek-chat",
        max_turns=3
    )
    
    # 创建助手
    assistant = Assistant(config)
    
    # 测试对话
    test_prompts = [
        "今天天气怎么样？",
        "我在上海，天气如何？",
        "现在几点了？顺便告诉我北京的天气",
    ]
    
    for prompt in test_prompts:
        print("\n" + "=" * 60)
        print("📝 新对话")
        print("=" * 60)
        
        result = assistant.chat(prompt)
        
        print("\n" + "=" * 60)
        print("✅ 最终回答")
        print("=" * 60)
        print(result)
        print("\n")
        
        # 重置对话
        assistant.reset()
        print("-" * 60)

if __name__ == "__main__":
    main()