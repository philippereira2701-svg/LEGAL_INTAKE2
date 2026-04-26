/**
 * LexBridge data use policy single source of truth.
 * Review this file before every deployment.
 */
export const DATA_POLICY = {
  TRAIN_ON_CLIENT_DATA: false,
  RETAIN_AFTER_PURPOSE: false,
  SHARE_WITH_THIRD_PARTIES: false,
  PII_LOGGING_ALLOWED: false,
  AUDIT_LOG_RETENTION_DAYS: 2555,
  PHI_FIELDS: [
    "full_name",
    "phone",
    "email",
    "dob",
    "injury_type",
    "hospital_name",
    "policy_number",
    "incident_description",
  ],
} as const;

export type DataPolicy = typeof DATA_POLICY;
