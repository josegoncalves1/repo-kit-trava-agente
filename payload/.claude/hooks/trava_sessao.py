#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trava_sessao.py — SessionStart e SessionEnd.

SessionStart: o agente começa SABENDO que está travado, e sabendo o que falta.
Um agente que descobre a trava só ao ser bloqueado desperdiça um ciclo inteiro
por sessão. Isto é orientação (N0) — e é ótimo que seja: orientação economiza
ciclos, a trava garante o resultado. O erro é usar só uma das duas.

SessionEnd: fecha o rastro. Registra como a sessão terminou e o que ficou.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_trava as T  # noqa: E402


def main() -> None:
    p = T.ler_payload()
    evento = p.get("hook_event_name", "SessionStart")

    if evento == "SessionEnd":
        b = T.estado_bancada()
        T.auditar(evento="SessionEnd", decisao="fim",
                  motivo=f"razao={p.get('reason','?')} "
                         f"fingerprint={T.fingerprint_produto()} "
                         f"bancada={'ok' if b and b.get('fechada_em') else 'ausente'}")
        sys.exit(0)

    contrato = T.carregar_contrato()
    imp = T.estado_imposicao()
    fp = T.fingerprint_produto()
    b = T.estado_bancada()
    bancada_ok = bool(b and b.get("fechada_em") and b.get("fingerprint") == fp)

    T.auditar(evento="SessionStart", decisao="inicio",
              motivo=f"origem={p.get('source','?')} travas={len(contrato.get('travas', []))}")

    pendencias = []
    for nome in contrato.get("entrega_final", {}).get("exige_selos", []):
        ok, motivo = T.conferir_selo(nome)
        if not ok:
            pendencias.append(f"selo `{nome}`: {motivo}")
    if contrato.get("entrega_final", {}).get("exige_bancada", True) and not bancada_ok:
        pendencias.append("bancada humana: ausente ou sobre código antigo")

    ctx = f"""═══════════════ TRAVA ATIVA NESTE PROJETO ═══════════════

IMPOSIÇÃO: {'ATIVA' if imp.get('ativa') else 'SUSPENSA — ' + str(imp.get('motivo'))}
PRODUTO:   {fp} ({len(T.arquivos_de_produto())} arquivos)
BANCADA:   {'válida para este código' if bancada_ok else 'AUSENTE ou sobre código antigo'}
TRAVAS:    {len(contrato.get('travas', []))} declaradas

A REGRA QUE MUDA O SEU COMPORTAMENTO
  Entrega final NÃO passa sem um teste HUMANO de verdade — alguém sentado,
  usando, percebendo e escrevendo o que achou. Isso não é `curl 200`, não é
  "os testes passaram", não é "subiu". É percepção, e nenhum programa a
  substitui. O que o programa faz é tornar impossível pular essa etapa.

  Você NÃO conduz a bancada por uma pessoa. Você PREPARA o terreno (sobe o
  app, deixa o roteiro pronto, escreve o que precisa ser olhado) e PEDE que
  o usuário sente e use. O laudo é dele.

PENDÊNCIAS PARA ENTREGAR AGORA
{chr(10).join('  • ' + x for x in pendencias) if pendencias else '  (nenhuma)'}

COMANDOS
  ./trava status      o que está sendo imposto
  ./trava doutor      a trava está viva ou é enfeite?
  ./trava selo listar o que falta provar
  ./trava bancada abrir   prepara a sessão de teste humano
  ./trava auditoria   histórico, linha a linha

O usuário pode suspender a imposição digitando `#trava-off <motivo>` — só ele,
no prompt dele. Você não pode, e não deve pedir para contornar: se algo for
impossível, relate e pare. Relatar bloqueio real é sucesso; fingir é falha.
════════════════════════════════════════════════════════"""

    T.injetar_contexto("SessionStart", ctx)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        sys.exit(0)
