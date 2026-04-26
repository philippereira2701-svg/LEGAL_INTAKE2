/**
 * Non-blocking case tier preview badge shown after injury assessment step.
 * Never exposes monetary estimates to clients.
 */

import type { AiScorePreviewResponse } from "../../types/intake";

interface AiScoreBadgeProps {
  preview: AiScorePreviewResponse | null;
  loading: boolean;
}

export function AiScoreBadge({ preview, loading }: AiScoreBadgeProps) {
  if (loading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
        Refreshing case tier preview...
      </div>
    );
  }

  if (!preview) return null;

  const tierClass =
    preview.tier === "Critical"
      ? "bg-red-100 text-red-700"
      : preview.tier === "High"
        ? "bg-orange-100 text-orange-700"
        : preview.tier === "Medium"
          ? "bg-amber-100 text-amber-700"
          : "bg-slate-100 text-slate-700";

  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Case Tier Preview</p>
      <div className="mt-2">
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${tierClass}`}>{preview.tier}</span>
      </div>
    </div>
  );
}
