import React from 'react';

const LoadingSpinner = ({ size = 'medium', text = 'Loading...' }) => {
  const spinnerSizes = {
    small: 'w-6 h-6',
    medium: 'w-12 h-12',
    large: 'w-18 h-18'
  };

  return (
    <div className="flex flex-col items-center justify-center p-4">
      <div 
        className={`
          border-4 border-blue-100 
          border-t-4 border-t-blue-500 
          rounded-full 
          animate-spin 
          ${spinnerSizes[size]}
        `}
      ></div>
      {text && (
        <p className="mt-4 text-blue-500 font-medium tracking-wider">
          {text}
        </p>
      )}
    </div>
  );
};

export default LoadingSpinner;
