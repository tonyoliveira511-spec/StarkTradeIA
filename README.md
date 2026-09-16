# Quotex AI Analyzer

Plataforma de **análise técnica e estatística de ativos**, com integração
somente-leitura à Quotex. **Não envia, executa, automatiza ou clica em
nenhuma operação.** A execução manual permanece 100% com o usuário, na
própria Quotex.

> ⚠️ Status do projeto: **MVP inicial — Fase 1, esqueleto funcional.**
> A conexão real com a Quotex (`app/quotex/quotex_adapter.py`) está
> marcada como `NotImplementedError` / `TODO — REQUIRES VALIDATION` porque
> depende de testes contra uma conta real, que não podem ser feitos neste
> ambiente. Todo o resto (indicadores, market structure, signal engine,
> testes) já é funcional e testado.

## O que já funciona

- ✅ `MarketDataProvider` — interface que desacopla todo o sistema de
  qualquer corretora específica.
- ✅ Motor de indicadores (EMA, RSI, MACD, Bollinger, ATR) — puro, testado.
- ✅ Market Structure (swing highs/lows, HH/HL/LH/LL, classificação de regime).
- ✅ Signal Engine (pesos configuráveis, estado AGUARDAR como resultado legítimo).
- ✅ API FastAPI com endpoint de health, `/api/assets` e WebSocket de candles
  (ainda sem feed real plugado).
- ✅ Dashboard Next.js com layout de 3 colunas (ativos / gráfico / sinal).
- ✅ Testes unitários dos indicadores e do signal engine (9/9 passando).

## O que falta (por design, não por esquecimento)

- ❌ `QuotexAdapter.connect/get_candles/subscribe_candles/...` — requer
  validação contra uma conta Quotex real. Ver `docs/QUOTEX_ADAPTER.md`.
- ❌ Suporte/Resistência por zonas, Price Action, Expiry Prediction Engine,
  Backtesting, Replay Mode, ML — Fases 2 e 3 do roadmap original.
- ❌ Persistência (migrations/Supabase) — schema ainda não desenhado.

## Rodando localmente

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # preencher os valores
uvicorn app.main:app --reload
```

### Testes
```bash
cd backend
PYTHONPATH=. pytest tests/ -v
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Com Docker Compose (backend + Postgres)
```bash
docker compose up --build
```

## Deploy

- **Frontend**: pronto para Vercel (`vercel.json` incluso). `vercel deploy`
  a partir da pasta `frontend/`, configurando `NEXT_PUBLIC_API_URL` nas
  env vars do projeto Vercel.
- **Backend**: qualquer host que rode um container Python (Railway, Fly.io,
  Render, VM própria). Evite serverless puro para o backend por causa da
  conexão WebSocket persistente com a Quotex.
- **Banco**: Postgres próprio ou Supabase (recomendado para reduzir
  complexidade operacional em fases iniciais).

## Documentação

- [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) — decisões de arquitetura e trade-offs.
- [`QUOTEX_ADAPTER.md`](docs/QUOTEX_ADAPTER.md) — riscos e limitações da integração.
- [`SIGNAL_ENGINE.md`](docs/SIGNAL_ENGINE.md) — como o score é calculado.

## Aviso importante

Ativos binários/digitais (incluindo os operados via Quotex) são produtos de
altíssimo risco. Estatísticas de desempenho histórico geradas por este
sistema **não são garantia de resultado futuro**, especialmente em ativos
OTC, cujo preço é gerado pela própria corretora. Use os sinais como um
insumo a mais na sua análise, nunca como recomendação financeira.
