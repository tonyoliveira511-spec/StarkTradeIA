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

const DIRECTION_CONFIG: Record<
  Direction,
  { label: string; textClass: string; barClass: string; glowClass: string }
> = {
  CALL: {
    label: "Comprar",
    textClass: "text-call",
    barClass: "bg-call",
    glowClass: "shadow-[0_0_40px_-12px_rgba(47,158,104,0.5)]",
  },
  PUT: {
    label: "Vender",
    textClass: "text-put",
    barClass: "bg-put",
    glowClass: "shadow-[0_0_40px_-12px_rgba(193,68,60,0.5)]",
  },
  AGUARDAR: {
    label: "Sem confluência suficiente",
    textClass: "text-wait",
    barClass: "bg-wait",
    glowClass: "shadow-[0_0_40px_-12px_rgba(217,164,65,0.4)]",
  },
};

export function SignalPanel({ signal }: { signal: SignalData }) {
  const config = DIRECTION_CONFIG[signal.direction];

  return (
    <div className={clsx("animate-slip-rise", config.glowClass)}>
      <div className="slip-perforation rounded-t-sm" />
      <div className="bg-panelRaised border-x border-panelBorder px-6 py-6">
        <div className="flex items-baseline justify-between mb-1">
          <span className="text-xs text-ash font-data tracking-wide">
            StarkTrade IA — leitura
          </span>
          <span className="text-xs text-ash font-data">
            {new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>

        <h2 className={clsx("font-display font-bold text-4xl mb-1", config.textClass)}>
          {signal.direction}
        </h2>
        <p className="text-sm text-ash mb-5">{config.label}</p>

        <div className="mb-5">
          <div className="flex items-baseline justify-between mb-1.5">
            <span className="text-xs text-ash">Confiança</span>
            <span className="font-data text-sm text-paper">{signal.confidence.toFixed(0)}/100</span>
          </div>
          <div className="h-1.5 bg-ink rounded-full overflow-hidden">
            <div
              className={clsx("h-full rounded-full animate-gauge-fill", config.barClass)}
              style={{ width: `${Math.min(signal.confidence, 100)}%` }}
            />
          </div>
        </div>

        {signal.direction !== "AGUARDAR" && (
          <div className="grid grid-cols-2 gap-4 mb-5 pt-4 border-t border-panelBorder">
            {signal.entryZoneLow !== undefined && signal.entryZoneHigh !== undefined && (
              <div>
                <span className="text-xs text-ash block mb-0.5">Zona de entrada</span>
                <span className="font-data text-sm text-paper">
                  {signal.entryZoneLow.toFixed(5)}–{signal.entryZoneHigh.toFixed(5)}
                </span>
              </div>
            )}
            {signal.expiryMinutes !== undefined && (
              <div>
                <span className="text-xs text-ash block mb-0.5">Expiração sugerida</span>
                <span className="font-data text-sm text-paper">{signal.expiryMinutes} min</span>
              </div>
            )}
          </div>
        )}

        <ul className="space-y-1.5 pt-4 border-t border-panelBorder">
          {signal.reasons.map((reason, i) => (
            <li key={i} className="text-xs text-ash leading-relaxed pl-3 relative before:content-['—'] before:absolute before:left-0 before:text-ashDim">
              {reason}
            </li>
          ))}
        </ul>
      </div>
      <div className="slip-perforation rounded-b-sm rotate-180" />
    </div>
  );
}
