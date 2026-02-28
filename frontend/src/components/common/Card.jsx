import React from 'react';

const Card = ({ title, children, className = '', headerAction }) => {
  return (
    <div className={`card ${className}`}>
      {title && (
        <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
          {headerAction && <div>{headerAction}</div>}
        </div>
      )}
      {children}
    </div>
  );
};

export default Card;
