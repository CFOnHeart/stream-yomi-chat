import React, { useState } from 'react';
import './ToolConfirmationModal.css';

const ToolConfirmationModal = ({ toolData, onConfirm, onClose }) => {
  const [toolArgs, setToolArgs] = useState(() => {
    const args = {};
    const properties = toolData.tool_schema?.parameters?.properties || {};
    
    // 初始化参数值
    Object.keys(properties).forEach(paramName => {
      args[paramName] = toolData.suggested_args?.[paramName] || '';
    });
    
    return args;
  });

  const handleParamChange = (paramName, value) => {
    setToolArgs(prev => ({
      ...prev,
      [paramName]: value
    }));
  };

  const handleConfirm = () => {
    onConfirm(true, toolArgs);
  };

  const handleCancel = () => {
    onConfirm(false, {});
  };

  const handleModalClick = (e) => {
    if (e.target === e.currentTarget) {
      handleCancel();
    }
  };

  const properties = toolData.tool_schema?.parameters?.properties || {};

  return (
    <div className="tool-confirmation-modal" onClick={handleModalClick}>
      <div className="tool-confirmation-dialog">
        <div className="tool-confirmation-header">
          <span style={{ fontSize: '24px' }}>🔧</span>
          <h3>工具执行确认</h3>
        </div>
        
        <p><strong>检测到工具:</strong> {toolData.tool_name}</p>
        <p>{toolData.message}</p>
        
        <div className="confidence-indicator">
          <span>置信度:</span>
          <div className="confidence-bar">
            <div 
              className="confidence-fill" 
              style={{ width: `${(toolData.confidence * 100)}%` }}
            ></div>
          </div>
          <span>{(toolData.confidence * 100).toFixed(0)}%</span>
        </div>
        
        <div className="tool-details">
          <h4>工具描述:</h4>
          <p>{toolData.tool_schema?.description || '执行特定任务的工具'}</p>
          
          <h4>参数:</h4>
          <div className="tool-parameters">
            {Object.keys(properties).length === 0 ? (
              <p style={{ color: '#666', fontStyle: 'italic' }}>此工具无需参数</p>
            ) : (
              Object.entries(properties).map(([paramName, paramSchema]) => (
                <div key={paramName} className="tool-param">
                  <label>
                    {paramName}
                    {paramSchema.description && ` - ${paramSchema.description}`}
                  </label>
                  <input
                    type={paramSchema.type === 'number' ? 'number' : 'text'}
                    value={toolArgs[paramName] || ''}
                    onChange={(e) => handleParamChange(paramName, e.target.value)}
                    placeholder={paramSchema.default || ''}
                  />
                </div>
              ))
            )}
          </div>
        </div>
        
        <div className="confirmation-buttons">
          <button className="cancel-button" onClick={handleCancel}>
            取消
          </button>
          <button className="confirm-button" onClick={handleConfirm}>
            确认执行
          </button>
        </div>
      </div>
    </div>
  );
};

export default ToolConfirmationModal;
