/**
 * Ponto único de acesso ao backend no frontend.
 *
 * REST: sempre via `/api/backend/...` (rota Next.js, same-origin). A URL
 * real do backend nunca chega ao navegador — fica só em `API_URL` no
 * servidor Next.js (ver app/api/backend/[...path]/route.ts).
 *
 * WebSocket: exceção conhecida. Funções serverless da Vercel não sustentam
 * proxy de conexão persistente, então o navegador conecta direto no
 * backend. Para isso funcionar, `NEXT_PUBLIC_BACKEND_WS_URL` precisa ser
 * pública mesmo — mas ela contém só o host do backend (ex:
 * "wss://starkflow-backend.onrender.com"), nunca uma credencial. Isso é
 * uma URL de serviço, não um segredo.
 */

export function backendRestPath(path: string): string {
  const cleanPath = path.replace(/^\//, "");
  return `/api/backend/${cleanPath}`;
}

export function backendWsUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_BACKEND_WS_URL;
  if (!base) {
    throw new Error(
      "NEXT_PUBLIC_BACKEND_WS_URL não configurada. Defina-a nas env vars " +
        "da Vercel (esta uma É pública de propósito — ver comentário no topo do arquivo)."
    );
  }
  const cleanPath = path.replace(/^\//, "");
  return `${base.replace(/\/$/, "")}/${cleanPath}`;
}
