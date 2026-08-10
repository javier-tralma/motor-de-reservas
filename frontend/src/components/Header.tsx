import React from 'react';
import { Link } from 'react-router-dom';

interface HeaderProps {
  businessName?: string;
  businessEmail?: string;
  businessPhone?: string | null;
}

export const Header: React.FC<HeaderProps> = ({
  businessName = 'Estudio Nómada',
  businessEmail = 'hola@estudionomada.cl',
  businessPhone = '+56912345678',
}) => {
  return (
    <header className="w-full bg-[#fffdf9] border-b border-[#dfe4df] py-4 px-4 sm:px-8">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
        <Link
          to="/"
          className="group flex items-center gap-3 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2f7fd3] rounded-lg p-1"
        >
          <div className="w-10 h-10 rounded-full bg-[#176b5b] text-white flex items-center justify-center font-bold text-lg tracking-wider group-hover:bg-[#125548] transition-colors">
            EN
          </div>
          <div className="text-left">
            <span className="block font-bold text-[#1f2a27] text-lg sm:text-xl leading-tight">
              {businessName}
            </span>
            <span className="block text-xs text-[#66736e]">Viña del Mar · Chile</span>
          </div>
        </Link>

        <div className="flex items-center gap-4 text-xs sm:text-sm text-[#66736e]">
          {businessPhone && (
            <a
              href={`tel:${businessPhone}`}
              className="hover:text-[#176b5b] transition-colors min-h-[44px] inline-flex items-center"
            >
              {businessPhone}
            </a>
          )}
          <span>·</span>
          <a
            href={`mailto:${businessEmail}`}
            className="hover:text-[#176b5b] transition-colors min-h-[44px] inline-flex items-center"
          >
            {businessEmail}
          </a>
        </div>
      </div>
    </header>
  );
};
