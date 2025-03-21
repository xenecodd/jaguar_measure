import React from 'react';

const Button = ({ text, onClick, type = 'primary', disabled = false, className = '' }) => {
  const buttonTypes = {
    primary: 'bg-gray-700 text-white hover:bg-gray-600',
    secondary: 'bg-gray-500 text-white hover:bg-gray-400',
    success: 'bg-green-700 text-white hover:bg-green-600',
    danger: 'bg-red-700 text-white hover:bg-red-600',
    outline: 'border border-gray-700 text-gray-700 hover:bg-gray-700 hover:text-white',
    link: 'text-gray-700 bg-transparent hover:underline'
  };

  return (
    <button 
      className={`
        inline-block px-6 py-3 text-base font-medium text-center 
        rounded-lg transition-all duration-200 ease-in-out 
        min-w-[120px] shadow-sm hover:shadow-md 
        focus:outline-none focus:ring-2 focus:ring-offset-2 
        focus:ring-gray-500
        ${buttonTypes[type]}
        ${disabled ? 'opacity-50 cursor-not-allowed pointer-events-none' : ''}
        ${className}
      `}
      onClick={onClick} 
      disabled={disabled}
    >
      {text}
    </button>
  );
};

export default Button;
