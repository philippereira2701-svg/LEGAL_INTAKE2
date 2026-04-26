/**
 * Renders all visible fields for a single dynamic intake step.
 * Delegates each field to FieldRenderer and keeps layout consistent.
 */

import type { FieldErrors, UseFormRegister } from "react-hook-form";

import type { FieldVisibilityMap, IntakeFormValues, StepSchema } from "../../types/intake";
import { FieldRenderer } from "./FieldRenderer";

interface StepRendererProps {
  step: StepSchema;
  visibilityMap: FieldVisibilityMap;
  register: UseFormRegister<IntakeFormValues>;
  errors: FieldErrors<IntakeFormValues>;
}

export function StepRenderer({ step, visibilityMap, register, errors }: StepRendererProps) {
  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-xl font-semibold text-slate-900">{step.title}</h2>
      </header>
      <div className="space-y-5">
        {step.fields
          .filter((field) => visibilityMap[field.id] ?? true)
          .map((field) => (
            <FieldRenderer key={field.id} field={field} register={register} errors={errors} />
          ))}
      </div>
    </section>
  );
}
