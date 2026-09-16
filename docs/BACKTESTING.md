# Backtesting Engine (Fase 2 — ainda não implementado)

## Objetivo
Para cada sinal gerado (real ou em replay), persistir:
`asset, timestamp, entry_price, direction, timeframe, expiry,
technical_features, score, model_probability, result, payout, market_type`.

## Regra inegociável: sem look-ahead bias
Toda função usada para gerar o sinal em backtesting deve ser a **mesma**
função usada em tempo real, recebendo apenas candles até o instante `t`.
É por isso que `app/indicators/technical.py` é puro (sem estado, sem
acesso a "futuro") — pode ser chamado candle a candle no replay com a
garantia matemática de que o resultado é idêntico ao que teria sido
calculado ao vivo.

## Walk-forward (planejado)
```
[ treino ] [ validação ] [ out-of-sample ]
   60%          20%             20%
```
Pesos do Signal Engine só podem ser calibrados na janela de treino/validação;
a métrica de sucesso reportada ao usuário deve vir exclusivamente da janela
out-of-sample.

## Status
Não implementado nesta entrega — depende de schema de persistência
(Postgres/Supabase) ainda não desenhado e de dados reais de candles, que
por sua vez dependem do `QuotexAdapter` validado (ver `QUOTEX_ADAPTER.md`).
