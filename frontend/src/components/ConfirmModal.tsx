import React, { useEffect, useRef } from 'react';

export interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmText: string;
  cancelText?: string;
  isDestructive?: boolean;
  isLoading?: boolean;
  onConfirm: () => void | Promise<unknown>;

  onClose: () => void;
  triggerRef?: React.RefObject<HTMLElement | null>;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  title,
  description,
  confirmText,
  cancelText = 'Volver',
  isDestructive = false,
  isLoading = false,
  onConfirm,
  onClose,
  triggerRef,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  const confirmButtonRef = useRef<HTMLButtonElement>(null);
  const activeTriggerRef = useRef<HTMLElement | null>(null);
  const isSubmittingRef = useRef(false);

  // Store trigger element when opening
  useEffect(() => {
    if (isOpen) {
      activeTriggerRef.current = triggerRef?.current || (document.activeElement as HTMLElement | null);
      isSubmittingRef.current = false;
    }
  }, [isOpen, triggerRef]);

  // Handle Focus Trap and Safe Initial Focus
  useEffect(() => {
    if (!isOpen) return;

    // Initial Focus: For destructive actions, focus safe cancel button first.
    const focusTimer = setTimeout(() => {
      if (isDestructive && cancelButtonRef.current) {
        cancelButtonRef.current.focus();
      } else if (confirmButtonRef.current) {
        confirmButtonRef.current.focus();
      } else if (cancelButtonRef.current) {
        cancelButtonRef.current.focus();
      }
    }, 10);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === 'Tab') {
        if (!modalRef.current) return;
        const focusables = modalRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusables.length === 0) return;

        const first = focusables[0];
        const last = focusables[focusables.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      clearTimeout(focusTimer);
      document.removeEventListener('keydown', handleKeyDown);
      // Restore focus on close
      if (activeTriggerRef.current) {
        activeTriggerRef.current.focus();
      }
    };
  }, [isOpen, isDestructive, onClose]);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    if (isSubmittingRef.current || isLoading) return;
    isSubmittingRef.current = true;
    try {
      await onConfirm();
    } finally {
      isSubmittingRef.current = false;
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isLoading) {
          onClose();
        }
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        aria-describedby="modal-description"
        className="w-full max-w-md p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl space-y-6 text-left"
      >
        <div>
          <h3 id="modal-title" className="text-xl font-bold text-white">
            {title}
          </h3>
          <p id="modal-description" className="text-sm text-slate-300 mt-2 leading-relaxed">
            {description}
          </p>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            ref={cancelButtonRef}
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2.5 rounded-xl text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-500 disabled:opacity-50 transition-colors"
          >
            {cancelText}
          </button>
          <button
            ref={confirmButtonRef}
            type="button"
            onClick={handleConfirm}
            disabled={isLoading}
            className={`px-4 py-2.5 rounded-xl text-sm font-semibold text-white focus:outline-none focus:ring-2 disabled:opacity-50 transition-colors flex items-center gap-2 ${
              isDestructive
                ? 'bg-rose-600 hover:bg-rose-700 focus:ring-rose-500'
                : 'bg-emerald-600 hover:bg-emerald-700 focus:ring-emerald-500'
            }`}
          >
            {isLoading ? (
              <>
                <svg className="w-4 h-4 animate-spin text-white" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                <span>Procesando...</span>
              </>
            ) : (
              confirmText
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
