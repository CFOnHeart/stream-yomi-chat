import React from 'react';
import ChatHeader from './ChatHeader';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import StatusIndicator from './StatusIndicator';
import ToolConfirmationModal from './ToolConfirmationModal';
import { useChatClient } from '../hooks/useChatClient';
import './ChatContainer.css';

const ChatContainer = () => {
  const {
    messages,
    isProcessing,
    status,
    isTyping,
    toolConfirmation,
    sendMessage,
    confirmTool,
    closeToolConfirmation
  } = useChatClient();

  return (
    <div className="chat-container">
      <ChatHeader />
      
      <ChatMessages 
        messages={messages} 
        isTyping={isTyping}
      />
      
      <StatusIndicator status={status} />
      
      <ChatInput 
        onSendMessage={sendMessage}
        isProcessing={isProcessing}
      />
      
      {toolConfirmation && (
        <ToolConfirmationModal
          toolData={toolConfirmation}
          onConfirm={confirmTool}
          onClose={closeToolConfirmation}
        />
      )}
    </div>
  );
};

export default ChatContainer;
