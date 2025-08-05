import React, { useState } from 'react';
import './ToolConfirmationModal.css';

const ToolConfirmationModal = ({ toolData, onConfirm, onClose }) => {
  const [toolArgs, setToolArgs] = useState(() => {
    const args = {};
    const properties = toolData.args_schema || {};
    
    // 初始化参数值
    Object.keys(properties).forEach(paramName => {
      args[paramName] = toolData.args?.[paramName] || '';
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

  const formatParameterType = (type) => {
    if (typeof type === 'string') {
      return type;
    }
    return String(type).replace(/^<class '(.+)'>$/, '$1');
  };

  const properties = toolData.args_schema || {};

  return (
    <div className="tool-confirmation-modal" onClick={handleModalClick}>
      <div className="tool-confirmation-dialog">
        <div className="tool-confirmation-header">
          <span style={{ fontSize: '24px' }}>🔧</span>
          <h3>工具执行确认</h3>
        </div>
        
        <p><strong>检测到工具:</strong> {toolData.name}</p>
        
        <div className="tool-details">
          <h4>工具描述:</h4>
          <p>{toolData.description || '执行特定任务的工具'}</p>
          
          <h4>参数:</h4>
          <div className="tool-parameters">
            {Object.keys(properties).length === 0 ? (
              <p style={{ color: '#666', fontStyle: 'italic' }}>此工具无需参数</p>
            ) : (
              Object.entries(properties).map(([paramName, paramSchema]) => (
                <div key={paramName} className="tool-param">
                  <label>
                    <div className="param-name">{paramName}</div>
                    <div className="param-info">
                      <span className="param-type">类型: {formatParameterType(paramSchema.type)}</span>
                      {paramSchema.required && <span className="param-required">必需</span>}
                    </div>
                    {paramSchema.description && (
                      <div className="param-description">{paramSchema.description}</div>
                    )}
                  </label>
                  <input
                    type={paramSchema.type === 'number' || paramSchema.type?.includes('int') || paramSchema.type?.includes('float') ? 'number' : 'text'}
                    value={toolArgs[paramName] || ''}
                    onChange={(e) => handleParamChange(paramName, e.target.value)}
                    placeholder={`请输入${paramName}`}
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
