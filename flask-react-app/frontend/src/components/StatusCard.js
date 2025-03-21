import React from 'react';

const StatusCard = ({ title, value, isBoolean = false }) => {
  // For boolean values, convert to Yes/No
  const displayValue = isBoolean ? (value ? 'Yes' : 'No') : value;
  
  // Determine status class for styling
  const statusClass = isBoolean && value 
    ? 'bg-green-50 text-green-600 border-green-300' 
    : 'bg-red-50 text-red-600 border-red-300';
  
  return (
    <div className="bg-gray-50 rounded-lg p-4 shadow-sm hover:shadow-md transition-all duration-300 hover:-translate-y-1">
      <h3 className="text-sm uppercase text-gray-500 mb-2">{title}</h3>
      <div 
        className={`
          inline-block px-3 py-1 rounded-md font-semibold 
          text-base border
          ${isBoolean ? statusClass : 'bg-gray-100 text-gray-800'}
        `}
      >
        {displayValue}
      </div>
    </div>
  );
};

export default StatusCard;
