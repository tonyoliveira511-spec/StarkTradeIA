import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy server-side para o backend FastAPI.
 *
 * A URL real do backend fica em `API_URL` (SEM prefixo NEXT_PUBLIC_), então
 * só existe no servidor Next.js — nunca é embutida no bundle JS enviado ao
 * navegador. O frontend chama sempre `/api/backend/...` (mesma origem),
 * e esta rota repassa a chamada para o backend de verdade.
 *
 * Limitação conhecida: isto cobre requisições HTTP normais (GET/POST).
 * NÃO cobre o WebSocket de candles (`/ws/candles/{asset}`) — funções
 * serverless da Vercel não sustentam proxy de conexão persistente. O
 * WebSocket continua conectando direto no backend a partir do navegador
 * (ver `lib/backend-url.ts`), o que é aceitável porque a URL do backend
 * não é um segredo — é só um endpoint público, sem credenciais embutidas.
 */

function getBackendUrl(): string {
  const url = process.env.API_URL;
  if (!url) {
    throw new Error(
      "API_URL não configurada no servidor. Defina-a nas env vars do " +
        "projeto Vercel (sem prefixo NEXT_PUBLIC_)."
    );
  }
  return url.replace(/\/$/, "");
}

async function proxy(request: NextRequest, path: string[]): Promise<NextResponse> {
  const backendUrl = getBackendUrl();
  const targetPath = path.join("/");
  const search = request.nextUrl.search;
  const targetUrl = `${backendUrl}/${targetPath}${search}`;

  const init: RequestInit = {
    method: request.method,
    headers: {
      "Content-Type": request.headers.get("content-type") ?? "application/json",
    },
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  const backendResponse = await fetch(targetUrl, init);
  const body = await backendResponse.text();

  return new NextResponse(body, {
    status: backendResponse.status,
    headers: {
      "Content-Type": backendResponse.headers.get("content-type") ?? "application/json",
    },
  });
}

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxy(request, params.path);
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxy(request, params.path);
}
