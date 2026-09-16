"use client";

import clsx from "clsx";

export type Direction = "CALL" | "PUT" | "AGUARDAR";

export interface SignalData {
  direction: Direction;
  confidence: number; // 0-100
  entryZoneLow?: number;
  entryZoneHigh?: number;
  expiryMinutes?: number;
  reasons: string[];
}

const DIRECTION_STYLES: Record<Direction, { bg: string; label: string; dot: string }> = {
  CALL: { bg: "bg-call/10 border-call", label: "text-call", dot: "bg-call" },
  PUT: { bg: "bg-put/10 border-put", label: "text-put", dot: "bg-put" },
  AGUARDAR: { bg: "bg-wait/10 border-wait", label: "text-wait", dot: "bg-wait" },
};

export function SignalPanel({ signal }: { signal: SignalData }) {
  const style = DIRECTION_STYLES[signal.direction];

  return (
    <div className={clsx("rounded-lg border p-4 transition-colors", style.bg)}>
      <div className="flex items-center gap-2 mb-3">
        <span className={clsx("h-2.5 w-2.5 rounded-full", style.dot)} />
        <span className={clsx("text-lg font-semibold tracking-wide", style.label)}>
          {signal.direction === "AGUARDAR" ? "🟡 AGUARDAR" : signal.direction === "CALL" ? "🟢 CALL" : "🔴 PUT"}
        </span>
        <span className="ml-auto text-sm text-gray-400">
          Score: {signal.confidence.toFixed(0)}/100
        </span>
      </div>

      {signal.direction !== "AGUARDAR" && signal.entryZoneLow && signal.entryZoneHigh && (
        <div className="text-sm text-gray-300 mb-1">
          Entrada: {signal.entryZoneLow.toFixed(5)} – {signal.entryZoneHigh.toFixed(5)}
        </div>
      )}
      {signal.direction !== "AGUARDAR" && signal.expiryMinutes && (
        <div className="text-sm text-gray-300 mb-2">
          Expiração recomendada: {signal.expiryMinutes} min
        </div>
      )}

      <ul className="text-xs text-gray-400 space-y-1 mt-2">
        {signal.reasons.map((reason, i) => (
          <li key={i}>• {reason}</li>
        ))}
      </ul>
    </div>
  );
}
