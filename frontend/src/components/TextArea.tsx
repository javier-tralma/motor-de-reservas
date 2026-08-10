import React, { forwardRef } from 'react';

interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  error?: string;
  maxLength?: number;
  currentLength?: number;
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ label, error, maxLength = 500, currentLength = 0, id, className = '', ...props }, ref) => {
    const inputId = id || props.name;

    return (
      <div className="flex flex-col gap-1.5 w-full">
        <div className="flex justify-between items-center">
          <label htmlFor={inputId} className="text-sm font-semibold text-[#1f2a27]">
            {label}
          </label>
          <span className="text-xs text-[#66736e]">
            {currentLength}/{maxLength}
          </span>
        </div>
        <textarea
          ref={ref}
          id={inputId}
          maxLength={maxLength}
          rows={3}
          className={`px-3.5 py-2.5 rounded-lg border bg-[#fffdf9] text-[#1f2a27] text-base placeholder-[#66736e] transition-colors focus:outline-none focus:ring-2 ${
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

TextArea.displayName = 'TextArea';
