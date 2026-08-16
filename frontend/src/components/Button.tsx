import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  isLoading?: boolean;
  fullWidth?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  isLoading = false,
  fullWidth = false,
  disabled,
  className = '',
  ...props
}) => {
  const baseStyle =
    'inline-flex items-center justify-center min-h-[44px] min-w-[44px] px-5 py-2.5 text-base font-medium rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2f7fd3] focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

  const variantStyles = {
    primary: 'bg-[#176b5b] text-white hover:bg-[#125548] active:bg-[#0e443a]',
    secondary: 'bg-[#d98b5f] text-white hover:bg-[#c77a4e]',
    outline: 'border border-[#dfe4df] text-[#1f2a27] bg-[#fffdf9] hover:bg-[#f7f5f0]',
    ghost: 'text-[#1f2a27] hover:bg-[#f0eee9] active:bg-[#e4e1da]',
  };

  return (
    <button
      disabled={disabled || isLoading}
      aria-busy={isLoading ? 'true' : undefined}
      className={`${baseStyle} ${variantStyles[variant]} ${fullWidth ? 'w-full' : ''} ${className}`}
      {...props}
    >
      {isLoading && (
        <svg
          className="animate-spin h-5 w-5 text-current shrink-0 mr-2"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          ></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
      )}
      {children}
    </button>
  );
};
