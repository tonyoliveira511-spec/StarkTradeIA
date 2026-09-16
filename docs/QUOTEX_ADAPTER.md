# QuotexAdapter — decisão, riscos e limitações

## Contexto

Não existe API pública/oficial da Quotex. Todas as bibliotecas disponíveis
(pyquotex e forks) são implementações não-oficiais que se comunicam com o
WebSocket privado usado pelo site, obtido por engenharia reversa.

## Opções avaliadas

| Biblioteca | Observações |
|---|---|
| `cleitonleonel/pyquotex` | Original, mais estrelas/uso, MIT. Login pode exigir Playwright dependendo da versão. Mantida ativamente. |
| `iahmedani/pyquotex` (fork) | Adiciona servidor FastAPI+WS embutido — redundante com nosso próprio backend FastAPI, então não usamos essa parte, só o cliente. |
| `A11ksa/API-Quotex` | Login via Playwright + SSID, foco em "lifecycle de trade" (execução) — descartada como base porque expõe funcionalidades de ordem que não queremos nem importar por engano. |
| `cbtradersbd/pyquotex-unofficial-async-api` | Se apresenta explicitamente como ferramenta para bots de automação de trade/martingale — **descartada**: incompatível com o requisito de somente-leitura deste projeto. |

## Decisão

Usar `cleitonleonel/pyquotex` como referência/base para o cliente de dados
(candles, ativos, payout, preço atual), por ser a mais madura e menos
acoplada a fluxos de execução de ordem.

**Importante**: o `QuotexAdapter` (`backend/app/quotex/quotex_adapter.py`)
**não importa nem expõe** nenhuma função de compra/venda que a biblioteca
eventualmente forneça. Apenas os métodos de leitura de mercado são
encapsulados, e somente esses.

## Riscos assumidos

1. **Quebra sem aviso**: a Quotex pode alterar o protocolo WebSocket ou o
   fluxo de login a qualquer momento, quebrando a biblioteca. Não há SLA.
2. **Bloqueio anti-bot**: login automatizado pode ser identificado por
   proteção Cloudflare, exigindo Playwright/navegador real por trás — mais
   pesado operacionalmente do que um cliente WebSocket puro.
3. **Termos de uso**: automatizar a leitura de dados da própria conta do
   usuário é uma zona cinzenta em relação aos termos de uso da corretora.
   Isso é uma decisão de risco do usuário, documentada aqui para
   transparência — não é uma questão técnica que o código resolve.
4. **Sem garantia de exaustividade de dados históricos**: alguns forks
   limitam a quantidade de candles retornados por chamada; o backtesting
   (Fase 2) precisa paginar respeitando esse limite, não assumir acesso
   irrestrito ao histórico.

## Por que não implementar "fallback" agora

Por pedido explícito: não construir fallback complexo nesta fase. A
interface `MarketDataProvider` já deixa o sistema preparado para receber
um segundo adapter no futuro (outra corretora, ou uma versão mais robusta
do cliente Quotex) sem exigir mudança em nenhum outro módulo.

## Status de implementação

**Atualizado**: `QuotexAdapter` foi reescrito com a API real da biblioteca
`cleitonleonel/pyquotex`, confirmada por introspecção direta da classe
`Quotex` instalada (`inspect.signature`), sem precisar de credenciais —
isso evitou basear a implementação em documentação desatualizada/divergente
entre forks.

Métodos usados e suas assinaturas confirmadas:
- `connect() -> tuple[bool, str]`
- `set_account_mode(balance_mode: str = 'PRACTICE')` — chamado antes de
  `connect()` para nunca operar sobre a conta real por acidente
- `get_all_assets() -> dict[str, str]` — mapeia código do ativo → nome de exibição
- `check_asset_open(asset_name: str) -> tuple[...]` — status aberto/fechado
- `get_payout_by_asset(asset_name: str, timeframe: str) -> float | dict | None`
- `get_candles(asset, end_from_time, offset, period, ...) -> list[dict] | None`
- `get_realtime_price(asset: str) -> list[dict]`
- `start_candles_stream(asset, period)` / `stop_candles_stream(asset)`
- `close() -> bool`

### O que ainda não foi validado contra dados reais

A introspecção confirma que os métodos existem e suas assinaturas, mas
**não confirma o formato exato dos dicionários retornados** (nomes de
campo como `open`/`o`, `high`/`max`/`h`, formato de timestamp) — isso só
pode ser confirmado com uma conexão real. O código em `get_candles()` e
`get_current_price()` tenta múltiplas variações de nome de campo como
tolerância, mas isso precisa ser validado (e simplificado) assim que
houver uma primeira conexão bem-sucedida com dados reais.

`subscribe_candles()` usa polling curto sobre `get_candles()` como ponte
simples, em vez do mecanismo de callback nativo da biblioteca — funcional,
mas não é a forma mais eficiente. Revisar quando o volume de ativos
monitorados simultaneamente crescer.
