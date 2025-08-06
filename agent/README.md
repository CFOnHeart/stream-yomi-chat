# Agent Architecture Documentation

## 概述

这个重构后的 Agent 架构提供了一个可扩展的框架，让您可以轻松创建不同类型的 AI Agent，同时共享核心功能如流式聊天、工具调用和会话管理。

## 架构组件

### 1. BaseAgent (基础 Agent 类)
- 位置：`agent/base.py`
- 提供所有 Agent 的通用功能
- 核心功能：`chat_stream`、会话管理、工具执行、确认机制
- 抽象方法需要子类实现：`_initialize_agent`、`_get_tools`、`_build_graph`

### 2. AgentFactory (Agent 工厂)
- 位置：`agent/factory.py`
- 集中管理和创建不同类型的 Agent
- 支持动态注册新的 Agent 类型
- 提供便捷的创建方法

### 3. ConversationAgent (对话 Agent)
- 位置：`agent/conversation.py`
- BaseAgent 的具体实现
- 专注于对话和数学工具调用
- 原有功能完全保留

### 4. 向后兼容层
- 位置：`agent/builder.py`
- 保持原有 API 不变
- 内部使用新架构实现

## 使用方法

### 创建现有的对话 Agent

```python
from agent.factory import AgentFactory

# 方法 1: 使用工厂
agent = AgentFactory.create_agent('conversation', 'path/to/config.yaml')

# 方法 2: 直接导入 (向后兼容)
from agent.builder import ConversationAgent
agent = ConversationAgent('path/to/config.yaml')

# 方法 3: 使用便捷函数
from agent.factory import create_conversation_agent
agent = create_conversation_agent('path/to/config.yaml')
```

### 创建新的 Agent 类型

#### 步骤 1: 创建新的 Agent 类

```python
from agent.base import BaseAgent
from typing import List
from langchain.tools import BaseTool

class MyCustomAgent(BaseAgent):
    """自定义 Agent 实现"""
    
    def _initialize_agent(self):
        """初始化自定义组件"""
        self.tools = self._get_tools()
        self.tool_node = ToolNode(self.tools) if self.tools else None
        self.llm_with_tools = self.llm.bind_tools(self.tools) if self.tools else self.llm
        self.graph = self._build_graph()
    
    def _get_tools(self) -> List[BaseTool]:
        """获取该 Agent 特有的工具"""
        # 返回您的自定义工具列表
        return []
    
    def _build_graph(self):
        """构建该 Agent 的 LangGraph"""
        # 实现您的图构建逻辑
        from langgraph.prebuilt import create_react_agent
        return create_react_agent(self.llm, self.tools)
```

#### 步骤 2: 注册新的 Agent 类型

```python
from agent.factory import AgentFactory

# 注册新的 Agent 类型
AgentFactory.register_agent_type('my_custom', MyCustomAgent)

# 现在可以创建该类型的 Agent
agent = AgentFactory.create_agent('my_custom', 'config.yaml')
```

### 查看可用的 Agent 类型

```python
from agent.factory import AgentFactory

# 获取所有可用类型
available_types = AgentFactory.get_available_agent_types()
print(f"Available types: {available_types}")

# 获取特定类型的信息
info = AgentFactory.get_agent_info('conversation')
print(f"Agent info: {info}")
```

### 使用 Agent 进行对话

```python
import asyncio

async def chat_example():
    agent = AgentFactory.create_agent('conversation', 'config.yaml')
    
    async for chunk in agent.chat_stream("Hello, can you help me with math?"):
        if chunk["type"] == "message":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "tool_detected":
            print(f"\n[Tool detected: {chunk['name']}]")
        elif chunk["type"] == "complete":
            print("\n[Conversation complete]")

# 运行示例
asyncio.run(chat_example())
```

## 示例 Agent 实现

查看 `agent/examples.py` 文件，其中包含：
- `CodeAgent`: 专门处理代码相关任务的 Agent
- `DataAnalysisAgent`: 专门处理数据分析的 Agent

这些示例展示了如何扩展基础架构来创建专门的 Agent。

## 扩展指南

### 添加自定义工具

1. 创建工具类（继承 `BaseTool`）
2. 在 Agent 的 `_get_tools` 方法中包含您的工具
3. 工具会自动集成到确认和执行流程中

### 自定义流式行为

如果需要自定义流式行为，可以重写 `_stream_graph_response` 方法：

```python
class MyAgent(BaseAgent):
    async def _stream_graph_response(self, messages):
        # 自定义流式处理逻辑
        async for chunk in super()._stream_graph_response(messages):
            # 可以修改或过滤 chunk
            yield chunk
```

### 自定义会话管理

可以重写会话相关方法来实现自定义行为：

```python
class MyAgent(BaseAgent):
    def get_session_info(self, session_id: str):
        info = super().get_session_info(session_id)
        # 添加自定义信息
        info['custom_data'] = 'something'
        return info
```

## 核心优势

1. **代码复用**: 核心功能如 `chat_stream` 在所有 Agent 中共享
2. **易于扩展**: 只需实现几个抽象方法即可创建新 Agent
3. **向后兼容**: 原有代码无需修改
4. **集中管理**: 通过工厂模式统一管理所有 Agent 类型
5. **灵活配置**: 每个 Agent 可以有自己的工具集和行为

## 迁移指南

如果您有现有的代码使用 `ConversationAgent`：

1. **无需修改**: 原有导入和使用方式继续有效
2. **可选升级**: 可以逐步迁移到使用 `AgentFactory`
3. **扩展方便**: 可以轻松添加新的 Agent 类型而不影响现有功能

这个架构让您可以专注于实现特定领域的逻辑，而不需要重复实现基础的聊天和工具管理功能。
