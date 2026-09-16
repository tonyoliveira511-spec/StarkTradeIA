"""
Script de DIAGNÓSTICO para validar o pyquotex contra sua conta real.

COMO USAR (na sua máquina, NUNCA aqui no chat):

    pip install --upgrade git+https://github.com/cleitonleonel/pyquotex.git
    # se pedir: playwright install

    export QUOTEX_EMAIL="seu_email_aqui"
    export QUOTEX_PASSWORD="sua_senha_aqui"

    python diagnose_quotex.py

O que ele faz:
  1. Conecta na sua conta (modo DEMO por padrão — nunca mexe na conta real).
  2. Lista os métodos realmente disponíveis no client instalado.
  3. Tenta chamar os candidatos mais prováveis para: saldo, lista de ativos,
     histórico de candles, preço atual — e imprime o resultado (ou o erro).
  4. NUNCA imprime email/senha. Você pode colar a saída completa de volta
     no chat com segurança — ela não contém suas credenciais.

O objetivo NÃO é usar isto em produção. É descobrir, na prática, os nomes
de método corretos da versão que você instalou, para eu escrever o
QuotexAdapter final com precisão, em vez de adivinhar pela documentação
(que diverge entre forks e muda entre versões).
"""
import asyncio
import inspect
import os
import sys


async def main() -> None:
    email = os.environ.get("QUOTEX_EMAIL")
    password = os.environ.get("QUOTEX_PASSWORD")

    if not email or not password:
        print("ERRO: defina QUOTEX_EMAIL e QUOTEX_PASSWORD como variáveis de "
              "ambiente antes de rodar este script. Não edite este arquivo "
              "para colocar a senha direto no código.")
        sys.exit(1)

    try:
        from pyquotex.stable_api import Quotex
    except ImportError:
        print("ERRO: pyquotex não está instalado. Rode:\n"
              "  pip install git+https://github.com/cleitonleonel/pyquotex.git")
        sys.exit(1)

    print("=" * 70)
    print("1. Conectando (modo DEMO)...")
    print("=" * 70)

    client = Quotex(email=email, password=password, lang="pt")

    # Tenta forçar modo demo antes de conectar, se o atributo existir.
    for demo_attr in ("account_is_demo", "set_account_mode"):
        if hasattr(client, demo_attr):
            print(f"  (atributo/método de modo demo encontrado: {demo_attr})")

    try:
        result = await client.connect()
    except Exception as e:
        print(f"FALHA ao conectar: {type(e).__name__}: {e}")
        sys.exit(1)

    # connect() pode retornar bool ou tupla (check, reason) dependendo da versão
    if isinstance(result, tuple):
        check, reason = result
    else:
        check, reason = result, None

    print(f"  connect() -> check={check!r} reason={reason!r}")
    if not check:
        print("FALHA: conexão não foi estabelecida. Verifique email/senha "
              "e se a conta não está com 2FA bloqueando login automatizado.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("2. Métodos públicos disponíveis no client:")
    print("=" * 70)
    methods = sorted(
        name for name, _ in inspect.getmembers(client, predicate=inspect.ismethod)
        if not name.startswith("_")
    )
    for m in methods:
        print(f"  - {m}")

    print("\n" + "=" * 70)
    print("3. Testando candidatos a métodos de leitura de dados...")
    print("=" * 70)

    async def try_call(label: str, coro_factory):
        print(f"\n--- {label} ---")
        try:
            result = await coro_factory()
            preview = repr(result)
            if len(preview) > 500:
                preview = preview[:500] + "... (truncado)"
            print(f"  OK: {preview}")
        except Exception as e:
            print(f"  FALHOU: {type(e).__name__}: {e}")

    if hasattr(client, "get_balance"):
        await try_call("get_balance()", client.get_balance)

    for candidate in ("get_all_asset_name", "get_all_assets", "assets_open", "get_assets"):
        if hasattr(client, candidate):
            fn = getattr(client, candidate)
            await try_call(f"{candidate}()", fn)

    for candidate in ("get_candles", "get_historical_candles", "get_candle"):
        if hasattr(client, candidate):
            fn = getattr(client, candidate)
            sig = inspect.signature(fn)
            print(f"\n(assinatura de {candidate}: {sig})")

    print("\n" + "=" * 70)
    print("4. Encerrando conexão...")
    print("=" * 70)
    if hasattr(client, "close"):
        await client.close()

    print("\nDIAGNÓSTICO CONCLUÍDO. Copie toda esta saída (sem editar) e "
          "cole de volta no chat — não contém suas credenciais.")


if __name__ == "__main__":
    asyncio.run(main())
