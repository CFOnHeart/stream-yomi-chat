import React from 'react';
import './Message.css';
import ToolMessage from './ToolMessage';
import MarkdownRenderer from './MarkdownRenderer';

const Message = ({ content, sender, type = 'normal' }) => {
  const getMessageClass = () => {
    let className = 'message-content';
    
    switch (type) {
      case 'event':
        className += ' event-message';
        break;
      case 'tool':
        className += ' tool-message';
        break;
      case 'error':
        className += ' error-message';
        break;
      default:
        break;
    }
    
    return className;
  };

  // 如果是工具类型的消息且内容是对象，使用 ToolMessage 组件
  if ((type === 'tool' || type === 'event') && typeof content === 'object' && content.type) {
    return (
      <div className={`message ${sender}`}>
        <ToolMessage content={content} type={type} />
      </div>
    );
  }

  // 检查是否应该渲染为 Markdown
  const shouldRenderMarkdown = (content) => {
    if (typeof content !== 'string') return false;
    
    // 检查是否包含 Markdown 标记
    const markdownPatterns = [
      /^#{1,6}\s+/m,           // 标题
      /\*\*.*?\*\*/,           // 粗体
      /\*.*?\*/,               // 斜体
      /`.*?`/,                 // 行内代码
      /```[\s\S]*?```/,        // 代码块
      /^\s*[-*+]\s+/m,         // 无序列表
      /^\s*\d+\.\s+/m,         // 有序列表
      /^\s*>\s+/m,             // 引用
      /\[.*?\]\(.*?\)/,        // 链接
      /!\[.*?\]\(.*?\)/        // 图片
    ];
    
    return markdownPatterns.some(pattern => pattern.test(content));
  };

  return (
    <div className={`message ${sender}`}>
      <div className={getMessageClass()}>
        {shouldRenderMarkdown(content) && sender === 'bot' ? (
          <MarkdownRenderer content={content} />
        ) : (
          content
        )}
      </div>
    </div>
  );
};

export default Message;
