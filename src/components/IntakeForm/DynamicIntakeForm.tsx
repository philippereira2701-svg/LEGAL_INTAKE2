/**
 * Main schema-driven multi-step intake orchestrator.
 * Handles schema fetch, conditional rendering, step validation, autosave/resume, AI tier preview, and final lead submission.
 */

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import axios from "axios";
import { useForm } from "react-hook-form";
import { create } from "zustand";

import { useConditionalFields } from "../../hooks/useConditionalFields";
import { useIntakeDraft } from "../../hooks/useIntakeDraft";
import { useIntakeSchema } from "../../hooks/useIntakeSchema";
import { buildZodSchema } from "../../lib/buildZodSchema";
import type {
  AiScorePreviewResponse,
  FieldSchema,
  IntakeFormValues,
  SubmissionPayload,
} from "../../types/intake";
import { AiScoreBadge } from "./AiScoreBadge";
import { ProgressBar } from "./ProgressBar";
import { StepRenderer } from "./StepRenderer";

interface DynamicIntakeFormProps {
  tenantId?: string;
  token: string;
}

interface ToastState {
  message: string | null;
  setMessage: (message: string | null) => void;
}

const useToastStore = create<ToastState>((set) => ({
  message: null,
  setMessage: (message) => set({ message }),
}));

function decodeJwtTenantId(token: string): string {
  try {
    const payloadSegment = token.split(".")[1];
    const normalized = payloadSegment.replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(window.atob(normalized));
    return payload.tenant_id ?? "";
  } catch {
    return "";
  }
}

function generateSessionId(): string {
  if (crypto?.randomUUID) return crypto.randomUUID();
  return `sess_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

export default function DynamicIntakeForm({ tenantId, token }: DynamicIntakeFormProps) {
  const resolvedTenantId = tenantId || decodeJwtTenantId(token);
  const { message, setMessage } = useToastStore();

  const { data, isLoading, isError } = useIntakeSchema({
    tenantId: resolvedTenantId,
    token,
  });

  const steps = data?.steps ?? [];
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [aiPreview, setAiPreview] = useState<AiScorePreviewResponse | null>(null);
  const [aiPreviewLoading, setAiPreviewLoading] = useState(false);
  const [showResume, setShowResume] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sessionId] = useState(() => generateSessionId());

  const {
    register,
    getValues,
    setValue,
    setError,
    setFocus,
    clearErrors,
    formState: { errors },
  } = useForm<IntakeFormValues>({
    mode: "onBlur",
    defaultValues: {},
  });

  const values = getValues();
  const visibility = useConditionalFields(steps, values);
  const { loadDraft, saveDraft, clearDraft } = useIntakeDraft(resolvedTenantId);

  const piiFieldMap = useMemo(() => {
    const map: Record<string, boolean> = {};
    steps.forEach((step) => {
      step.fields.forEach((field) => {
        map[field.id] = Boolean(field.pii);
      });
    });
    return map;
  }, [steps]);

  useEffect(() => {
    if (!steps.length) return;
    const draft = loadDraft();
    if (draft && Object.keys(draft).length > 0) {
      setShowResume(true);
    }
  }, [steps, loadDraft]);

  const applyDraft = () => {
    const draft = loadDraft();
    if (!draft) return;
    Object.entries(draft).forEach(([fieldId, fieldValue]) => {
      setValue(fieldId, fieldValue);
    });
    setShowResume(false);
  };

  const dismissDraft = () => {
    clearDraft();
    setShowResume(false);
  };

  const currentStep = steps[currentStepIndex];

  const validateCurrentStep = () => {
    if (!currentStep) return false;
    clearErrors();
    const stepValues = getValues();
    const visibleFields = currentStep.fields.filter((field) => visibility[field.id] ?? true);

    try {
      buildZodSchema(visibleFields, visibility, stepValues);
      return true;
    } catch (error: any) {
      const issues = error?.issues ?? [];
      issues.forEach((issue: any) => {
        const fieldName = issue.path?.[0];
        if (fieldName) {
          setError(fieldName, { type: "manual", message: issue.message });
        }
      });
      if (issues.length > 0) {
        setFocus(issues[0].path[0]);
      }
      return false;
    }
  };

  const saveStepDraftWithoutPii = () => {
    const allValues = getValues();
    const safeValues: IntakeFormValues = {};
    Object.entries(allValues).forEach(([fieldId, fieldValue]) => {
      if (!piiFieldMap[fieldId]) {
        safeValues[fieldId] = fieldValue;
      }
    });
    saveDraft(safeValues);
  };

  const requestAiPreview = async () => {
    setAiPreviewLoading(true);
    try {
      const response = await axios.post<AiScorePreviewResponse>(
        "/api/v1/intake/score-preview",
        { fields: getValues() },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      setAiPreview(response.data);
    } catch {
      setMessage("Could not refresh case tier preview right now.");
    } finally {
      setAiPreviewLoading(false);
    }
  };

  const nextStep = async () => {
    if (!validateCurrentStep()) return;
    saveStepDraftWithoutPii();

    if (currentStepIndex === 2) {
      void requestAiPreview();
    }

    if (currentStepIndex < steps.length - 1) {
      setCurrentStepIndex((prev) => prev + 1);
    }
  };

  const previousStep = () => {
    setCurrentStepIndex((prev) => Math.max(0, prev - 1));
  };

  const sanitizeSubmissionFields = (allValues: IntakeFormValues) => {
    const fields: Record<string, unknown> = {};
    steps.forEach((step) => {
      step.fields.forEach((field: FieldSchema) => {
        if (visibility[field.id] ?? true) {
          fields[field.id] = allValues[field.id];
        }
      });
    });
    return fields;
  };

  const submit = async () => {
    if (!validateCurrentStep() || !data) return;
    setIsSubmitting(true);
    setMessage(null);
    try {
      const allValues = getValues();
      const payload: SubmissionPayload = {
        tenant_id: resolvedTenantId,
        intake_source: "web_form",
        form_version: data.form_version,
        submitted_at: new Date().toISOString(),
        fields: sanitizeSubmissionFields(allValues),
        consent: {
          contact: Boolean(allValues.consent_contact),
          data_storage: Boolean(allValues.consent_data),
        },
        session_id: sessionId,
      };

      await axios.post("/api/v1/intake/leads", payload, {
        headers: { Authorization: `Bearer ${token}` },
      });

      clearDraft();
      setMessage("Your intake has been submitted successfully.");
    } catch {
      setMessage("Submission failed. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-600">Loading intake form...</div>;
  }

  if (isError || !data || !currentStep) {
    return <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">Could not load intake schema.</div>;
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      {message && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">{message}</div>
      )}

      {showResume && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
          <p className="text-sm text-amber-900">Resume your application from a saved draft.</p>
          <div className="flex items-center gap-2">
            <button type="button" onClick={applyDraft} className="rounded-md bg-amber-600 px-3 py-2 text-xs font-medium text-white">
              Resume
            </button>
            <button type="button" onClick={dismissDraft} className="rounded-md border border-amber-300 bg-white px-3 py-2 text-xs font-medium text-amber-800">
              Dismiss
            </button>
          </div>
        </div>
      )}

      <ProgressBar steps={steps} currentStepIndex={currentStepIndex} />
      <AiScoreBadge preview={aiPreview} loading={aiPreviewLoading} />

      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep.step_id}
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -30 }}
          transition={{ duration: 0.25 }}
        >
          <StepRenderer step={currentStep} visibilityMap={visibility} register={register} errors={errors} />
        </motion.div>
      </AnimatePresence>

      <div className="flex items-center justify-between pt-2">
        <button
          type="button"
          onClick={previousStep}
          disabled={currentStepIndex === 0 || isSubmitting}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Back
        </button>

        {currentStepIndex < steps.length - 1 ? (
          <button
            type="button"
            onClick={nextStep}
            disabled={isSubmitting}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Continue
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={isSubmitting}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Submitting...
              </>
            ) : (
              "Submit intake"
            )}
          </button>
        )}
      </div>
    </div>
  );
}
