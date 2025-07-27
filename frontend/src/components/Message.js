import React from 'react';
import './Message.css';
import ToolMessage from './ToolMessage';

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

  return (
    <div className={`message ${sender}`}>
      <div className={getMessageClass()}>
        {content}
      </div>
    </div>
  );
};

export default Message;
