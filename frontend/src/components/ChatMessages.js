import React, { useEffect, useRef } from 'react';
import Message from './Message';
import TypingIndicator from './TypingIndicator';
import './ChatMessages.css';

const ChatMessages = ({ messages, isTyping }) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  return (
    <div className="chat-messages">
      {/* 初始欢迎消息 */}
      <Message 
        content="👋 你好！我是Yomi AI助手，可以帮您回答问题、查找文档、使用工具等。请输入您的问题！"
        sender="bot"
        type="normal"
      />
      
      {/* 聊天消息 */}
      {messages.map((message, index) => (
        <Message 
          key={message.id || index}
          content={message.content}
          sender={message.sender}
          type={message.type}
        />
      ))}
      
      {/* 打字指示器 */}
      {isTyping && <TypingIndicator />}
      
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessages;
