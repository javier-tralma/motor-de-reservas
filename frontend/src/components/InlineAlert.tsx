import React from 'react';

interface InlineAlertProps {
  type?: 'error' | 'warning' | 'info' | 'success';
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const InlineAlert: React.FC<InlineAlertProps> = ({
  type = 'error',
  title,
  message,
  onRetry,
}) => {
  const typeStyles = {
    error: 'bg-[#fffdf9] border-[#b33a3a] text-[#b33a3a]',
    warning: 'bg-[#fffdf9] border-[#9a6416] text-[#9a6416]',
    info: 'bg-[#fffdf9] border-[#176b5b] text-[#176b5b]',
    success: 'bg-[#fffdf9] border-[#247a57] text-[#247a57]',
  };

  return (
    <div
      role="alert"
      className={`p-4 rounded-xl border-l-4 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${typeStyles[type]}`}
    >
      <div className="flex-1">
        {title && <h4 className="font-semibold text-base mb-0.5">{title}</h4>}
        <p className="text-sm leading-relaxed text-[#1f2a27]">{message}</p>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="text-xs font-semibold uppercase tracking-wider underline hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-current rounded px-2 py-1 min-h-[44px]"
        >
          Reintentar
        </button>
      )}
    </div>
  );
};
