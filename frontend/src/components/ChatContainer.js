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

  // 调试：监控工具确认状态
  React.useEffect(() => {
    if (toolConfirmation) {
      console.log('ChatContainer: 工具确认数据更新:', toolConfirmation);
    }
  }, [toolConfirmation]);

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
        <>
          {console.log('渲染工具确认模态框:', toolConfirmation)}
          <ToolConfirmationModal
            toolData={toolConfirmation}
            onConfirm={confirmTool}
            onClose={closeToolConfirmation}
          />
        </>
      )}
      
      {/* 调试信息 */}
      {toolConfirmation && (
        <div style={{
          position: 'fixed',
          top: '10px',
          right: '10px',
          background: 'red',
          color: 'white',
          padding: '10px',
          zIndex: 9999
        }}>
          工具确认对话框应该显示！
        </div>
      )}
    </div>
  );
};

export default ChatContainer;
