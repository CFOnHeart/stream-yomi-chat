import React from 'react';
import './StatusIndicator.css';

const StatusIndicator = ({ status }) => {
  return (
    <div className="status-indicator">
      {status}
    </div>
  );
};

export default StatusIndicator;
