export interface SemanticPayload {
  service_id: string;
  provider_id: string | null;
  starts_at: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  customer_notes: string;
}

export function generateUUID(): string {
  if (typeof crypto === 'undefined' || typeof crypto.randomUUID !== 'function') {
    throw new Error('crypto.randomUUID is not available in this environment');
  }
  return crypto.randomUUID();
}

export function createNormalizedPayload(raw: SemanticPayload): SemanticPayload {
  return {
    service_id: raw.service_id,
    provider_id: raw.provider_id || null,
    starts_at: raw.starts_at,
    customer_name: raw.customer_name.trim(),
    customer_email: raw.customer_email.trim().toLowerCase(),
    customer_phone: raw.customer_phone.trim(),
    customer_notes: (raw.customer_notes || '').trim(),
  };
}

export function normalizePayload(payload: SemanticPayload): string {
  const norm = createNormalizedPayload(payload);
  return JSON.stringify(norm);
}

export class IdempotencyManager {
  private lastHash: string | null = null;
  private currentKey: string | null = null;

  getIdempotencyKey(payload: SemanticPayload): string {
    const norm = createNormalizedPayload(payload);
    const hash = JSON.stringify(norm);
    if (this.lastHash === hash && this.currentKey) {
      return this.currentKey;
    }
    const newKey = generateUUID();
    this.lastHash = hash;
    this.currentKey = newKey;
    return newKey;
  }

  invalidate(): void {
    this.lastHash = null;
    this.currentKey = null;
  }
}
