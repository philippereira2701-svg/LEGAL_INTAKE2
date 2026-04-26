/**
 * LexBridge intake type system.
 * Defines schema-driven form contracts used by hooks, renderers, validation, and submission.
 */

export type FieldType =
  | "text"
  | "email"
  | "tel"
  | "date"
  | "textarea"
  | "select"
  | "radio"
  | "checkbox"
  | "multi_select";

export interface FieldConditionalRule {
  depends_on: string;
  show_when: string | boolean | number;
}

export interface FieldSchema {
  id: string;
  label: string;
  type: FieldType;
  required?: boolean;
  pii?: boolean;
  options?: string[];
  min_length?: number;
  max_length?: number;
  conditional?: FieldConditionalRule;
}

export interface StepSchema {
  step_id: string;
  title: string;
  fields: FieldSchema[];
}

export interface FormSchemaResponse {
  tenant_id: string;
  form_version: string;
  steps: StepSchema[];
}

export type IntakeFormValues = Record<string, unknown>;
export type FieldVisibilityMap = Record<string, boolean>;

export interface AiScorePreviewResponse {
  tier: "Low" | "Medium" | "High" | "Critical";
}

export interface SubmissionPayload {
  tenant_id: string;
  intake_source: "web_form";
  form_version: string;
  submitted_at: string;
  fields: Record<string, unknown>;
  consent: {
    contact: boolean;
    data_storage: boolean;
  };
  session_id: string;
}
