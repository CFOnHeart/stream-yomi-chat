import { useState, useCallback } from 'react';

const generateSessionId = () => {
  return 'session_' + Math.random().toString(36).substr(2, 9);
};

export const useChatClient = () => {
  const [messages, setMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [status, setStatus] = useState('准备就绪');
  const [isTyping, setIsTyping] = useState(false);
  const [toolConfirmation, setToolConfirmation] = useState(null);
  const [sessionId] = useState(generateSessionId());

  const addMessage = useCallback((content, sender, type = 'normal') => {
    const newMessage = { 
      content, 
      sender, 
      type, 
      id: Date.now() + Math.random() // 添加唯一标识符
    };
    setMessages(prev => [...prev, newMessage]);
    return newMessage;
  }, []);

  const updateStatus = useCallback((newStatus) => {
    setStatus(newStatus);
  }, []);

  const handleStreamEvent = useCallback((event, currentBotMessage) => {
    console.log('收到流式事件:', event);

    switch (event.type) {
      case 'session_info':
        updateStatus('会话开始...');
        console.log('会话ID:', event.session_id);
        break;

      case 'message':
        setIsTyping(true);
        updateStatus('AI正在回复...');
        
        // 如果没有当前消息，创建一个新的空消息并添加到消息列表
        if (!currentBotMessage) {
          currentBotMessage = { 
            content: event.content, 
            sender: 'bot', 
            type: 'normal',
            id: Date.now() + Math.random() // 添加唯一标识符
          };
          setMessages(prev => [...prev, currentBotMessage]);
        } else {
          // 更新现有消息的内容
          currentBotMessage.content += event.content;
          
          // 更新消息列表中的对应消息
          setMessages(prev => {
            const updated = [...prev];
            const messageIndex = updated.findIndex(msg => msg && msg.id === currentBotMessage.id);
            if (messageIndex !== -1) {
              updated[messageIndex] = { ...currentBotMessage };
            }
            return updated;
          });
        }
        
        // 如果消息完成，停止输入指示器
        if (event.is_complete) {
          setIsTyping(false);
          updateStatus('响应完成');
          // 不要在这里设置为 null，让它在 complete 或 stream_end 事件中处理
        }
        break;

      case 'tool_call':
        // 发送结构化的工具调用信息
        const toolCallData = {
          toolName: event.name,
          description: event.description || '',
          argsSchema: event.args_schema || {},
          type: 'tool_call'
        };
        
        addMessage(toolCallData, 'bot', 'tool');
        updateStatus('正在执行工具...');
        break;

      case 'tool_result':
        // 发送结构化的工具结果信息
        const toolResultData = {
          toolName: event.tool_name,
          result: event.result,
          args: event.args || {},
          description: event.description || '',
          argsSchema: event.args_schema || {},
          type: 'tool_result'
        };
        
        addMessage(toolResultData, 'bot', 'event');
        break;

      case 'complete':
        setIsTyping(false);
        updateStatus('准备就绪');
        currentBotMessage = null; // 清空当前消息引用
        break;

      case 'stream_end':
        setIsTyping(false);
        updateStatus('准备就绪');
        currentBotMessage = null; // 清空当前消息引用
        break;

      case 'error':
        addMessage(`❌ 错误: ${event.content}`, 'bot', 'error');
        updateStatus('发生错误');
        setIsTyping(false);
        break;
        
      default:
        console.log('未知事件类型:', event.type);
        break;
    }

    return currentBotMessage;
  }, [addMessage, updateStatus, setIsTyping, setMessages]);

  const streamChat = useCallback(async (message) => {
    return new Promise((resolve, reject) => {
      // 使用 EventSource 进行真正的 SSE 连接
      const url = new URL('/chat/stream', window.location.origin);
      
      // 创建 POST 请求来启动流式响应
      fetch('/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          session_id: sessionId
        })
      }).then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let currentBotMessage = null;
        let buffer = '';

        const processStream = () => {
          return reader.read().then(({ done, value }) => {
            if (done) {
              resolve();
              return;
            }

            // 将新数据添加到缓冲区
            buffer += decoder.decode(value, { stream: true });
            
            // 按行分割数据
            const lines = buffer.split('\n');
            // 保留最后一个不完整的行
            buffer = lines.pop() || '';

            // 处理每一行
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6).trim();

                if (data === '[DONE]' || data === '') {
                  continue;
                }

                try {
                  const event = JSON.parse(data);
                  currentBotMessage = handleStreamEvent(event, currentBotMessage);
                } catch (e) {
                  console.error('Failed to parse event:', e, data);
                }
              }
            }

            // 继续读取下一个块
            return processStream();
          });
        };

        return processStream();
      }).catch(reject);
    });
  }, [sessionId, handleStreamEvent]);

  const sendMessage = useCallback(async (message) => {
    if (isProcessing) return;

    // 添加用户消息
    addMessage(message, 'user');
    setIsProcessing(true);

    try {
      await streamChat(message);
    } catch (error) {
      console.error('Chat error:', error);
      addMessage('抱歉，发生了网络错误。请稍后重试。', 'bot', 'error');
    } finally {
      setIsProcessing(false);
    }
  }, [isProcessing, addMessage, streamChat]);

  const confirmTool = useCallback(async (confirmed, toolArgs = {}) => {
    try {
      const response = await fetch('/chat/tool-confirm', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          confirmed: confirmed,
          tool_args: toolArgs
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('工具确认结果:', result);

      // 关闭对话框
      setToolConfirmation(null);

      // 更新状态
      if (confirmed) {
        updateStatus('工具执行已确认，正在处理...');
      } else {
        updateStatus('工具执行已取消');
      }

    } catch (error) {
      console.error('工具确认失败:', error);
      addMessage('工具确认失败，请重试', 'bot', 'error');
      setToolConfirmation(null);
    }
  }, [sessionId, updateStatus, addMessage]);

  const closeToolConfirmation = useCallback(() => {
    setToolConfirmation(null);
  }, []);

  return {
    messages,
    isProcessing,
    status,
    isTyping,
    toolConfirmation,
    sendMessage,
    confirmTool,
    closeToolConfirmation
  };
};
