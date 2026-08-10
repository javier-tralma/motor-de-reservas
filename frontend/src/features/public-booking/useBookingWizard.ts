import { useReducer, useCallback, useRef } from 'react';
import type { ServicePublic, ProviderPublic } from '../../lib/api/services';
import type { SlotPublic } from '../../lib/api/availability';
import { IdempotencyManager, type SemanticPayload } from '../../lib/idempotency';

export interface CustomerFormData {
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  customer_notes?: string;
}

export interface WizardState {
  step: 1 | 2 | 3 | 4;
  selectedService: ServicePublic | null;
  selectedProvider: ProviderPublic | null; // null means "Cualquier profesional"
  isAnyProvider: boolean;
  selectedDate: string; // YYYY-MM-DD
  selectedSlot: SlotPublic | null;
  customerData: CustomerFormData;
}

type WizardAction =
  | { type: 'SET_STEP'; step: 1 | 2 | 3 | 4 }
  | { type: 'SELECT_SERVICE'; service: ServicePublic }
  | { type: 'SELECT_PROVIDER'; provider: ProviderPublic | null; isAny: boolean }
  | { type: 'SELECT_DATE'; date: string }
  | { type: 'SELECT_SLOT'; slot: SlotPublic | null }
  | { type: 'SET_CUSTOMER_DATA'; data: CustomerFormData }
  | { type: 'CLEAR_SLOT_FOR_CONFLICT' };

function getInitialState(): WizardState {
  return {
    step: 1,
    selectedService: null,
    selectedProvider: null,
    isAnyProvider: true,
    selectedDate: '',
    selectedSlot: null,
    customerData: {
      customer_name: '',
      customer_email: '',
      customer_phone: '',
      customer_notes: '',
    },
  };
}

function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case 'SET_STEP':
      return { ...state, step: action.step };

    case 'SELECT_SERVICE':
      if (state.selectedService?.id === action.service.id) return state;
      return {
        ...state,
        selectedService: action.service,
        selectedProvider: null,
        isAnyProvider: true,
        selectedSlot: null,
      };

    case 'SELECT_PROVIDER':
      if (state.selectedProvider?.id === action.provider?.id && state.isAnyProvider === action.isAny) {
        return state;
      }
      return {
        ...state,
        selectedProvider: action.provider,
        isAnyProvider: action.isAny,
        selectedSlot: null,
      };

    case 'SELECT_DATE':
      if (state.selectedDate === action.date) return state;
      return {
        ...state,
        selectedDate: action.date,
        selectedSlot: null,
      };

    case 'SELECT_SLOT':
      return {
        ...state,
        selectedSlot: action.slot,
      };

    case 'SET_CUSTOMER_DATA':
      return {
        ...state,
        customerData: action.data,
      };

    case 'CLEAR_SLOT_FOR_CONFLICT':
      return {
        ...state,
        selectedSlot: null,
        step: 3,
      };

    default:
      return state;
  }
}

export function useBookingWizard() {
  const [state, dispatch] = useReducer(wizardReducer, undefined, getInitialState);
  const idempotencyManagerRef = useRef<IdempotencyManager>(new IdempotencyManager());

  const setStep = useCallback((step: 1 | 2 | 3 | 4) => {
    dispatch({ type: 'SET_STEP', step });
  }, []);

  const selectService = useCallback((service: ServicePublic) => {
    dispatch({ type: 'SELECT_SERVICE', service });
  }, []);

  const selectProvider = useCallback((provider: ProviderPublic | null, isAny: boolean) => {
    dispatch({ type: 'SELECT_PROVIDER', provider, isAny });
  }, []);

  const selectDate = useCallback((date: string) => {
    dispatch({ type: 'SELECT_DATE', date });
  }, []);

  const selectSlot = useCallback((slot: SlotPublic | null) => {
    dispatch({ type: 'SELECT_SLOT', slot });
  }, []);

  const setCustomerData = useCallback((data: CustomerFormData) => {
    dispatch({ type: 'SET_CUSTOMER_DATA', data });
  }, []);

  const clearSlotForConflict = useCallback(() => {
    idempotencyManagerRef.current.invalidate();
    dispatch({ type: 'CLEAR_SLOT_FOR_CONFLICT' });
  }, []);

  const getClientRequestId = useCallback((payload: SemanticPayload): string => {
    return idempotencyManagerRef.current.getIdempotencyKey(payload);
  }, []);

  return {
    state,
    setStep,
    selectService,
    selectProvider,
    selectDate,
    selectSlot,
    setCustomerData,
    clearSlotForConflict,
    getClientRequestId,
  };
}
