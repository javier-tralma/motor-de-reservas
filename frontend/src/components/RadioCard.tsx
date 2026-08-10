import React from 'react';

interface RadioCardProps {
  id: string;
  name: string;
  value: string;
  checked: boolean;
  onChange: () => void;
  title: string;
  description?: string;
  badgeRight?: string;
  subtitleRight?: string;
  disabled?: boolean;
}

export const RadioCard: React.FC<RadioCardProps> = ({
  id,
  name,
  value,
  checked,
  onChange,
  title,
  description,
  badgeRight,
  subtitleRight,
  disabled = false,
}) => {
  return (
    <label
      htmlFor={id}
      className={`relative flex items-start gap-4 p-4 rounded-xl border transition-all cursor-pointer min-h-[44px] ${
        checked
          ? 'bg-[#fffdf9] border-[#176b5b] ring-2 ring-[#176b5b]'
          : 'bg-[#fffdf9] border-[#dfe4df] hover:border-[#66736e]'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <input
        type="radio"
        id={id}
        name={name}
        value={value}
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        className="mt-1 h-5 w-5 text-[#176b5b] border-[#dfe4df] focus:ring-[#2f7fd3]"
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <span className="font-semibold text-[#1f2a27] text-base sm:text-lg">{title}</span>
          {badgeRight && (
            <span className="font-medium text-[#176b5b] text-base">{badgeRight}</span>
          )}
        </div>
        {description && (
          <p className="mt-1 text-sm text-[#66736e] leading-relaxed">{description}</p>
        )}
        {subtitleRight && (
          <span className="mt-1 block text-xs text-[#66736e]">{subtitleRight}</span>
        )}
      </div>
    </label>
  );
};
