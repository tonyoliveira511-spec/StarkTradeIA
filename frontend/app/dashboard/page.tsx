"use client";

import { useEffect, useRef, useState } from "react";
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
const LIVE_INTERVAL_OPTIONS = [15, 30, 60];

async function analyzeImages(
  images: { file: File | Blob; timeframe: string }[]
): Promise<AnalyzeResponse> {
  const formData = new FormData();
  images.forEach((img) => {
    formData.append("images", img.file, "capture.png");
    formData.append("timeframes", img.timeframe.trim());
  });

  const response = await fetch(backendRestPath("api/analyze"), {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Erro ${response.status}: ${text}`);
  }
  return response.json();
}

export default function DashboardPage() {
  const [slots, setSlots] = useState<ImageSlot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const [isCapturing, setIsCapturing] = useState(false);
  const [liveTimeframe, setLiveTimeframe] = useState("15m");
  const [liveIntervalSec, setLiveIntervalSec] = useState(30);
  const [autoAnalyze, setAutoAnalyze] = useState(true);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => stopCapture();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function startCapture() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { frameRate: 1 },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setIsCapturing(true);

      stream.getVideoTracks()[0].addEventListener("ended", stopCapture);

      if (autoAnalyze) {
        intervalRef.current = setInterval(captureAndAnalyze, liveIntervalSec * 1000);
      }
    } catch (e) {
      setError(
        e instanceof Error && e.name === "NotAllowedError"
          ? "Permissão de captura de tela negada."
          : "Não foi possível iniciar a captura de tela neste navegador."
      );
    }
  }

  function stopCapture() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setIsCapturing(false);
  }

  function captureFrame(): Promise<Blob | null> {
    return new Promise((resolve) => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.videoWidth === 0) {
        resolve(null);
        return;
      }
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        resolve(null);
        return;
      }
      ctx.drawImage(video, 0, 0);
      canvas.toBlob((blob) => resolve(blob), "image/png");
    });
  }

  async function captureAndAnalyze() {
    const blob = await captureFrame();
    if (!blob) return;

    setLoading(true);
    setError(null);
    try {
      const data = await analyzeImages([{ file: blob, timeframe: liveTimeframe }]);
      setResult(data);
      setLastUpdated(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao analisar captura.");
    } finally {
      setLoading(false);
    }
  }

  function restartInterval(newIntervalSec: number) {
    setLiveIntervalSec(newIntervalSec);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = setInterval(captureAndAnalyze, newIntervalSec * 1000);
    }
  }

  function toggleAutoAnalyze(next: boolean) {
    setAutoAnalyze(next);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (next && isCapturing) {
      intervalRef.current = setInterval(captureAndAnalyze, liveIntervalSec * 1000);
    }
  }

  function handleFileSelect(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    const remaining = MAX_IMAGES - slots.length;
    const filesToAdd = Array.from(fileList).slice(0, remaining);
    const newSlots: ImageSlot[] = filesToAdd.map((file, i) => ({
      file,
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
      const data = await analyzeImages(
        slots.map((s) => ({ file: s.file, timeframe: s.timeframe }))
      );
      setResult(data);
      setLastUpdated(new Date());
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
        <section className="space-y-8">
          <div>
            <h2 className="font-display text-sm font-medium text-paper mb-1">
              Captura ao vivo
            </h2>
            <p className="text-xs text-ashDim mb-3 leading-relaxed">
              Compartilhe a aba/janela da Quotex e o StarkTrade lê o gráfico
              periodicamente — sem precisar tirar print manualmente. Nenhum
              frame é salvo; cada captura é analisada e descartada na hora.
            </p>

            {!isCapturing ? (
              <button
                onClick={startCapture}
                className="w-full rounded-sm border border-brass text-brass hover:bg-brass hover:text-ink py-2.5 text-sm font-medium transition-colors"
              >
                Compartilhar tela da Quotex
              </button>
            ) : (
              <div className="border border-panelBorder rounded-sm p-3 space-y-3">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-put opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-put" />
                  </span>
                  <span className="text-xs text-paper">Compartilhando tela</span>
                </div>

                <video ref={videoRef} muted playsInline className="w-full rounded-sm border border-panelBorder" />

                <div className="flex items-center gap-2">
                  <label className="text-xs text-ashDim">Timeframe</label>
                  <input
                    type="text"
                    value={liveTimeframe}
                    onChange={(e) => setLiveTimeframe(e.target.value)}
                    className="w-16 bg-transparent border-b border-panelBorder focus:border-brass outline-none text-sm text-paper py-0.5"
                  />
                </div>

                <label className="flex items-center gap-2 text-xs text-ashDim cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoAnalyze}
                    onChange={(e) => toggleAutoAnalyze(e.target.checked)}
                    className="accent-brass"
                  />
                  Analisar automaticamente a cada
                  <select
                    value={liveIntervalSec}
                    onChange={(e) => restartInterval(Number(e.target.value))}
                    disabled={!autoAnalyze}
                    className="bg-panel border border-panelBorder rounded-sm text-paper text-xs py-0.5 px-1 disabled:opacity-40"
                  >
                    {LIVE_INTERVAL_OPTIONS.map((s) => (
                      <option key={s} value={s}>{s}s</option>
                    ))}
                  </select>
                </label>

                <div className="flex gap-2">
                  <button
                    onClick={captureAndAnalyze}
                    disabled={loading}
                    className="flex-1 rounded-sm bg-brass hover:bg-brassDim disabled:opacity-40 text-ink text-xs font-medium py-2 transition-colors"
                  >
                    {loading ? "Analisando…" : "Analisar agora"}
                  </button>
                  <button
                    onClick={stopCapture}
                    className="flex-1 rounded-sm border border-panelBorder text-ashDim hover:text-put hover:border-put text-xs py-2 transition-colors"
                  >
                    Parar
                  </button>
                </div>

                {lastUpdated && (
                  <p className="text-[11px] text-ashDim">
                    Última leitura: {lastUpdated.toLocaleTimeString("pt-BR")}
                  </p>
                )}
              </div>
            )}
            <canvas ref={canvasRef} className="hidden" />
          </div>

          <div className="border-t border-panelBorder pt-6">
            <h2 className="font-display text-sm font-medium text-paper mb-1">
              Ou envie manualmente
            </h2>
            <p className="text-xs text-ashDim mb-4 leading-relaxed">
              1 imagem (15m já preenchido) para leitura rápida, ou até 3 para
              combinar contexto, estrutura e entrada.
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
              className="w-full mt-4 rounded-sm bg-panelRaised border border-panelBorder hover:border-brass disabled:opacity-40 disabled:cursor-not-allowed text-paper font-medium py-2.5 text-sm transition-colors"
            >
              {loading ? "Analisando…" : "Analisar"}
            </button>
          </div>

          {error && <p className="text-xs text-put">{error}</p>}
        </section>

        <section>
          {!signalData && (
            <div className="h-full min-h-[420px] border border-dashed border-panelBorder rounded-sm flex flex-col items-center justify-center text-center px-8">
              <p className="font-display text-paper text-lg mb-2">
                Aguardando o primeiro gráfico
              </p>
              <p className="text-sm text-ashDim max-w-sm leading-relaxed">
                Compartilhe a tela da Quotex ou envie um screenshot à esquerda.
                A leitura aparece aqui como CALL, PUT ou AGUARDAR — nunca uma
                direção forçada quando os sinais são fracos ou conflitantes.
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
