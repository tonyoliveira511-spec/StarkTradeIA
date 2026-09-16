"use client";

import { useState } from "react";
import { SignalPanel, type SignalData } from "@/components/signal/SignalPanel";
import { backendRestPath } from "@/lib/backend-url";

interface ImageSlot {
  file: File;
  timeframe: string;
  previewUrl: string;
}

interface ExtractionResult {
  timeframe_label: string;
  asset: string;
  detected_timeframe: string;
  current_price: string;
  trend: string;
  structure_sequence: string;
  support_zone: string;
  resistance_zone: string;
  momentum: string;
  rsi_reading: string;
  macd_reading: string;
  bollinger_reading: string;
  price_action_pattern: string;
  notes: string;
}

interface EntryInfo {
  zone_low: number;
  zone_high: number;
  confirmation: string;
  invalidation: string;
}

interface AnalyzeResponse {
  direction: "CALL" | "PUT" | "AGUARDAR";
  score: number;
  reasons: string[];
  expiry_suggestion_minutes: number | null;
  expiry_reason: string;
  data_availability: number;
  entry: EntryInfo | null;
  extractions: ExtractionResult[];
}

const SENTINEL = "NAO_DISPONIVEL";
function display(value: string): string {
  return value === SENTINEL ? "não disponível" : value;
}

const MAX_IMAGES = 3;
const SLOT_HINTS = ["contexto", "estrutura", "entrada"];

export default function DashboardPage() {
  const [slots, setSlots] = useState<ImageSlot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  function handleFileSelect(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    const remaining = MAX_IMAGES - slots.length;
    const filesToAdd = Array.from(fileList).slice(0, remaining);
    const newSlots: ImageSlot[] = filesToAdd.map((file, i) => ({
      file,
      // Fluxo rápido: a primeira imagem já vem com "15m" preenchido, já
      // que é o timeframe mais comum para uma leitura de entrada única.
      // Timeframes seguintes (estrutura/entrada) ficam em branco de propósito.
      timeframe: slots.length === 0 && i === 0 ? "15m" : "",
      previewUrl: URL.createObjectURL(file),
    }));
    setSlots((prev) => [...prev, ...newSlots]);
  }

  function updateTimeframe(index: number, timeframe: string) {
    setSlots((prev) => prev.map((s, i) => (i === index ? { ...s, timeframe } : s)));
  }

  function removeSlot(index: number) {
    setSlots((prev) => {
      URL.revokeObjectURL(prev[index].previewUrl);
      return prev.filter((_, i) => i !== index);
    });
  }

  async function handleAnalyze() {
    setError(null);
    if (slots.length === 0) {
      setError("Adicione pelo menos um screenshot.");
      return;
    }
    if (slots.some((s) => !s.timeframe.trim())) {
      setError("Informe o timeframe de cada imagem, por exemplo 15m, 5m ou 1m.");
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const formData = new FormData();
      slots.forEach((s) => {
        formData.append("images", s.file);
        formData.append("timeframes", s.timeframe.trim());
      });

      const response = await fetch(backendRestPath("api/analyze"), {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`Erro ${response.status}: ${text}`);
      }

      setResult(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro desconhecido ao analisar.");
    } finally {
      setLoading(false);
    }
  }

  const signalData: SignalData | null = result
    ? {
        direction: result.direction,
        confidence: result.score,
        entryZoneLow: result.entry?.zone_low,
        entryZoneHigh: result.entry?.zone_high,
        confirmation: result.entry?.confirmation,
        invalidation: result.entry?.invalidation,
        expiryMinutes: result.expiry_suggestion_minutes ?? undefined,
        reasons: [...result.reasons, result.expiry_reason],
      }
    : null;

  return (
    <div className="min-h-screen">
      <header className="border-b border-panelBorder px-6 py-4 flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <h1 className="font-display font-bold text-lg tracking-tight text-paper">
            StarkTrade IA
          </h1>
          <span className="text-xs text-ashDim hidden sm:inline">
            leitura técnica de gráfico por imagem
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-waitDim">
          <span className="w-1.5 h-1.5 rounded-full bg-wait" />
          Somente análise. Sem execução automática.
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10 grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-10">
        <section>
          <h2 className="font-display text-sm font-medium text-paper mb-1">Gráficos</h2>
          <p className="text-xs text-ashDim mb-4 leading-relaxed">
            Envie 1 imagem (15m já preenchido) para uma leitura rápida, ou até
            3 para combinar contexto, estrutura e entrada. As imagens não são
            salvas — existem só durante esta análise.
          </p>

          <div className="space-y-3">
            {slots.map((slot, i) => (
              <div key={i} className="flex gap-3 bg-panel border border-panelBorder rounded-sm p-3">
                <span className="font-data text-xs text-ashDim pt-0.5 w-4">{i + 1}</span>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={slot.previewUrl}
                  alt={`Screenshot ${i + 1}`}
                  className="w-16 h-16 object-cover rounded-sm border border-panelBorder flex-shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <input
                    type="text"
                    placeholder={SLOT_HINTS[i] ?? "timeframe"}
                    value={slot.timeframe}
                    onChange={(e) => updateTimeframe(i, e.target.value)}
                    className="w-full bg-transparent border-b border-panelBorder focus:border-brass outline-none text-sm text-paper py-1 placeholder:text-ashDim transition-colors"
                  />
                  <span className="text-[11px] text-ashDim mt-1 block truncate">
                    {slot.file.name}
                  </span>
                </div>
                <button
                  onClick={() => removeSlot(i)}
                  aria-label={`Remover screenshot ${i + 1}`}
                  className="text-ashDim hover:text-put transition-colors text-sm self-start"
                >
                  ×
                </button>
              </div>
            ))}

            {slots.length < MAX_IMAGES && (
              <label className="flex items-center gap-3 border border-dashed border-panelBorder hover:border-ashDim rounded-sm p-3 cursor-pointer transition-colors group">
                <span className="font-data text-xs text-ashDim w-4">{slots.length + 1}</span>
                <span className="text-sm text-ashDim group-hover:text-ash transition-colors">
                  Adicionar {slots.length === 0 ? "gráfico" : SLOT_HINTS[slots.length] ?? "gráfico"}
                </span>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  multiple
                  className="hidden"
                  onChange={(e) => handleFileSelect(e.target.files)}
                />
              </label>
            )}
          </div>

          <button
            onClick={handleAnalyze}
            disabled={loading || slots.length === 0}
            className="w-full mt-5 rounded-sm bg-brass hover:bg-brassDim disabled:bg-panelBorder disabled:text-ashDim disabled:cursor-not-allowed text-ink font-medium py-2.5 text-sm transition-colors"
          >
            {loading ? "Analisando…" : "Analisar"}
          </button>

          {error && <p className="text-xs text-put mt-3">{error}</p>}
        </section>

        <section>
          {!signalData && (
            <div className="h-full min-h-[420px] border border-dashed border-panelBorder rounded-sm flex flex-col items-center justify-center text-center px-8">
              <p className="font-display text-paper text-lg mb-2">
                Aguardando o primeiro gráfico
              </p>
              <p className="text-sm text-ashDim max-w-sm leading-relaxed">
                Envie um screenshot do gráfico à esquerda. A leitura aparece aqui
                como CALL, PUT ou AGUARDAR — nunca uma direção forçada quando os
                sinais são fracos ou conflitantes.
              </p>
            </div>
          )}

          {signalData && (
            <div className="max-w-md">
              <SignalPanel signal={signalData} />
            </div>
          )}

          {result && result.extractions.length > 0 && (
            <div className="mt-8">
              <div className="flex items-baseline justify-between mb-3">
                <h3 className="font-display text-sm font-medium text-paper">
                  Leitura por timeframe
                </h3>
                <span className="text-xs text-ashDim font-data">
                  {result.data_availability}% dos campos legíveis
                </span>
              </div>

              <div className="space-y-4">
                {result.extractions.map((ex, i) => (
                  <div key={i} className="border-t border-panelBorder pt-3">
                    <div className="text-sm text-paper font-medium mb-2">
                      {ex.timeframe_label}
                      {ex.asset !== SENTINEL && (
                        <span className="text-ashDim font-normal"> · {ex.asset}</span>
                      )}
                    </div>
                    <dl className="grid grid-cols-[120px_1fr] gap-y-1 text-xs">
                      <dt className="text-ashDim">Tendência</dt>
                      <dd className="font-data text-ash">{display(ex.trend)}</dd>
                      <dt className="text-ashDim">Estrutura</dt>
                      <dd className="font-data text-ash">{display(ex.structure_sequence)}</dd>
                      <dt className="text-ashDim">Momentum</dt>
                      <dd className="font-data text-ash">{display(ex.momentum)}</dd>
                      <dt className="text-ashDim">Suporte</dt>
                      <dd className="font-data text-ash">{display(ex.support_zone)}</dd>
                      <dt className="text-ashDim">Resistência</dt>
                      <dd className="font-data text-ash">{display(ex.resistance_zone)}</dd>
                      {ex.notes !== SENTINEL && (
                        <>
                          <dt className="text-ashDim">Notas</dt>
                          <dd className="text-ash">{ex.notes}</dd>
                        </>
                      )}
                    </dl>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
