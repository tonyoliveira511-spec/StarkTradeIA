# Signal Engine

## Como funciona

1. Cada dimensão de análise (trend, market structure, suporte/resistência,
   momentum, RSI, MACD, volatilidade, price action) produz um sub-score de
   `-100` (forte PUT) a `+100` (forte CALL).
2. O `SignalEngine` combina os sub-scores usando pesos configuráveis
   (`Weights`, soma sempre 1.0 — validado em runtime).
3. Se a confiança (`|score ponderado|`) ficar abaixo de
   `min_score_to_trade` (padrão: 60), o resultado é **AGUARDAR** — não é
   um caso de erro, é o comportamento correto quando os indicadores
   discordam.
4. Se a qualidade dos dados (`DataQuality`) não for `EXCELLENT`, o
   resultado é **AGUARDAR** independentemente do score — nunca operar
   sobre dado atrasado ou indisponível.

## Pesos padrão (a calibrar via backtesting — Fase 2/3)

| Fator | Peso |
|---|---|
| Trend | 20% |
| Market Structure | 20% |
| Suporte/Resistência | 15% |
| Momentum | 15% |
| RSI | 10% |
| MACD | 5% |
| Volatilidade | 5% |
| Price Action | 10% |

Estes valores **não são resultado de otimização** — são um ponto de
partida razoável baseado no peso relativo que cada fator normalmente tem
em análise técnica discricionária. Não devem ser apresentados ao usuário
como "os pesos certos" até que o Backtesting Engine (Fase 2) permita
validá-los/recalibrá-los contra dados históricos reais.

## Por que AGUARDAR é um resultado de primeira classe

O enum `Direction` trata `WAIT` (AGUARDAR) exatamente como `CALL`/`PUT` —
não é um caso especial tratado por exceção. Isso é proposital: o maior
risco de um sistema desse tipo é forçar uma direção só porque o usuário
está olhando a tela. Os testes (`tests/test_signal_engine.py`) verificam
explicitamente que indicadores conflitantes e dados de baixa qualidade
resultam em AGUARDAR mesmo quando isso poderia "parecer" um score alto em
um único fator isolado.
