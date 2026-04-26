/**
 * Manages per-tenant sessionStorage autosave and draft restoration for intake.
 * Never logs payload contents to avoid PII leaks.
 */

import { useCallback, useMemo } from "react";

import type { IntakeFormValues } from "../types/intake";

export function useIntakeDraft(tenantId: string) {
  const storageKey = useMemo(() => `lexbridge_intake_${tenantId}`, [tenantId]);

  const loadDraft = useCallback((): IntakeFormValues | null => {
    if (!tenantId) return null;
    const raw = sessionStorage.getItem(storageKey);
    if (!raw) return null;

    try {
      return JSON.parse(raw) as IntakeFormValues;
    } catch {
      return null;
    }
  }, [storageKey, tenantId]);

  const saveDraft = useCallback(
    (values: IntakeFormValues) => {
      if (!tenantId) return;
      sessionStorage.setItem(storageKey, JSON.stringify(values));
    },
    [storageKey, tenantId]
  );

  const clearDraft = useCallback(() => {
    if (!tenantId) return;
    sessionStorage.removeItem(storageKey);
  }, [storageKey, tenantId]);

  return {
    storageKey,
    loadDraft,
    saveDraft,
    clearDraft,
  };
}
