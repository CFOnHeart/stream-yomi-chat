# Yomi Chatbot Frontend

基于 React + JavaScript 构建的对话式 AI 助手前端界面。

## 环境要求

- Node.js 16.0.0 或更高版本
- npm 或 yarn

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 启动开发服务器

```bash
npm start
```

应用将在 `http://localhost:3000` 启动

### 3. 确保后端服务运行

前端需要后端 API 服务运行在 `http://localhost:8000`

## 可用脚本

- `npm start` - 启动开发服务器
- `npm run build` - 构建生产版本
- `npm test` - 运行测试
- `npm run eject` - 弹出配置（不可逆）

## 功能特性

- 🎯 实时流式对话
- 🔧 工具调用确认界面
- 📱 响应式设计
- 🎨 现代化 UI
- ⚡ 快速响应

## 项目结构

```
src/
├── components/          # React 组件
│   ├── ChatContainer.js # 主聊天容器
│   ├── ChatHeader.js    # 聊天头部
│   ├── ChatMessages.js  # 消息列表
│   ├── ChatInput.js     # 输入框
│   ├── Message.js       # 单条消息
│   ├── StatusIndicator.js # 状态指示器
│   ├── TypingIndicator.js # 打字指示器
│   └── ToolConfirmationModal.js # 工具确认对话框
├── hooks/               # React Hooks
│   └── useChatClient.js # 聊天客户端逻辑
├── App.js              # 主应用组件
├── index.js            # 应用入口
└── index.css           # 全局样式
```

## 后端集成

前端通过以下 API 与后端通信：

- `POST /chat/stream` - 流式聊天
- `POST /chat/tool-confirm` - 工具确认

代理配置已在 `package.json` 中设置，开发时会自动代理到 `http://localhost:8000`。

## 构建部署

```bash
npm run build
```

构建文件将输出到 `build/` 目录，可直接部署到任何静态文件服务器。

🎯 Key Features Implemented
1. ✅ Complete UI Replication
    + Identical styling and layout to original HTML
    + Gradient backgrounds and modern design
    + Responsive layout

2. ✅ React Component Architecture
    + Modular component structure
    + Custom hooks for state management
    + Clean separation of concerns

3. ✅ Streaming Chat Support
    + Real-time message streaming
    + Typing indicators
    + Status updates

4. ✅ Tool Confirmation Modal
    + Interactive parameter editing
    + Confidence level display
    + Proper form handling

5. ✅ Complete Event Handling
    + All stream events from original
    + Error handling
    + Session management