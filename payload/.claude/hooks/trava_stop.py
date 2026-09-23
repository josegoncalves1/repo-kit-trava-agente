#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trava_stop.py — SubagentStop e Stop. A trava que EXIGE CONCLUSÃO.

Quando o agente considera a tarefa terminada, este hook decide se ele pode
encerrar. Faltando prova, responde {"decision":"block","reason":...} e ele é
OBRIGADO a continuar trabalhando. Elimina a classe inteira de falha
"entreguei pela metade e declarei sucesso".

TRÊS SEGURANÇAS OBRIGATÓRIAS (sem elas isto vira loop infinito):
  1. fusível stop_hook_active   — não empilhar bloqueio sobre bloqueio
  2. contador de reentrada      — cede e ESCALA depois de N tentativas
  3. saída honrosa              — relatar o impedimento também destrava

POLÍTICA DE FALHA: ABERTA. Erro interno aqui NÃO pode prender o agente para
sempre; libera e registra. É o oposto do gate, e é proposital: no gate o risco
é deixar passar; aqui o risco é nunca soltar.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_trava as T  # noqa: E402


def main() -> None:
    p = T.ler_payload()
    evento = p.get("hook_event_name", "SubagentStop")
    sessao = p.get("session_id", "sem-sessao")

    # ── SEGURANÇA 1: fusível. A maior causa de loop infinito é omitir isto.
    if p.get("stop_hook_active"):
        T.auditar(evento=evento, decisao="fusivel", motivo="stop_hook_active=true")
        sys.exit(0)

    if not T.imposicao_ativa():
        T.auditar(evento=evento, decisao="imposicao_suspensa")
        sys.exit(0)

    contrato = T.carregar_contrato()

    papel = T.papel_atual()
    por_papel = (contrato.get("saida_por_papel") or {}).get(papel or "")
    regra = por_papel or contrato.get(
        "saida_subagente" if evento == "SubagentStop" else "saida_principal", {})

    T.auditar(evento=evento, decisao="invocado", papel=papel, tem_regra=bool(regra))
    if not regra:
        sys.exit(0)

    # Teto GLOBAL de rodadas: sem isto executor e fiscal jogam ping-pong.
    teto = int((contrato.get("loop") or {}).get("max_rodadas", 0))
    if teto:
        r = T.incrementar("rodadas_loop")
        if r > teto:
            T.auditar(evento=evento, decisao="loop_estourado", motivo=f"{r} rodadas")
            T.avisar(f"[trava] Loop executor↔fiscal atingiu {r} rodadas (teto {teto}). "
                     "Encerramento liberado SEM as provas. ESCALE PARA O USUÁRIO: o "
                     "ciclo não converge — decida manualmente.")

    faltas: list[tuple[str, str]] = []

    for nome in regra.get("exige_selos", []):
        ok, motivo = T.conferir_selo(nome, estrito=bool(regra.get("estrito")))
        if not ok:
            faltas.append((nome, motivo))

    for spec in regra.get("exige_arquivos", []):
        caminho = T.raiz_projeto() / spec["caminho"]
        minimo = int(spec.get("min_bytes", 1))
        if not caminho.exists():
            faltas.append((spec["caminho"], f"arquivo obrigatório ausente: {spec['caminho']}"))
        elif caminho.stat().st_size < minimo:
            faltas.append((spec["caminho"],
                           f"{spec['caminho']} tem só {caminho.stat().st_size} bytes "
                           f"(mínimo {minimo}) — conteúdo insuficiente"))

    # Bancada humana exigida para encerrar (use só onde faz sentido: entrega).
    if regra.get("exige_bancada"):
        b = T.estado_bancada()
        if not b or not b.get("fechada_em"):
            faltas.append(("bancada",
                "nenhuma sessão de bancada HUMANA foi realizada e fechada. "
                "Isto não é algo que você faça: prepare o terreno e PEÇA ao usuário "
                "que sente, use e escreva o laudo."))
        elif b.get("fingerprint") != T.fingerprint_produto():
            faltas.append(("bancada",
                "a bancada humana é sobre um código ANTIGO — o produto mudou depois "
                "do teste. Uma prova que não aponta para esta versão não prova esta versão."))

    if not faltas:
        T.zerar(f"stop_{sessao}")
        T.auditar(evento=evento, decisao="liberado", motivo="todas as provas presentes")
        sys.exit(0)

    # ── SEGURANÇA 2: contador de reentrada. Cede e escala em vez de prender.
    n = T.incrementar(f"stop_{sessao}")
    maximo = int(regra.get("max_reentradas", 3))
    if n > maximo:
        T.auditar(evento=evento, decisao="cedido",
                  motivo=f"{n} tentativas; faltando={[f[0] for f in faltas]}")
        T.avisar(f"[trava] Encerramento liberado após {n} tentativas sem as provas "
                 f"exigidas. Pendências: {', '.join(nome for nome, _ in faltas)}. "
                 f"Revise manualmente — a entrega NÃO foi verificada.")

    receitas = regra.get("como_destravar", {})
    linhas = [f"TAREFA INCOMPLETA — encerramento bloqueado (tentativa {n} de {maximo}).",
              "", "Pendências detectadas:"]
    linhas += [f"  - {motivo}" for _, motivo in faltas]
    linhas += ["", "Resolva cada pendência:"]
    for nome, _ in faltas:
        linhas.append(f"  {nome}: {receitas.get(nome, 'ver .trava/contrato.json')}")
    linhas += ["",
        # ── SEGURANÇA 3: saída honrosa. Sem isto, impedimento real = prisão.
        regra.get("saida_honrosa",
            "Se alguma pendência for IMPOSSÍVEL de satisfazer, não contorne a trava: "
            "escreva o impedimento em output/relatorio.md (o que tentou, o que falhou, "
            "o erro literal), emita o selo 'relatorio' e então encerre. "
            "Relatar bloqueio real é sucesso; fingir conclusão é falha.")]

    T.auditar(evento=evento, decisao="bloqueado", tentativa=n,
              motivo="; ".join(m for _, m in faltas)[:400])
    T.bloquear_encerramento("\n".join(linhas))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        # FALHA ABERTA — nunca prender o agente por bug do hook.
        T.auditar(evento="Stop", decisao="erro_interno_liberado", motivo=repr(e))
        sys.exit(0)
