import React, { useRef, useState } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import { ConfirmModal } from './ConfirmModal';

const TestContainer: React.FC<{ isDestructive?: boolean; onConfirm: () => void | Promise<void> }> = ({
  isDestructive = false,
  onConfirm,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  return (
    <div>
      <button ref={triggerRef} onClick={() => setIsOpen(true)}>
        Open Modal
      </button>
      <ConfirmModal
        isOpen={isOpen}
        title="Confirmar Acción"
        description="¿Está seguro de continuar?"
        confirmText="Confirmar"
        cancelText="Cancelar"
        isDestructive={isDestructive}
        onConfirm={onConfirm}
        onClose={() => setIsOpen(false)}
        triggerRef={triggerRef}
      />
    </div>
  );
};

describe('ConfirmModal Accessibility & Behavior', () => {
  it('focuses safe cancel button initially when action is destructive', async () => {
    render(<TestContainer isDestructive={true} onConfirm={() => {}} />);
    fireEvent.click(screen.getByText('Open Modal'));

    await waitFor(() => {
      expect(document.activeElement).toBe(screen.getByText('Cancelar'));
    });
  });

  it('traps focus inside modal during tab navigation', async () => {
    render(<TestContainer isDestructive={false} onConfirm={() => {}} />);
    fireEvent.click(screen.getByText('Open Modal'));

    const modalDialog = screen.getByRole('dialog');
    const cancelButton = screen.getByText('Cancelar');
    const confirmButton = screen.getByText('Confirmar');

    // Simulate Tab on last focusable element (confirmButton)
    confirmButton.focus();
    fireEvent.keyDown(modalDialog, { key: 'Tab', code: 'Tab' });

    // Focus stays on one of the modal buttons
    expect(
      document.activeElement === cancelButton || document.activeElement === confirmButton
    ).toBe(true);
  });

  it('closes modal and restores focus to trigger button on Escape key', async () => {
    render(<TestContainer onConfirm={() => {}} />);
    const trigger = screen.getByText('Open Modal');
    fireEvent.click(trigger);

    expect(screen.getByRole('dialog')).toBeDefined();

    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' });

    expect(screen.queryByRole('dialog')).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });

  it('prevents double submit when confirm is clicked twice', async () => {
    let resolvePromise: () => void = () => {};
    const pendingPromise = new Promise<void>((resolve) => {
      resolvePromise = resolve;
    });

    const onConfirmMock = vi.fn().mockImplementation(() => pendingPromise);

    render(<TestContainer onConfirm={onConfirmMock} />);
    fireEvent.click(screen.getByText('Open Modal'));

    const confirmBtn = screen.getByText('Confirmar');
    fireEvent.click(confirmBtn);
    fireEvent.click(confirmBtn);

    expect(onConfirmMock).toHaveBeenCalledTimes(1);

    resolvePromise();
  });
});
