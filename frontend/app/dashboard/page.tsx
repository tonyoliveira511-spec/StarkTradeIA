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

interface AnalyzeResponse {
  direction: "CALL" | "PUT" | "AGUARDAR";
  score: number;
  reasons: string[];
  expiry_suggestion_minutes: number | null;
  expiry_reason: string;
  data_availability: number;
  extractions: ExtractionResult[];
}

const MAX_IMAGES = 3;

export default function DashboardPage() {
  const [slots, setSlots] = useState<ImageSlot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  function handleFileSelect(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    const remaining = MAX_IMAGES - slots.length;
    const filesToAdd = Array.from(fileList).slice(0, remaining);

    const newSlots: ImageSlot[] = filesToAdd.map((file) => ({
      file,
      timeframe: "",
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
      setError("Informe o timeframe de cada imagem (ex: 15m, 5m, 1m).");
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

      const data: AnalyzeResponse = await response.json();
      setResult(data);
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
        expiryMinutes: result.expiry_suggestion_minutes ?? undefined,
        reasons: [...result.reasons, result.expiry_reason],
      }
    : null;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-panelBorder px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-sm font-semibold tracking-wider text-gray-300">
            STARKTRADE IA
          </h1>
          <p className="text-xs text-gray-500">AI Market Intelligence — análise por screenshot</p>
        </div>
        <span className="text-xs px-2 py-1 rounded bg-yellow-900/30 text-yellow-400 border border-yellow-800">
          SOMENTE ANÁLISE — sem execução automática
        </span>
      </header>

      <main className="flex-1 max-w-3xl mx-auto w-full p-6 space-y-6">
        <section className="rounded-lg border border-panelBorder p-4">
          <h2 className="text-sm uppercase text-gray-500 mb-3">
            Screenshots ({slots.length}/{MAX_IMAGES})
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
            {slots.map((slot, i) => (
              <div key={i} className="rounded border border-panelBorder p-2 relative">
                <button
                  onClick={() => removeSlot(i)}
                  className="absolute top-1 right-1 text-xs text-gray-500 hover:text-red-400"
                  aria-label="Remover"
                >
                  ✕
                </button>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={slot.previewUrl}
                  alt="preview"
                  className="w-full h-28 object-cover rounded mb-2"
                />
                <input
                  type="text"
                  placeholder="Timeframe (ex: 15m)"
                  value={slot.timeframe}
                  onChange={(e) => updateTimeframe(i, e.target.value)}
                  className="w-full bg-panel border border-panelBorder rounded px-2 py-1 text-xs text-gray-200"
                />
              </div>
            ))}

            {slots.length < MAX_IMAGES && (
              <label className="rounded border border-dashed border-panelBorder flex flex-col items-center justify-center h-full min-h-[140px] cursor-pointer text-gray-500 hover:text-gray-300 hover:border-gray-500 text-xs text-center p-2">
                <span>+ Adicionar screenshot</span>
                <span className="text-[10px] mt-1">PNG, JPG ou WebP até 8MB</span>
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

          <p className="text-xs text-gray-500 mb-3">
            Envie de 1 a 3 gráficos (ex: 15m para contexto, 5m para estrutura, 1m
            para entrada). As imagens não são armazenadas — existem só durante
            esta análise.
          </p>

          <button
            onClick={handleAnalyze}
            disabled={loading || slots.length === 0}
            className="w-full rounded bg-white text-black font-medium py-2 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? "Analisando..." : "Analisar gráfico(s)"}
          </button>

          {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
        </section>

        {signalData && (
          <section>
            <h2 className="text-sm uppercase text-gray-500 mb-2">Resultado</h2>
            <SignalPanel signal={signalData} />
          </section>
        )}

        {result && result.extractions.length > 0 && (
          <section className="rounded-lg border border-panelBorder p-4">
            <h2 className="text-sm uppercase text-gray-500 mb-3">
              Dados extraídos por timeframe
            </h2>
            <p className="text-xs text-gray-500 mb-3">
              Disponibilidade de dados na imagem: {result.data_availability}%
              {result.data_availability < 60 && (
                <span className="text-yellow-400">
                  {" "}— baixa; a imagem tinha pouca informação legível.
                </span>
              )}
            </p>
            <div className="space-y-3">
              {result.extractions.map((ex, i) => (
                <div key={i} className="text-xs text-gray-400 border-t border-panelBorder pt-2">
                  <div className="text-gray-300 font-medium mb-1">
                    {ex.timeframe_label} {ex.asset !== "NÃO DISPONÍVEL" && `— ${ex.asset}`}
                  </div>
                  <div>Tendência: {ex.trend}</div>
                  <div>Estrutura: {ex.structure_sequence}</div>
                  <div>Momentum: {ex.momentum}</div>
                  <div>Suporte: {ex.support_zone} · Resistência: {ex.resistance_zone}</div>
                  {ex.notes !== "NÃO DISPONÍVEL" && <div>Notas: {ex.notes}</div>}
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
