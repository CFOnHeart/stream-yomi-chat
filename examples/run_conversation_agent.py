"""
Standalone Conversation Agent Console Example
运行这个文件可以直接在控制台测试对话代理，无需启动API服务器

使用方法:
1. 确保已配置 agent/config/llm_config.yaml 中的API密钥
2. 运行: python examples/run_conversation_agent.py
3. 在控制台中输入消息进行对话测试
4. 输入 'quit', 'exit' 或 'bye' 退出程序

支持的数学运算测试:
- "计算 15 + 25"
- "What is 12 * 8?"  
- "50 除以 2 等于多少?"
- "100 - 30 = ?"
"""

import sys
import os
import asyncio
from pathlib import Path
from uuid import uuid4

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from agent.builder import ConversationAgent
    from utils.logger import setup_logger, get_logger
    from agent.models.loader import ModelLoader
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在项目根目录下运行此脚本")
    sys.exit(1)

# 设置日志
logger = get_logger(__name__)

class ConsoleConversationAgent:
    """控制台对话代理类"""
    
    def __init__(self, config_path: str = "agent/config/llm_config.yaml"):
        """
        初始化控制台对话代理
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.session_id = str(uuid4())
        self.agent = None
        self.conversation_count = 0
        
        print("🤖 正在初始化对话代理...")
        self._init_agent()
    
    def _init_agent(self):
        """初始化代理"""
        try:
            # 检查配置文件是否存在
            if not Path(self.config_path).exists():
                print(f"❌ 配置文件不存在: {self.config_path}")
                print("请确保配置文件存在并包含有效的API密钥")
                sys.exit(1)
            
            # 创建代理
            self.agent = ConversationAgent(self.config_path)
            print("✅ 对话代理初始化成功!")
            print(f"📝 会话ID: {self.session_id}")
            
        except Exception as e:
            print(f"❌ 代理初始化失败: {e}")
            print("请检查配置文件中的API密钥是否正确")
            sys.exit(1)
    
    async def process_message(self, message: str) -> str:
        """
        处理用户消息
        
        Args:
            message: 用户输入的消息
            
        Returns:
            代理的完整回复
        """
        print("🔄 正在处理您的消息...")
        
        response_parts = []
        tool_calls = []
        
        try:
            async for chunk in self.agent.chat_stream(message, self.session_id):
                chunk_type = chunk.get("type", "")
                
                if chunk_type == "session_info":
                    if chunk.get("was_compressed"):
                        print("💾 注意: 对话历史已被压缩以节省上下文空间")
                
                elif chunk_type == "tool_call":
                    tool_name = chunk.get("name", "unknown")
                    tool_args = chunk.get("args", {})
                    print(f"🔧 调用工具: {tool_name} 参数: {tool_args}")
                    tool_calls.append(chunk)
                
                elif chunk_type == "tool_result":
                    tool_name = chunk.get("tool_name", "unknown")
                    result = chunk.get("result", "")
                    print(f"🔧 工具 {tool_name} 结果: {result}")
                
                elif chunk_type == "message":
                    content = chunk.get("content", "")
                    response_parts.append(content)
                    # 实时显示响应内容
                    print(content, end="", flush=True)
                
                elif chunk_type == "complete":
                    print("\n✅ 消息处理完成")
                    break
                
                elif chunk_type == "error":
                    error_msg = chunk.get("content", "未知错误")
                    print(f"\n❌ 处理错误: {error_msg}")
                    return f"处理消息时发生错误: {error_msg}"
            
            full_response = "".join(response_parts)
            
            # 如果有工具调用，显示摘要
            if tool_calls:
                print(f"\n📊 本次对话使用了 {len(tool_calls)} 个工具")
            
            return full_response
            
        except Exception as e:
            error_msg = f"处理消息时发生异常: {e}"
            print(f"\n❌ {error_msg}")
            return error_msg
    
    def show_session_stats(self):
        """显示会话统计信息"""
        try:
            stats = self.agent.get_session_info(self.session_id)
            print(f"\n📊 会话统计:")
            print(f"   • 总字符数: {stats.get('total_characters', 0)}")
            print(f"   • 消息数量: {stats.get('message_count', 0)}")
            print(f"   • 需要压缩: {'是' if stats.get('needs_compression', False) else '否'}")
            print(f"   • 最大字符数: {stats.get('max_characters', 0)}")
        except Exception as e:
            print(f"❌ 获取会话统计失败: {e}")
    
    def clear_session(self):
        """清空当前会话"""
        try:
            self.agent.clear_session(self.session_id)
            print("🗑️ 会话历史已清空")
            # 生成新的会话ID
            self.session_id = str(uuid4())
            print(f"📝 新会话ID: {self.session_id}")
        except Exception as e:
            print(f"❌ 清空会话失败: {e}")
    
    async def run_interactive_session(self):
        """运行交互式会话"""
        print("\n" + "=" * 60)
        print("🎯 对话代理控制台测试程序")
        print("=" * 60)
        print("💡 提示:")
        print("   • 输入消息开始对话")
        print("   • 尝试数学运算: '15 + 25 等于多少?'")
        print("   • 输入 'stats' 查看会话统计")
        print("   • 输入 'clear' 清空会话历史")
        print("   • 输入 'quit', 'exit' 或 'bye' 退出程序")
        print("=" * 60)
        
        while True:
            try:
                # 获取用户输入
                user_input = input(f"\n[{self.conversation_count + 1}] 您: ").strip()
                
                # 检查退出命令
                if user_input.lower() in ['quit', 'exit', 'bye', '退出', 'q']:
                    print("👋 再见! 感谢使用对话代理!")
                    break
                
                # 检查特殊命令
                if user_input.lower() == 'stats':
                    self.show_session_stats()
                    continue
                
                if user_input.lower() == 'clear':
                    self.clear_session()
                    self.conversation_count = 0
                    continue
                
                # 跳过空输入
                if not user_input:
                    print("请输入一些内容...")
                    continue
                
                # 处理消息
                print(f"\n🤖 代理: ", end="")
                response = await self.process_message(user_input)
                
                self.conversation_count += 1
                
                # 每5轮对话显示一次统计
                if self.conversation_count % 5 == 0:
                    print(f"\n💭 已进行 {self.conversation_count} 轮对话")
                    self.show_session_stats()
                
            except KeyboardInterrupt:
                print("\n\n⏹️ 程序被用户中断")
                break
            except EOFError:
                print("\n\n👋 程序结束")
                break
            except Exception as e:
                print(f"\n❌ 程序运行错误: {e}")
                print("程序将继续运行...")

def main():
    """主函数"""
    # 设置日志级别
    setup_logger(__name__, level="INFO")
    
    print("🚀 启动对话代理控制台测试程序...")
    
    # 检查是否在正确的目录中
    if not Path("agent/config").exists():
        print("❌ 请在项目根目录下运行此脚本")
        print("当前目录应包含 agent/config/ 文件夹")
        sys.exit(1)
    
    try:
        # 创建并运行控制台代理
        console_agent = ConsoleConversationAgent()
        
        # 运行交互式会话
        asyncio.run(console_agent.run_interactive_session())
        
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断，正在退出...")
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
        print("请检查配置文件和依赖是否正确安装")
        sys.exit(1)

if __name__ == "__main__":
    main()
