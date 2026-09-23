#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trava_prompt.py — UserPromptSubmit. Duas funções, ambas essenciais.

(1) O CANAL DO HUMANO.
    Este é o único ponto do runtime onde chega TEXTO DIGITADO PELA PESSOA, antes
    de o modelo ver. O agente não consegue emitir um UserPromptSubmit. Por isso é
    aqui — e só aqui — que se liga e desliga a imposição por prompt:

        #trava-off <motivo com 10+ caracteres>    suspende por 60 min
        #trava-on                                 reativa agora
        #trava-status                             imprime o que está imposto

    Um arquivo de flag qualquer tool call escreveria. Este canal, não.

(2) O CONTRATO VIVO.
    Republica o estado REAL das travas a cada turno, lido do disco. Resolve a
    evaporação de contexto: a regra volta do disco a cada prompt, em vez de
    depender de o modelo ter guardado. É a camada N0 feita direito — não substitui
    a trava, mas economiza os ciclos que o agente gastaria batendo às cegas.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_trava as T  # noqa: E402


def comandos_do_humano(prompt: str) -> None:
    if re.search(r"(^|\s)#trava-on\b", prompt, re.I):
        T.definir_imposicao(True, "reativada pelo humano no prompt", por="humano:prompt")
        T.injetar_contexto("UserPromptSubmit",
            "[TRAVA] IMPOSIÇÃO REATIVADA pelo usuário. A partir de agora nenhuma entrega "
            "passa sem bancada humana válida e sem os selos exigidos.")

    m = re.search(r"(^|\s)#trava-off\s+(.{10,200})", prompt, re.I | re.S)
    if m:
        motivo = m.group(2).strip().splitlines()[0][:200]
        d = T.definir_imposicao(False, motivo, minutos=60, por="humano:prompt")
        T.injetar_contexto("UserPromptSubmit",
            f"[TRAVA] IMPOSIÇÃO SUSPENSA pelo usuário até {T.iso(d['expira_em'])} "
            f"— motivo: {motivo}\n\n"
            "O que continua valendo mesmo com a imposição suspensa:\n"
            "  • a AUTOPROTEÇÃO do cofre (.trava/, hooks, settings) — sempre\n"
            "  • o registro FORENSE de tudo que você tocar — sempre\n"
            "  • a AUDITORIA — sempre\n\n"
            "O que fica suspenso: as travas do contrato e a exigência de bancada.\n"
            "Isto serve para troubleshooting, deploy e investigação. NÃO serve para\n"
            "declarar entrega: a imposição volta sozinha e a entrega continuará "
            "exigindo o teste humano.")

    if re.search(r"(^|\s)#trava-off\b", prompt, re.I) and not m:
        T.injetar_contexto("UserPromptSubmit",
            "[TRAVA] '#trava-off' RECUSADO: exige um motivo com pelo menos 10 caracteres.\n"
            "Exemplo: #trava-off investigando 502 intermitente no gateway\n"
            "O motivo vai para AUDITORIA.md e fica visível. É assim que se percebe, "
            "semanas depois, que o modo de escape virou o modo padrão.")


def main() -> None:
    p = T.ler_payload()
    prompt = str(p.get("prompt", "") or "")

    if "#trava-" in prompt.lower():
        comandos_do_humano(prompt)   # cada ramo termina em injetar_contexto()

    contrato = T.carregar_contrato()
    travas = contrato.get("travas", [])
    imp = T.estado_imposicao()

    linhas = ["## TRAVAS DESTE PROJETO (estado real, lido do disco agora)", ""]

    if not imp.get("ativa"):
        linhas += [f"⚠️ **IMPOSIÇÃO SUSPENSA** até {T.iso(imp.get('expira_em', 0))} — "
                   f"{imp.get('motivo','?')}", "",
                   "Autoproteção, forense e auditoria continuam ativas. As travas do "
                   "contrato e a exigência de bancada estão suspensas. Isto é para "
                   "troubleshooting — **não declare entrega neste modo**.", ""]
    elif not travas:
        linhas += ["⚠️ Os hooks estão ativos, mas o contrato **não declara nenhuma trava**. "
                   "Nada será bloqueado. Avise o usuário: 'instalado' não é 'protegido'. "
                   "Receitas prontas em `docs/04-receitas.md`.", ""]
    else:
        linhas += ["Estas travas são aplicadas pelo runtime via hooks. Elas **não dependem "
                   "de você lembrar delas**: a chamada de ferramenta é cancelada "
                   "mecanicamente. Não tente contorná-las — leia o motivo, que sempre traz "
                   "o comando literal que destrava.", ""]

    for regra in travas:
        q = regra.get("quando", {})
        alvo = ", ".join(q.get("ferramentas", ["*"]))
        linhas.append(f"- **{regra.get('id')}** — `{regra.get('veredito','deny')}` em `{alvo}`"
                      + (f" casando `{q['regex_alvo']}`" if q.get("regex_alvo") else ""))
        for nome in regra.get("exige_selos", []):
            ok, motivo = T.conferir_selo(nome)
            linhas.append(f"    - selo `{nome}`: {'✅ OK' if ok else '🔒 ' + motivo}")
        if regra.get("exige_bancada"):
            b = T.estado_bancada()
            fresca = bool(b and b.get("fechada_em") and
                          b.get("fingerprint") == T.fingerprint_produto())
            linhas.append(f"    - bancada humana: {'✅ válida' if fresca else '🔒 ausente ou sobre código antigo'}")
        for cmd in regra.get("como_destravar", []) or []:
            linhas.append(f"    - destravar: `{cmd}`")

    saida = contrato.get("saida_subagente", {})
    if saida.get("exige_selos"):
        linhas += ["", f"**Saída de sub-agente** exige: {', '.join(saida['exige_selos'])} "
                       f"(máx. {saida.get('max_reentradas', 3)} reentradas)."]

    linhas += ["", "`./trava status` mostra isto a qualquer momento. "
                   "`./trava doutor` diz se a trava está viva ou é enfeite."]

    T.injetar_contexto("UserPromptSubmit", "\n".join(linhas))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        sys.exit(0)   # injetar contexto nunca pode quebrar o turno do usuário
