# Expiry Prediction Engine (Fase 2 — ainda não implementado)

## Objetivo
Para um setup identificado pelo Signal Engine, estimar, para cada horizonte
(3/5/10/15/20/30 min), a proporção histórica de vezes em que
`close(expiry)` ficou do lado correto do preço de entrada, **usando apenas
setups estatisticamente semelhantes já ocorridos no passado** (walk-forward,
sem look-ahead bias).

## Por que isso ainda não está implementado
Depende do Backtesting Engine (armazenar setup + resultado real) ter
amostra suficiente. Implementar o cálculo de probabilidade antes de ter
dados históricos reais geraria números fabricados — o próprio briefing
original exige mostrar "Insufficient historical data" nesse caso, e é
exatamente essa a postura adotada aqui: nada é implementado como
placeholder fingindo maturidade estatística que não existe ainda.

## Alerta estatístico importante
Ativos OTC da Quotex têm preço sintético gerado pela corretora fora do
horário de mercado real. Estatísticas de "win rate por horizonte" nesses
ativos medem o comportamento do gerador de preço da corretora, não um
mercado real — por isso o sistema mantém `market_type` (REAL/OTC)
segregado em todas as camadas (ver `MarketDataProvider`), inclusive nas
estatísticas de backtesting.

## Próximos passos (quando Fase 2 começar)
1. Implementar Backtesting Engine armazenando setup completo + resultado.
2. Agrupar setups por similaridade (score, regime, ativo, market_type).
3. Calcular taxa de acerto por horizonte com validação walk-forward
   (treino/validação/out-of-sample), nunca com o dataset completo de uma vez.
4. Só então expor os percentuais no `ExpiryPanel` do frontend.
