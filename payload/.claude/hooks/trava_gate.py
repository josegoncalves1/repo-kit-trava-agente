#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trava_gate.py — PreToolUse. A trava que IMPEDE a ferramenta de rodar.

Ordem de avaliação (importa, e é deliberada):

  0. HEARTBEAT      registra que o hook rodou — distingue "não bloqueou" de "nem rodou"
  1. AUTOPROTEÇÃO   ninguém escreve no cofre .trava/ nem nos hooks     ← sempre, mesmo suspensa
  2. FORENSE        guarda a imagem-anterior de todo arquivo tocado    ← sempre
  3. IMPOSIÇÃO      se suspensa, só 0/1/2 valem; o resto passa
  4. PAPEL          fiscal não escreve produto; executor não escreve o laudo que o julga
  5. CONTRATO       as travas declaradas em .trava/contrato.json

POLÍTICA DE FALHA: FECHADA. Exceção interna NEGA a chamada. Trava de segurança
que falha aberta não é trava.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_trava as T  # noqa: E402

# ── 1. O COFRE. Escrita aqui é sempre negada, em qualquer modo, sempre.
#
# Sem isto, todo o resto é teatro: bastaria o agente reescrever o próprio hook,
# o contrato ou um selo. A regex cobre a superfície `command` do Bash — filtrar
# só `file_path` é o furo clássico (`echo x > .trava/selos/x.json` passa).
COFRE = re.compile(
    r"(^|[^\w./-])\.trava(/|$)|/\.trava/|chave\.secreta|"
    r"\.claude/hooks/|\.claude/settings(\.local)?\.json|"
    r"\.claude/(agents|commands|skills)/",
    re.IGNORECASE)
ESCRITA_BASH = re.compile(
    r">|>>|\btee\b|\bsed\s+-i\b|\brm\b|\bmv\b|\bcp\b|\binstall\b|\btruncate\b|"
    r"\bdd\b|\bchmod\b|\bchown\b|\bln\b|\btouch\b|\bmkdir\b|"
    r"\bpython[0-9.]*\s+-c\b|\bperl\b|\bnode\s+-e\b|\bgit\s+(checkout|restore|clean|stash)\b",
    re.IGNORECASE)
LEITURA_BASH = re.compile(
    r"^\s*(cat|bat|less|more|head|tail|jq|ls|ll|stat|file|wc|grep|rg|find|awk|"
    r"sed\s+-n|sha256sum|md5sum|diff|tree|column)(\s|$)", re.IGNORECASE)


def protege_cofre(tool_name: str, tool_input: dict, alvo: str) -> None:
    if not COFRE.search(alvo or ""):
        return
    # Leitura é permitida: trava que impede inspeção faz o agente trabalhar às
    # cegas e gastar ciclos. Negue a escrita, libere a leitura.
    if tool_name in ("Read", "Glob", "Grep"):
        if "chave.secreta" not in (alvo or ""):
            return
    if tool_name == "Bash":
        cmd = str(tool_input.get("command", ""))
        if LEITURA_BASH.search(cmd) and not ESCRITA_BASH.search(cmd) \
                and "chave.secreta" not in cmd:
            return
    T.auditar(evento="PreToolUse", decisao="deny", trava="autoprotecao",
              ferramenta=tool_name, motivo="tentativa de escrita no cofre",
              alvo=(alvo or "")[:200])
    T.negar(
        "BLOQUEADO pela AUTOPROTEÇÃO da trava.\n\n"
        f"Ferramenta: {tool_name}\nAlvo: {(alvo or '')[:200]}\n\n"
        "O cofre .trava/, os hooks em .claude/hooks/, o settings.json e as definições\n"
        "de agentes/comandos/skills são gravados pelo INSTALADOR e pelo HUMANO — nunca\n"
        "pelo agente. Isto não é preferência de estilo: é o que faz a prova valer.\n"
        "Se você pudesse reescrever a trava, ela não travaria nada.\n\n"
        "LEITURA é permitida. ESCRITA não.\n\n"
        "  ver o que está imposto ....... ./trava status\n"
        "  ver o que falta .............. ./trava selo listar\n"
        "  ver o histórico .............. ./trava auditoria\n\n"
        "Se a trava parecer ERRADA, diga isso ao usuário e pare. Não a conserte por\n"
        "conta própria: mudar a trava é trabalho do humano, em commit separado."
    )


def regra_casa(regra: dict, tool_name: str, alvo: str, modo: str) -> bool:
    q = regra.get("quando", {})
    ferramentas = q.get("ferramentas")
    if ferramentas and tool_name not in ferramentas:
        return False
    # Regex inválido no contrato NÃO pode derrubar a sessão: uma vírgula errada
    # bloquearia toda ferramenta. Regra inavaliável é pulada, e gritada no log.
    padrao = q.get("regex_alvo")
    if padrao:
        try:
            if not re.search(padrao, alvo or "", re.IGNORECASE):
                return False
        except re.error as e:
            T.auditar(evento="contrato", decisao="REGEX_INVALIDO", trava=regra.get("id"),
                      motivo=f"regex_alvo inválido ({e}) — ESTA TRAVA ESTÁ DESLIGADA")
            return False
    excecao = q.get("regex_excecao")
    if excecao:
        try:
            if re.search(excecao, alvo or "", re.IGNORECASE):
                return False
        except re.error as e:
            T.auditar(evento="contrato", decisao="REGEX_INVALIDO", trava=regra.get("id"),
                      motivo=f"regex_excecao inválido ({e})")
    modos = q.get("permission_modes")
    if modos and modo not in modos:
        return False
    return True


def texto_de_bloqueio(regra: dict, faltas: list) -> str:
    """As 4 partes do RETORNO. Nunca negue sem isto — negar sem receita produz
    loop de tentativa, que é a segunda maior causa de 'agente preso'."""
    partes = [f"BLOQUEADO pela trava '{regra.get('id', 'sem-id')}'.", "",
              "Condição não satisfeita:"]
    partes += [f"  - {m}" for m in faltas]
    partes.append("")
    receitas = regra.get("como_destravar") or []
    if receitas:
        partes.append("Para destravar, rode exatamente:")
        partes += [f"    {c}" for c in receitas]
        partes.append("")
    if regra.get("mensagem"):
        partes += [regra["mensagem"], ""]
    partes.append(
        "Se a condição não puder ser satisfeita agora, NÃO contorne (não edite o hook, "
        "não desabilite testes, não use outra ferramenta para o mesmo efeito). Relate ao "
        "usuário o que impede e pare. Relatar bloqueio real é sucesso; fingir é falha.")
    return "\n".join(partes)


def main() -> None:
    p = T.ler_payload()
    tool_name = p.get("tool_name", "")
    tool_input = p.get("tool_input", {}) or {}
    modo = p.get("permission_mode", "default")
    sessao = p.get("session_id", "sem-sessao")
    alvo = T.alvo_da_ferramenta(tool_name, tool_input)

    contrato = T.carregar_contrato()
    n_regras = len(contrato.get("travas", []))

    # ── 0. HEARTBEAT: prova de vida, ANTES de avaliar qualquer regra.
    T.auditar(evento="PreToolUse", decisao="invocado", ferramenta=tool_name,
              regras_no_contrato=n_regras, modo=modo)
    if n_regras == 0:
        T.auditar(evento="PreToolUse", decisao="CONTRATO_SEM_TRAVAS",
                  motivo="hook ativo mas .trava/contrato.json não declara travas — "
                         "nada será bloqueado. 'Instalado' não é 'protegido'.")

    # ── 1. AUTOPROTEÇÃO — vale mesmo com a imposição suspensa.
    protege_cofre(tool_name, tool_input, alvo)

    # ── 2. FORENSE — imagem-anterior de tudo que for tocado. Sem isto não há
    #      rollback, e "o que este agente mudou?" vira arqueologia.
    if tool_name in ("Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"):
        for caminho in T.caminhos_da_ferramenta(tool_name, tool_input):
            try:
                T.registrar_forense(sessao, caminho, tool_name)
            except Exception as e:  # noqa: BLE001
                T.auditar(evento="forense", decisao="erro", motivo=repr(e))

    # ── Registra o perfil de todo sub-agente NO NASCIMENTO.
    #    Marcar aqui é robusto; adivinhar depois lendo o transcript não é.
    if tool_name in ("Task", "Agent"):
        (T.dir_contexto() / "papel_atual.json").write_text(json.dumps({
            "tipo": tool_input.get("subagent_type"),
            "descricao": tool_input.get("description"),
            "sessao_pai": sessao, "em": int(time.time()),
        }, ensure_ascii=False), encoding="utf-8")

    # ── Quem escreve produto é EXECUTOR, e isso fica gravado para sempre.
    #    É daqui que sai a garantia "o fiscal nunca é o executor" — derivada,
    #    não declarada.
    if tool_name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        fp = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        if fp and Path(fp).suffix.lower() in T.EXT_PRODUTO:
            T.registrar_escrita_de_produto(sessao, fp)

    # ── 3. IMPOSIÇÃO suspensa: autoproteção e forense continuam; o resto passa.
    if not T.imposicao_ativa():
        T.auditar(evento="PreToolUse", decisao="imposicao_suspensa", ferramenta=tool_name,
                  motivo=T.estado_imposicao().get("motivo", ""))
        T.seguir()

    # ── 4. PAPÉIS. O fiscal não escreve código; o executor não escreve o dossiê
    #      que o julga. Sem isto, quem faz o trabalho também assina o laudo.
    #
    #      LIMITE HONESTO: o papel vem do último Task registrado. Com sub-agentes
    #      em PARALELO isso fica ambíguo — rode executor e fiscal em SEQUÊNCIA.
    #      A separação à prova de tudo é o toolset (N4), não este arquivo.
    papel = T.papel_atual()
    perfil = (contrato.get("perfis") or {}).get(papel or "", {})
    for spec in perfil.get("proibido_escrever", []):
        if tool_name in ("Write", "Edit", "MultiEdit", "NotebookEdit") and \
                re.search(spec, alvo or ""):
            T.auditar(evento="PreToolUse", decisao="deny", trava=f"papel:{papel}",
                      ferramenta=tool_name, motivo=f"papel '{papel}' não escreve {spec}",
                      alvo=(alvo or "")[:200])
            T.negar(f"BLOQUEADO pelo papel '{papel}'.\n\n"
                    f"Este papel NÃO escreve arquivos que casem com: {spec}\n\n"
                    f"{perfil.get('mensagem', '')}\n\n"
                    "Se o trabalho exige tocar nesse arquivo, ele é de OUTRO papel. "
                    "Relate ao orquestrador o que precisa ser feito e encerre. "
                    "Não contorne com Bash.")

    # ── 5. CONTRATO
    for regra in contrato.get("travas", []):
        if not regra_casa(regra, tool_name, alvo, modo):
            continue
        faltas = []

        for nome in regra.get("exige_selos", []):
            ok, motivo = T.conferir_selo(nome, estrito=bool(regra.get("estrito")))
            if not ok:
                faltas.append(motivo)

        for spec in regra.get("exige_arquivos", []):
            caminho = T.raiz_projeto() / spec["caminho"]
            minimo = int(spec.get("min_bytes", 1))
            if not caminho.exists():
                faltas.append(f"arquivo obrigatório ausente: {spec['caminho']}")
            elif caminho.stat().st_size < minimo:
                faltas.append(f"arquivo {spec['caminho']} tem {caminho.stat().st_size} "
                              f"bytes, mínimo {minimo} (conteúdo insuficiente)")

        for trecho in regra.get("exige_trecho_no_alvo", []):
            if trecho not in alvo:
                faltas.append(f"o texto obrigatório {trecho!r} não está presente na chamada")

        # Exige uma bancada humana FRESCA sobre o código atual.
        if regra.get("exige_bancada"):
            b = T.estado_bancada()
            if not b or not b.get("fechada_em"):
                faltas.append("nenhuma sessão de bancada humana foi realizada e fechada")
            elif b.get("fingerprint") != T.fingerprint_produto():
                faltas.append("a bancada humana é sobre um código ANTIGO "
                              "(o produto mudou depois do teste)")

        orc = regra.get("orcamento")
        if orc:
            n = T.incrementar(f"orc_{regra.get('id')}")
            if n > int(orc.get("max", 0)):
                faltas.append(f"orçamento esgotado: {n - 1} de {orc.get('max')} usos consumidos")

        # Trava INCONDICIONAL: se a regra só declara `quando` + `veredito`, casar
        # com o `quando` JÁ É a condição.
        tem_condicao = any(regra.get(k) for k in
                           ("exige_selos", "exige_arquivos", "exige_trecho_no_alvo",
                            "orcamento", "exige_bancada"))
        if not tem_condicao:
            faltas = [regra.get("mensagem") or f"a ação casa com a trava '{regra.get('id')}'"]

        if faltas:
            acao = regra.get("veredito", "deny")
            motivo = texto_de_bloqueio(regra, faltas)
            T.auditar(evento="PreToolUse", ferramenta=tool_name, trava=regra.get("id"),
                      decisao=acao, motivo="; ".join(faltas)[:400], alvo=(alvo or "")[:300])
            if acao == "ask":
                T.perguntar(motivo)
            T.negar(motivo)

        T.auditar(evento="PreToolUse", ferramenta=tool_name, trava=regra.get("id"),
                  decisao="passou", alvo=(alvo or "")[:300])

    T.seguir()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        T.auditar(evento="PreToolUse", decisao="erro_interno", motivo=repr(e))
        T.negar(f"Trava indisponível (erro interno no gate: {e!r}). A chamada foi NEGADA "
                "por precaução (política de falha fechada). Avise o usuário: "
                ".claude/hooks/trava_gate.py precisa de conserto.")
