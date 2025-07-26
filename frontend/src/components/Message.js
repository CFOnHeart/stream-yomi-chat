import React from 'react';
import './Message.css';

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

  return (
    <div className={`message ${sender}`}>
      <div className={getMessageClass()}>
        {content}
      </div>
    </div>
  );
};

export default Message;
