import React, { useState } from 'react';
import './ChatInput.css';

const ChatInput = ({ onSendMessage, isProcessing }) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmedMessage = message.trim();
    if (trimmedMessage && !isProcessing) {
      onSendMessage(trimmedMessage);
      setMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-input-container">
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input 
          type="text" 
          className="chat-input" 
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="输入您的问题..."
          disabled={isProcessing}
          autoComplete="off"
        />
        <button 
          type="submit" 
          className="send-button"
          disabled={isProcessing || !message.trim()}
        >
          {isProcessing ? '处理中...' : '发送'}
        </button>
      </form>
    </div>
  );
};

export default ChatInput;
