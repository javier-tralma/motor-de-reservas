import React, { forwardRef } from 'react';

interface TextFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(
  ({ label, error, id, className = '', ...props }, ref) => {
    const inputId = id || props.name;

    return (
      <div className="flex flex-col gap-1.5 w-full">
        <label htmlFor={inputId} className="text-sm font-semibold text-[#1f2a27]">
          {label}
        </label>
        <input
          ref={ref}
          id={inputId}
          className={`min-h-[44px] px-3.5 py-2.5 rounded-lg border bg-[#fffdf9] text-[#1f2a27] text-base placeholder-[#66736e] transition-colors focus:outline-none focus:ring-2 ${
            error
              ? 'border-[#b33a3a] focus:ring-[#b33a3a]'
              : 'border-[#dfe4df] focus:ring-[#2f7fd3] focus:border-transparent'
          } ${className}`}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : undefined}
          {...props}
        />
        {error && (
          <span id={`${inputId}-error`} className="text-xs text-[#b33a3a] font-medium">
            {error}
          </span>
        )}
      </div>
    );
  }
);

TextField.displayName = 'TextField';
