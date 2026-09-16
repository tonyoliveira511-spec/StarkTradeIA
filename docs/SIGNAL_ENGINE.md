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

## Ausência estrutural de dado vs. indicador neutro (correção importante)

Screenshots reais frequentemente não têm RSI/MACD/Bollinger plotados —
isso não é falha de leitura, é a imagem genuinamente não ter essa
informação. O problema descoberto em testes reais (20 imagens, score
máximo observado: 33/100) foi que, sem distinguir "sem dado" de
"indicador neutro (score 0)", esses fatores ausentes diluíam o peso total
sem jamais contribuir — o teto de confiança alcançável ficava
estruturalmente baixo mesmo com confluência forte nos fatores que a
imagem realmente mostrava.

Correção: `build_sub_scores()` agora também retorna `active_factors`
(quais fatores tinham dado de origem disponível), e `compute_signal()`
aceita esse parâmetro para **renormalizar os pesos** entre os fatores
ativos, em vez de simplesmente contar os ausentes como neutros. Testado:
mesmo cenário (screenshot só com candles, sem RSI/MACD/Bollinger) foi de
AGUARDAR (54.4) para PUT (68.0) depois da correção — a confluência real
na imagem não estava sendo refletida corretamente antes.

O score de Suporte/Resistência também foi reescrito: antes dependia de
uma palavra-chave aparecer no campo de notas livre (raramente disparava);
agora usa a distância numérica real entre o preço atual e as zonas de
suporte/resistência extraídas — dado que a Vision AI normalmente
consegue ler mesmo sem indicadores adicionais plotados.

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
