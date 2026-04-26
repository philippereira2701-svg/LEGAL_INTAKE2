/**
 * Animated multi-step progress bar for dynamic schema-driven intake.
 * Shows step labels and current completion percentage.
 */

import { motion } from "framer-motion";

import type { StepSchema } from "../../types/intake";

interface ProgressBarProps {
  steps: StepSchema[];
  currentStepIndex: number;
}

export function ProgressBar({ steps, currentStepIndex }: ProgressBarProps) {
  const total = Math.max(steps.length, 1);
  const percentage = ((currentStepIndex + 1) / total) * 100;

  return (
    <div className="space-y-3">
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
        <motion.div
          className="h-full rounded-full bg-blue-600"
          initial={false}
          animate={{ width: `${percentage}%` }}
          transition={{ type: "spring", stiffness: 160, damping: 25 }}
        />
      </div>
      <div className="flex flex-wrap gap-2">
        {steps.map((step, index) => {
          const active = index === currentStepIndex;
          const completed = index < currentStepIndex;
          return (
            <span
              key={step.step_id}
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                active
                  ? "bg-blue-100 text-blue-700"
                  : completed
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-slate-100 text-slate-500"
              }`}
            >
              {step.title}
            </span>
          );
        })}
      </div>
    </div>
  );
}
