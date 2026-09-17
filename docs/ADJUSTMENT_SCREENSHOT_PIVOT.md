# Ajuste de arquitetura — pivô para análise via screenshot

## Decisão

A integração direta com a Quotex (WebSocket não-oficial via `pyquotex`)
foi removida do fluxo principal do MVP. Motivo: instabilidade e
imprevisibilidade de uma API não-oficial como base de um produto — risco
de quebra sem aviso, bloqueio anti-bot, e dependência de uma biblioteca de
terceiros fora do nosso controle.

## Novo fluxo principal

```
Upload de screenshot(s) (1-3, um por timeframe)
    ↓
ImageAnalysisProvider (Vision AI / Claude multimodal)
    ↓
VisionExtraction (dados estruturados, "NÃO DISPONÍVEL" onde não visível)
    ↓
technical_consolidation.build_sub_scores() — combina múltiplos timeframes
    ↓
signal_engine.compute_signal() — MESMO motor de antes, sem alteração
    ↓
CALL / PUT / AGUARDAR + sugestão de expiração (heurística, sem ML ainda)
```

## O que foi reaproveitado sem alteração

- `indicators/technical.py`, `market_structure/structure.py`: intactos,
  não usados no fluxo screenshot ainda (ver "Próximos passos" abaixo),
  mas preservados porque continuam corretos e testados.
- `signal_engine/engine.py`: usado exatamente como antes. Só muda quem
  produz o `SubScores` — antes seria calculado a partir de candles reais,
  agora vem de `technical_consolidation.build_sub_scores()`.
- `MarketDataProvider` (interface): mantida como conceito de abstração de
  fonte de dados, mesmo que o fluxo atual não a implemente diretamente
  (o `ImageAnalysisProvider` cumpre um papel equivalente, mas com uma
  interface diferente, já que "imagem" não é "stream de candles").
- Infraestrutura (Vercel, Render, proxy Next.js): sem mudança nenhuma.

## O que foi removido do fluxo ativo (não deletado do repo)

- `quotex/quotex_adapter.py`: arquivo mantido no repositório, mas não é
  mais importado por `main.py`. Reativar quando a integração em tempo
  real for retomada (ver `docs/QUOTEX_ADAPTER.md`).
- Endpoint `/ws/candles/{asset}` (WebSocket): removido do `main.py`.
- `pyquotex` removido do `requirements.txt` ativo (comentado, com
  instrução de como reativar).

## O que é novo

- `app/ai/vision_analysis.py`: `ImageAnalysisProvider`, chama a API da
  Anthropic (Claude multimodal) com a imagem, extrai JSON estruturado.
  Prompt instrui explicitamente a nunca inventar dado ausente — responde
  `"NÃO DISPONÍVEL"` nesse caso.
- `app/ai/technical_consolidation.py`: converte 1-3 `VisionExtraction`
  (uma por timeframe) em `SubScores`, ponderando por papel do timeframe
  (contexto/estrutura/entrada). Campos ausentes contribuem 0 (neutro).
- `POST /api/analyze`: novo endpoint principal. Recebe imagens via
  multipart, nunca escreve em disco, descarta os bytes após a chamada à
  Vision AI.
- Frontend: dashboard trocado de "lista de ativos + gráfico ao vivo" para
  upload de screenshot(s) com seletor de timeframe por imagem.

## Garantias de não-armazenamento de imagem

- `UploadFile.read()` carrega os bytes em memória.
- Os bytes são usados uma única vez, na chamada a `analyze_screenshot()`.
- Nenhuma linha de código escreve a imagem em disco, Supabase Storage, ou
  qualquer outro armazenamento persistente.
- O histórico (quando implementado — prioridade 10 do briefing) deve
  armazenar apenas os campos estruturados do resultado, nunca a imagem.

## Próximos passos (por prioridade, conforme o briefing)

1. ✅ Upload de imagem funcionando (`POST /api/analyze`)
2. ✅ Vision AI funcionando (`ImageAnalysisProvider`)
3. ✅ Extração estruturada (`VisionExtraction`)
4. ✅ Análise técnica / confluência (`technical_consolidation`)
5. ⏳ Market Structure — a extração já pede a sequência HH/HL/LH/LL à
   Vision AI; falta validar contra screenshots reais se o modelo consegue
   ler isso com precisão suficiente.
6. ⏳ Suporte/resistência — hoje é texto livre (zona como string); ainda
   não há cálculo de distância numérica a partir disso.
7. ✅ Signal Engine (reaproveitado)
8. ✅ Expiry Analysis (heurística simples, sem estatística)
9. ✅ Interface (upload + resultado)
10. ❌ Histórico — não implementado nesta fase (é a menor prioridade do
    briefing); quando implementado, sem persistir imagem.

## Risco a monitorar

A qualidade de todo o pipeline depende inteiramente da capacidade do
modelo Vision de ler os elementos visuais corretamente (velas, indicadores
plotados, zonas de preço). Isso não foi validado contra screenshots reais
da Quotex ainda — validar com casos reais é o próximo passo lógico antes
de confiar no sinal para qualquer decisão.

## Atualização — modelo descontinuado, troca para gemini-3.6-flash

Ao testar em produção, a API retornou 404 informando que `gemini-2.5-flash`
não está mais disponível para contas novas, recomendando `gemini-3.6-flash`
— já aplicado em `VISION_MODEL`. Isso é um lembrete prático: nomes de
modelo de APIs de terceiros mudam com o tempo (risco menor e mais bem
sinalizado do que a fragilidade da Quotex, já que aqui a própria API
informa o substituto no erro, mas ainda exige atenção periódica).

Correção sobre o free tier: diferente do que foi dito inicialmente, o
free tier do Google AI Studio para modelos Flash não tem garantia de
permanência incondicional — é explicitamente descrito pela documentação
mais recente como "rate-limited, para prototipagem", com cotas que podem
mudar a qualquer momento. Continua sendo gratuito e sem cartão de crédito
para o volume de uso esperado nesta fase de validação, mas não deve ser
tratado como uma garantia de custo zero permanente em produção com volume
maior.

Motivo: reduzir custo operacional na fase de validação do MVP. O Google
AI Studio oferece free tier permanente (sem cartão, sem expiração) para o
Gemini 2.5 Flash, incluindo entrada multimodal (imagem) sem custo
adicional, dentro de limites diários generosos (na casa de milhares de
requisições/dia em Setembro de 2026).

Trade-off documentado: no free tier do Google, prompts e respostas podem
ser usados para melhorar os produtos do Google (diferente do uso pago,
que tem garantias mais fortes de privacidade). Para screenshots de gráfico
(sem dado pessoal do usuário) isso é um risco baixo, mas fica registrado
aqui para o caso de o uso mudar no futuro.

Mudança de implementação:
- `app/ai/vision_analysis.py`: usa `google-genai` (`from google import genai`)
  em vez de `anthropic`. Usa `response_schema` estrito (tipo `OBJECT` com
  enum para os campos categóricos) em vez de confiar só no texto do
  prompt para forçar o formato JSON — mais robusto.
- Variável de ambiente: `GEMINI_API_KEY` (gerada em aistudio.google.com/apikey)
  substitui `ANTHROPIC_API_KEY`.
- A interface pública (`ImageAnalysisProvider.analyze_screenshot`) não
  mudou — o resto do sistema (`technical_consolidation.py`, `main.py`)
  não precisou de nenhuma alteração além de trocar o nome da variável de
  configuração.

## Captura de tela ao vivo (getDisplayMedia)

Alternativa ao upload manual: o usuário compartilha a aba/janela da Quotex
via `navigator.mediaDevices.getDisplayMedia` (API padrão do navegador,
mesma usada em compartilhamento de tela de videochamada). O frontend
captura frames periodicamente de um `<video>`/`<canvas>` em memória e
envia para o mesmo endpoint `/api/analyze` — nenhuma credencial da Quotex
é usada, nenhuma engenharia reversa, nenhum frame é persistido em disco.

**Por que isso não esbarra na mesma limitação do QuotexAdapter**: same-
origin policy impede um site de ler o DOM/pixels de outro site
diretamente (ex: via iframe), mas captura de tela é uma permissão que o
próprio usuário concede explicitamente pelo seletor nativo do navegador —
mecanismo diferente, sem tocar em nenhuma API não-oficial da corretora.

**Atenção à cota do Gemini free tier**: captura automática a cada 15-30s
consome chamadas rapidamente. Uma sessão de 1h a cada 30s = 120
chamadas — dentro do limite diário de a maioria dos modelos Flash, mas
várias sessões no mesmo dia podem esgotar a cota (reset à meia-noite
Pacífico). O intervalo padrão é 30s; o usuário pode ajustar para 60s ou
desligar a análise automática e usar "Analisar agora" manualmente.

**Limitações conhecidas**:
- Depende de suporte do navegador a `getDisplayMedia` (funciona em
  Chrome/Edge/Firefox desktop; suporte limitado ou ausente em navegadores
  mobile, especialmente Safari iOS).
- Exige HTTPS (funciona em produção via Vercel; não funciona em
  `http://localhost` sem flags especiais, exceto que a maioria dos
  navegadores trata localhost como contexto seguro).
- Se o usuário parar o compartilhamento pelo controle nativo do
  navegador (não pelo botão "Parar" do StarkTrade), o evento `ended` da
  track é escutado para encerrar o estado corretamente.
