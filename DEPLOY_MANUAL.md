# Guia de Deploy Manual — StarkTradeIA

Este guia cobre exatamente o que falta: subir este código pro GitHub e
fechar a integração frontend ↔ backend em produção.

---

## 1. Subir o código para o GitHub (`StarkTradeIA`)

Se o repositório já existe e tem código antigo, a forma mais segura é
substituir o conteúdo sem perder o histórico do repo:

```bash
# Extraia este zip em uma pasta, ex: ~/starkflow-src
cd ~/starkflow-src

# Clone o repositório real ao lado
git clone https://github.com/tonyoliveira511-spec/StarkTradeIA.git ~/StarkTradeIA
cd ~/StarkTradeIA

# Apague o conteúdo antigo (exceto .git) e copie o novo
find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
cp -r ~/starkflow-src/* .
cp ~/starkflow-src/.env.example .
cp ~/starkflow-src/.gitignore .

git add .
git commit -m "Estrutura inicial: backend FastAPI, frontend Next.js, proxy API, docs"
git push origin main
```

Se preferir manter o histórico separado por pastas (mais seguro se já
existe algo relevante no repo), copie manualmente `backend/`, `frontend/`,
`docs/`, `.env.example`, `.gitignore`, `README.md`, `docker-compose.yml`
para dentro do clone, revise o que for sobrescrito, e então `git add/commit/push`.

Assim que o push acontecer:
- **Vercel** builda o `frontend/` automaticamente (projeto `stark-flow-front`
  já está linkado a este repo).
- **Render** builda o `backend/` automaticamente (serviço `starkflow-backend`
  já está com auto-deploy ativo).

---

## 2. Configurar os segredos no Render (backend)

Painel Render → serviço `starkflow-backend` → **Environment** → adicionar:

| Variável | Valor |
|---|---|
| `QUOTEX_EMAIL` | seu e-mail da Quotex |
| `QUOTEX_PASSWORD` | sua senha da Quotex |

(`QUOTEX_DEMO_MODE`, `LOG_LEVEL`, `CORS_ORIGINS` já estão configuradas.)

Essas nunca devem ir para a Vercel — o frontend não as usa.

---

## 3. Configurar as variáveis na Vercel (frontend)

Painel Vercel → projeto `stark-flow-front` → **Settings → Environment
Variables**. Adicione (ou confirme que existem, sem o prefixo errado):

| Variável | Valor | Pública? |
|---|---|---|
| `API_URL` | `https://starkflow-backend.onrender.com` | **Não** — sem `NEXT_PUBLIC_` |
| `NEXT_PUBLIC_BACKEND_WS_URL` | `wss://starkflow-backend.onrender.com` | Sim, de propósito (ver `frontend/lib/backend-url.ts`) |

Apague `NEXT_PUBLIC_API_URL` se ainda existir (nome antigo, substituído).

Depois de salvar, force um redeploy (Deployments → ⋯ → Redeploy) — env
vars só valem a partir do próximo build.

---

## 4. Validar a integração ponta a ponta

1. Acesse `https://starkflow-backend.onrender.com/health` — deve responder
   `{"status": "ok", "read_only": true}`. Se o serviço estiver dormindo
   (free tier), a primeira resposta demora ~30-50s.
2. Acesse `https://stark-flow-front.vercel.app/api/backend/health` — deve
   retornar a MESMA resposta, mas vindo através do proxy Next.js. Se isso
   funcionar, o `API_URL` está configurado corretamente no servidor.
3. Acesse `https://stark-flow-front.vercel.app` — deve carregar o
   dashboard (ainda com sinal placeholder "AGUARDAR", já que o
   `QuotexAdapter` real segue pendente de validação — ver
   `docs/QUOTEX_ADAPTER.md`).

---

## 5. Próximo passo real de produto (não de infraestrutura)

Com a infraestrutura fechada, o que falta para o MVP funcionar de verdade
é o item que sempre foi o gargalo: validar `backend/app/quotex/quotex_adapter.py`
contra uma conta Quotex demo sua (instalar `pyquotex`, testar `connect()`,
`get_assets()`, `get_candles()` e preencher os `TODO`s). Sem isso, o
dashboard continua mostrando dados de placeholder, mesmo com toda a
infraestrutura no ar.
