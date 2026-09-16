# Arquitetura

## Visão geral

```
frontend/  (Next.js + TS + Tailwind)  ──HTTP/WS──▶  backend/ (FastAPI)
                                                        │
                                        ┌───────────────┼────────────────┐
                                        ▼               ▼                ▼
                                  quotex/          indicators/      database/
                              (QuotexAdapter)   market_structure/   (Postgres/
                                        │        signal_engine/      Supabase)
                                        ▼        expiry_engine/
                              MarketDataProvider  backtesting/
                                  (interface)         ai/
```

Decisão central: **nenhum módulo além de `app/quotex/` conhece a Quotex**.
Todo o resto depende apenas da interface `MarketDataProvider`. Isso permite:
- trocar de corretora/fonte de dados sem tocar em indicadores/engine;
- testar indicadores, market structure e signal engine com dados sintéticos,
  sem precisar de conexão real (como já fizemos nos testes unitários);
- isolar o ponto de maior fragilidade (integração não-oficial) do resto do
  sistema, que é estável e 100% sob nosso controle.

## Por que não microsserviços / filas / Kubernetes

O volume esperado (um usuário ou poucos, analisando alguns ativos por vez)
não justifica essa complexidade. Um único processo FastAPI com WebSocket
interno dá conta de:
- receber o stream da Quotex;
- calcular indicadores por candle fechado;
- publicar o resultado via WebSocket para o frontend.

Se no futuro houver múltiplos usuários simultâneos com necessidade de
processamento pesado (ex: backtesting de milhares de setups em paralelo),
isso justifica reavaliar (ex: mover o backtesting para um worker separado
com fila simples — não antes disso).

## Banco de dados: Postgres direto vs Supabase

Ambos suportados via `DATABASE_URL` (Postgres direto) ou `SUPABASE_URL` +
`SUPABASE_SERVICE_KEY`. Recomendação: **Supabase** para reduzir operação
(auth pronta se decidir ter múltiplos usuários no futuro, backups
automáticos, painel de administração), a menos que haja motivo concreto
para hospedar Postgres próprio (ex: volume de escrita muito alto do
backtesting, que pode estourar o plano gratuito/inicial do Supabase —
avaliar quando o Backtesting Engine (Fase 2) estiver implementado).

## Hospedagem escolhida: Frontend na Vercel, Backend no Railway

Decisão tomada após a Vercel detectar o backend como função serverless
(framework "fastapi"): serverless não sustenta a conexão WebSocket
persistente que o `QuotexAdapter` precisa manter com a Quotex, nem o
stream contínuo de candles para o frontend. Por isso:

- `stark-flow-front` (Vercel) — serve apenas o Next.js, `rootDirectory=frontend/`.
- `stark-flow-back` (Railway) — processo Python persistente (`uvicorn`),
  `rootDirectory=backend/`, usando o `Dockerfile` já existente em `backend/`.

`NEXT_PUBLIC_API_URL` no projeto Vercel deve apontar para o domínio público
que o Railway gerar para o backend (ex: `https://stark-flow-back.up.railway.app`).

## Frontend na Vercel

O `frontend/` é standalone e não depende de rodar no mesmo host do backend.
`NEXT_PUBLIC_API_URL` aponta para onde o FastAPI estiver hospedado. Não
colocar lógica de negócio (cálculo de indicador, decisão de sinal) no
frontend — ele só exibe o que o backend calculou. Isso evita duplicar (e
divergir) a lógica de decisão em dois lugares.

## Risco conhecido: dependência de biblioteca não-oficial

Ver `QUOTEX_ADAPTER.md`. Este é o único ponto do sistema com risco de
quebra externa fora do nosso controle. Mitigação arquitetural: isolamento
completo atrás de `MarketDataProvider` + testes do resto do sistema com
dados sintéticos, para que uma eventual quebra do adapter nunca derrube a
capacidade de testar/validar o motor de análise.
