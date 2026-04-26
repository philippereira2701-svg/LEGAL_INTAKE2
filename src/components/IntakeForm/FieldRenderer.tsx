/**
 * Renders a single schema-defined field using React Hook Form registration.
 * Supports all required dynamic field types without hardcoded business fields.
 */

import type { FieldErrors, UseFormRegister } from "react-hook-form";

import type { FieldSchema, IntakeFormValues } from "../../types/intake";

interface FieldRendererProps {
  field: FieldSchema;
  register: UseFormRegister<IntakeFormValues>;
  errors: FieldErrors<IntakeFormValues>;
}

const inputBaseClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

export function FieldRenderer({ field, register, errors }: FieldRendererProps) {
  const errorMessage = errors[field.id]?.message as string | undefined;
  const errorId = `${field.id}-error`;

  const commonProps = {
    id: field.id,
    "aria-label": field.label,
    "aria-invalid": Boolean(errorMessage),
    "aria-describedby": errorMessage ? errorId : undefined,
    ...register(field.id),
  };

  return (
    <div className="space-y-2">
      <label htmlFor={field.id} className="block text-sm font-medium text-slate-700">
        {field.label}
      </label>

      {field.type === "textarea" && <textarea {...commonProps} className={`${inputBaseClass} min-h-28`} />}

      {(field.type === "text" || field.type === "email" || field.type === "tel" || field.type === "date") && (
        <input {...commonProps} type={field.type} className={inputBaseClass} />
      )}

      {field.type === "select" && (
        <select {...commonProps} className={inputBaseClass} defaultValue="">
          <option value="" disabled>
            Select an option
          </option>
          {(field.options ?? []).map((option) => (
            <option key={`${field.id}-${option}`} value={option}>
              {option}
            </option>
          ))}
        </select>
      )}

      {field.type === "radio" && (
        <div className="space-y-2">
          {(field.options ?? []).map((option) => (
            <label key={`${field.id}-${option}`} className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
              <input
                type="radio"
                value={option}
                aria-label={`${field.label} - ${option}`}
                className="h-4 w-4 border-slate-300 text-blue-600 focus:ring-blue-500"
                {...register(field.id)}
              />
              <span>{option}</span>
            </label>
          ))}
        </div>
      )}

      {field.type === "checkbox" && (
        <label className="flex cursor-pointer items-start gap-2 text-sm text-slate-700">
          <input
            id={field.id}
            type="checkbox"
            aria-label={field.label}
            className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            {...register(field.id)}
          />
          <span>{field.label}</span>
        </label>
      )}

      {field.type === "multi_select" && (
        <div className="space-y-2">
          {(field.options ?? []).map((option) => (
            <label key={`${field.id}-${option}`} className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                value={option}
                aria-label={`${field.label} - ${option}`}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                {...register(field.id)}
              />
              <span>{option}</span>
            </label>
          ))}
        </div>
      )}

      <p id={errorId} aria-live="polite" className="min-h-5 text-xs text-red-600">
        {errorMessage ?? ""}
      </p>
    </div>
  );
}
