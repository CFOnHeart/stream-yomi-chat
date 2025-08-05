import React, { useState } from 'react';
import './ToolMessage.css';

const ToolMessage = ({ content, type }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  const formatParameterType = (typeStr) => {
    if (!typeStr) return '未知';
    // 清理类型字符串，提取主要类型信息
    const cleanType = typeStr.toString().replace(/^<class '|'>$/g, '').replace(/typing\./g, '');
    return cleanType;
  };

  const renderToolResult = () => {
    const { toolName, result, args, description, argsSchema } = content;
    
    return (
      <div className="tool-result-container">
        <div className="tool-header" onClick={toggleExpanded}>
          <span className="tool-icon">✅</span>
          <span className="tool-name">工具执行结果: {result}</span>
          <span className={`expand-arrow`}>
            查看详情 &gt;&gt;
          </span>
        </div>
        
        {isExpanded && (
          <div className="tool-details">
            <div className="tool-section">
              <div className="tool-section-title">🔧 工具名称</div>
              <div className="tool-section-content">{toolName}</div>
            </div>
            
            {args && Object.keys(args).length > 0 && (
              <div className="tool-section">
                <div className="tool-section-title">📥 实际参数</div>
                <div className="tool-params">
                  {Object.entries(args).map(([param, value]) => (
                    <div key={param} className="tool-param">
                      <div className="param-name">{param}</div>
                      <div className="param-value">{String(value)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {description && (
              <div className="tool-section">
                <div className="tool-section-title">📝 工具描述</div>
                <div className="tool-section-content">{description}</div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderToolDetected = () => {
    const { toolName, description, argsSchema } = content;
    
    return (
      <div className="tool-message-container">
        <div className="tool-header" onClick={toggleExpanded}>
          <span className="tool-icon">🔍</span>
          <span className="tool-name">检测到工具: {toolName}</span>
          <span className={`expand-arrow`}>
            查看详情 &gt;&gt;
          </span>
        </div>
        
        {isExpanded && (
          <div className="tool-details">
            {description && (
              <div className="tool-section">
                <div className="tool-section-title">📝 工具描述</div>
                <div className="tool-section-content">{description}</div>
              </div>
            )}
            
            {argsSchema && Object.keys(argsSchema).length > 0 && (
              <div className="tool-section">
                <div className="tool-section-title">⚙️ 参数定义</div>
                <div className="tool-params">
                  {Object.entries(argsSchema).map(([param, schema]) => (
                    <div key={param} className="tool-param">
                      <div className="param-name">{param}</div>
                      <div className="param-info">
                        <span className="param-type">类型: {formatParameterType(schema.type)}</span>
                        {schema.required && <span className="param-required">必需</span>}
                      </div>
                      {schema.description && (
                        <div className="param-description">{schema.description}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  if (typeof content === 'object' && content.type === 'tool_detected') {
    return renderToolDetected();
  } else if (typeof content === 'object' && content.type === 'tool_result') {
    return renderToolResult();
  } else {
    // 兼容旧的字符串格式
    console.log('ToolMessage 收到非标准格式的内容:', content, '类型:', typeof content);
    if (typeof content === 'object') {
      console.log('对象内容详情:', JSON.stringify(content, null, 2));
    }
    return <div className="tool-message-legacy">{String(content)}</div>;
  }
};

export default ToolMessage;
