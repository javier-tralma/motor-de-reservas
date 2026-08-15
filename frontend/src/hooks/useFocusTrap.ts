import { useEffect, useRef } from 'react';

export interface UseFocusTrapOptions {
  onEscape?: () => void;
  disableEscape?: boolean;
  initialFocusRef?: React.RefObject<HTMLElement | null>;
  returnFocusRef?: React.RefObject<HTMLElement | null>;
  inertRefs?: React.RefObject<HTMLElement | null>[];
}

const FOCUSABLE_SELECTOR =
  'button:not([disabled]):not([aria-hidden="true"]), ' +
  '[href]:not([aria-hidden="true"]), ' +
  'input:not([disabled]):not([aria-hidden="true"]), ' +
  'select:not([disabled]):not([aria-hidden="true"]), ' +
  'textarea:not([disabled]):not([aria-hidden="true"]), ' +
  '[tabindex]:not([tabindex="-1"]):not([aria-hidden="true"])';

export function useFocusTrap(
  containerRef: React.RefObject<HTMLElement | null>,
  isActive: boolean,
  options: UseFocusTrapOptions = {}
) {
  // Keep options in a ref so keydown handler and cleanup always access the freshest callbacks/refs
  // without causing the main effect to re-run on every render when options are passed inline.
  const optionsRef = useRef(options);
  useEffect(() => {
    optionsRef.current = options;
  });

  const triggerElementRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isActive) return;

    const latestOptions = optionsRef.current;

    // Capture the trigger element currently in focus upon opening
    triggerElementRef.current =
      latestOptions.returnFocusRef?.current || (document.activeElement as HTMLElement | null);

    // Apply inert to background elements once when opening
    const inertElements = latestOptions.inertRefs
      ?.map((ref) => ref.current)
      .filter(Boolean) as HTMLElement[] | undefined;

    if (inertElements && inertElements.length > 0) {
      inertElements.forEach((el) => {
        el.setAttribute('inert', '');
      });
    }

    // Initial focus within container once upon opening
    const container = containerRef.current;
    if (container) {
      if (latestOptions.initialFocusRef?.current) {
        latestOptions.initialFocusRef.current.focus();
      } else {
        const focusables = Array.from(
          container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
        ).filter((el) => !el.hasAttribute('disabled'));

        if (focusables.length > 0) {
          focusables[0].focus();
        } else {
          if (!container.hasAttribute('tabindex')) {
            container.setAttribute('tabindex', '-1');
          }
          container.focus();
        }
      }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      const currentOptions = optionsRef.current;

      if (e.key === 'Escape') {
        if (!currentOptions.disableEscape && currentOptions.onEscape) {
          e.preventDefault();
          currentOptions.onEscape();
        }
        return;
      }

      if (e.key === 'Tab') {
        const currentContainer = containerRef.current;
        if (!currentContainer) return;

        const focusables = Array.from(
          currentContainer.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
        ).filter((el) => !el.hasAttribute('disabled'));

        if (focusables.length === 0) {
          e.preventDefault();
          return;
        }

        const first = focusables[0];
        const last = focusables[focusables.length - 1];

        if (e.shiftKey) {
          if (
            document.activeElement === first ||
            !currentContainer.contains(document.activeElement)
          ) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (
            document.activeElement === last ||
            !currentContainer.contains(document.activeElement)
          ) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);

      // 1. Remove inert from background elements upon closing/unmounting
      if (inertElements && inertElements.length > 0) {
        inertElements.forEach((el) => {
          el.removeAttribute('inert');
        });
      }

      // 2. Restore focus to trigger element upon closing/unmounting
      const trigger =
        optionsRef.current.returnFocusRef?.current || triggerElementRef.current;
      if (trigger && typeof trigger.focus === 'function') {
        trigger.focus();
      }
    };
  }, [isActive, containerRef]);
}
