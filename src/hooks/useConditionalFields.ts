/**
 * Computes dynamic field visibility from schema conditionals and live form values.
 * Returns a map used by renderers and validation to gate conditional fields.
 */

import { useMemo } from "react";

import type { FieldVisibilityMap, IntakeFormValues, StepSchema } from "../types/intake";

export function useConditionalFields(steps: StepSchema[], values: IntakeFormValues): FieldVisibilityMap {
  return useMemo(() => {
    const visibility: FieldVisibilityMap = {};

    steps.forEach((step) => {
      step.fields.forEach((field) => {
        if (!field.conditional) {
          visibility[field.id] = true;
          return;
        }

        const dependencyValue = values[field.conditional.depends_on];
        visibility[field.id] = dependencyValue === field.conditional.show_when;
      });
    });

    return visibility;
  }, [steps, values]);
}
