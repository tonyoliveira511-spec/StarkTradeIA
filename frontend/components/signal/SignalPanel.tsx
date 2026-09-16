"use client";

import clsx from "clsx";

export type Direction = "CALL" | "PUT" | "AGUARDAR";

export interface SignalData {
  direction: Direction;
  confidence: number; // 0-100
  entryZoneLow?: number;
  entryZoneHigh?: number;
  confirmation?: string;
  invalidation?: string;
  expiryMinutes?: number;
  reasons: string[];
}

const DIRECTION_CONFIG: Record<
  Direction,
  { label: string; textClass: string; barClass: string; tintClass: string; glowClass: string }
> = {
  CALL: {
    label: "Comprar",
    textClass: "text-call",
    barClass: "bg-call",
    tintClass: "bg-call/10 border border-call/30",
    glowClass: "shadow-[0_0_40px_-12px_rgba(47,158,104,0.5)]",
  },
  PUT: {
    label: "Vender",
    textClass: "text-put",
    barClass: "bg-put",
    tintClass: "bg-put/10 border border-put/30",
    glowClass: "shadow-[0_0_40px_-12px_rgba(193,68,60,0.5)]",
  },
  AGUARDAR: {
    label: "Sem confluência suficiente",
    textClass: "text-wait",
    barClass: "bg-wait",
    tintClass: "bg-wait/10 border border-wait/30",
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

        {signal.direction !== "AGUARDAR" && signal.entryZoneLow !== undefined && signal.entryZoneHigh !== undefined && (
          <div className={clsx("rounded-sm px-4 py-3 mb-5", config.tintClass)}>
            <span className="text-[11px] uppercase tracking-wide text-ash block mb-1">
              Zona de entrada
            </span>
            <span className="font-data text-xl text-paper block">
              {signal.entryZoneLow === signal.entryZoneHigh
                ? signal.entryZoneLow.toFixed(5)
                : `${signal.entryZoneLow.toFixed(5)} – ${signal.entryZoneHigh.toFixed(5)}`}
            </span>
          </div>
        )}

        {signal.direction !== "AGUARDAR" && signal.expiryMinutes !== undefined && (
          <div className="mb-5">
            <span className="text-xs text-ash block mb-0.5">Expiração sugerida</span>
            <span className="font-data text-sm text-paper">{signal.expiryMinutes} min</span>
          </div>
        )}

        {(signal.confirmation || signal.invalidation) && (
          <div className="grid grid-cols-1 gap-3 mb-5 pt-4 border-t border-panelBorder">
            {signal.confirmation && (
              <div>
                <span className="text-[11px] uppercase tracking-wide text-call block mb-1">
                  Confirmar antes de entrar
                </span>
                <span className="text-sm text-paper leading-relaxed">{signal.confirmation}</span>
              </div>
            )}
            {signal.invalidation && (
              <div>
                <span className="text-[11px] uppercase tracking-wide text-put block mb-1">
                  Invalidado se
                </span>
                <span className="text-sm text-paper leading-relaxed">{signal.invalidation}</span>
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
