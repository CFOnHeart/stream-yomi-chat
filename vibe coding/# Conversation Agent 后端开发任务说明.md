# Conversation Agent 后端开发任务说明

## 🧠 项目目标

使用 `FastAPI + LangGraph + LangChain` 技术栈，构建一个支持多模型、多工具调用、流式输出、会话记忆管理的 **Conversation Agent 后端服务**，具备良好的代码结构、可扩展性与配置灵活性。

---

## 🛠️ 技术栈要求

- **Web 框架**：FastAPI（运行在端口 `8000`）
- **Agent 框架**：LangGraph + LangChain
- **虚拟环境**：使用 `venv` 管理依赖
- **数据库**：SQLite（可扩展为其他数据库）
- **配置文件**：支持 YAML / JSON 格式

---

## 📦 功能模块需求

### 1. Logging 机制

- 使用标准 logging 框架（如 `loguru` 或 `logging` 模块）
- 禁止使用 `print` 输出
---

### 2. 流式输出支持

- 支持字符逐步输出（可通过 `asyncio.sleep` 模拟）
- 支持一次性返回完整响应
- 输出方式支持：
  - Server-Sent Events（SSE）
  - LangChain 的 `streamable event` 协议
- 主接口路径：`/chat/stream`

---

### 3. LLM 模型配置与加载

- 支持通过配置文件指定模型：
  - 示例：`azure/gpt-4.1`、`openai/gpt-4o`、`google/gemini-pro`
- 支持 Provider：
  - Azure OpenAI
  - OpenAI
  - Google
- 配置文件路径作为 Agent 初始化参数传入
- 模型加载逻辑应抽象为统一接口，便于扩展

---

### 4. Embedding 模型配置

- 同样支持通过配置文件指定：
  - 示例：`azure/text-embedding-ada-002`
- 支持 Provider：
  - Azure OpenAI
  - OpenAI
  - Google
- 与 LLM 模型配置结构保持一致

---

### 5. Tool 调用机制

- 创建4个简单地math tool用于测试：
  - `add`: 两数相加
  - `subtract`: 两数相减
  - `multiply`: 两数相乘
  - `divide`: 两数相除
- Agent 根据用户输入判断是否匹配 Tool Schema
- 若匹配：
  - 调用对应 Tool
  - 将 Tool 的调用结果与 Schema 一并作为输入传给 LLM
  - Tool 的调用过程与结果需通过 stream 返回给用户
- 若无匹配 Tool，直接将用户输入交给 LLM 处理

---

### 6. ChatHistory 与 Memory 管理

- 总字符数 ≤ 3200：
  - 正常追加用户、AI、Tool 等消息
- 总字符数 > 3200：
  - 使用 LLM 对历史进行摘要（summarize）
  - 摘要信息不存入数据库，仅用于内存中压缩上下文
- 支持多类型消息（可扩展）

---

### 7. 会话持久化与数据库设计

- 使用 SQLite 存储会话信息，路径为：
  ```
  stream-yomi-chatbot/database/chat_history.db
  ```
- 数据库设计要求：
- 与 Agent 解耦
- 提供抽象接口，便于未来扩展其他数据库
- 支持按 session_id 加载历史记录
- 不存储 summarize 后的内容，仅存原始消息

---

## 📁 项目结构建议（示意）
```
stream-yomi-chatbot/ ├── main.py ├── agent/ │ ├── builder.py │ ├── memory.py │ ├── tools/ │ ├── models/ │ └── config/ │ ├── llm_config.yaml │ └── embedding_config.yaml ├── database/ │ ├── chat_history.db │ └── interface.py ├── api/ │ └── routes.py ├── utils/ │ └── logger.py └── README.md
```

---

## 📄 配置文件示例（YAML）

```yaml
llm:
  provider: azure
  model: gpt-4.1
  api_key: YOUR_KEY
  endpoint: https://your-endpoint.openai.azure.com/

embedding:
  provider: openai
  model: text-embedding-ada-002
  api_key: YOUR_KEY
```

## 开发规范补充
所有模块应具备良好的抽象接口
代码应简洁直观，便于维护与扩展
提供完整的说明文档（README）