#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar_revisao.py — o verificador da FISCALIZAÇÃO CRUZADA.

Problema: num mesmo runtime, executor e fiscal têm o mesmo disco e as mesmas
ferramentas. Não há como provar quem rodou o selo. Então não se tenta provar
identidade — se torna o auto-aval INVIÁVEL por quatro exigências que só uma
revisão de verdade satisfaz:

  1. FRESCOR   a revisão precisa ser MAIS NOVA que o código revisado.
               Mexeu no código depois? A revisão morreu. É o que impede
               "reviso, depois conserto escondido".
  2. VEREDITO  linha '## VEREDITO: APROVADO|REPROVADO' explícita.
  3. LASTRO    se APROVADO, precisa citar arquivo:linha REAIS, que existem e
               têm aquela linha. Não dá para aprovar sem ter aberto o código.
  4. SUBSTÂNCIA  seções obrigatórias preenchidas (qualidade, usabilidade,
               o que foi testado), com tamanho mínimo.

Uso:  verificar_revisao.py <arquivo-revisao> <dir-fonte> [--min-refs N]
Sai 0 se a revisão é válida; 1 caso contrário, explicando o que falta.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECOES = ["## QUALIDADE", "## USABILIDADE", "## PRIMEIRA IMPRESSÃO", "## O QUE FOI TESTADO"]

# "200 OK" NÃO é prova de usabilidade. Prova de uso é a jornada que o usuário
# percorre e o atrito que ele sente. Estes padrões, SOZINHOS, são recusados.
PROVA_FRACA = re.compile(
    r"^[\s\-*>]*(?:(?:http\s*)?(?:200|201|204)(?:\s*ok)?|ok|okay|funciona(?:ndo|u)?|"
    r"sem\s+erros?|tudo\s+certo|passou|success(?:ful)?|healthy|up)\W*$",
    re.I | re.M)
# Uma jornada é "N. ação → o que o usuário vê".
PASSO_JORNADA = re.compile(r"^\s*\d+[.)]\s+.{8,}?(?:→|->|=>)\s*\S.{4,}", re.M)
EXT_FONTE = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".sh", ".yml", ".yaml", ".json"}


def falhar(msg: str) -> None:
    print(f"REVISÃO INVÁLIDA: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("revisao")
    ap.add_argument("fonte", nargs="?", default=".")
    ap.add_argument("--min-refs", type=int, default=2)
    ap.add_argument("--min-bytes", type=int, default=400)
    a = ap.parse_args()

    rev = Path(a.revisao)
    if not rev.exists():
        falhar(f"{a.revisao} não existe. O fiscal ainda não escreveu a revisão.")
    texto = rev.read_text(encoding="utf-8", errors="replace")
    if len(texto.encode()) < a.min_bytes:
        falhar(f"{a.revisao} tem {len(texto.encode())} bytes; mínimo {a.min_bytes}. "
               "Revisão de uma linha não é revisão.")

    # ── 2. VEREDITO explícito
    m = re.search(r"^##\s*VEREDITO:\s*(APROVADO|REPROVADO)\s*$", texto, re.M | re.I)
    if not m:
        falhar("falta a linha '## VEREDITO: APROVADO' ou '## VEREDITO: REPROVADO'.")
    veredito = m.group(1).upper()

    # ── 4. SUBSTÂNCIA: seções obrigatórias, cada uma com conteúdo
    for sec in SECOES:
        if sec not in texto.upper():
            falhar(f"falta a seção obrigatória '{sec}'.")
        i = texto.upper().index(sec)
        corpo = texto[i + len(sec):]
        corpo = re.split(r"\n##\s", corpo)[0]
        if len(corpo.strip()) < 60:
            falhar(f"a seção '{sec}' está vazia ou quase. Descreva de verdade.")

        # ── 6. ATRAÇÃO: o resultado convida a pessoa a continuar?
        if sec == "## PRIMEIRA IMPRESSÃO":
            if not re.search(r"###\s*O\s+QUE\s+SE\s+V[ÊE]", corpo, re.I):
                falhar("PRIMEIRA IMPRESSÃO precisa da subseção '### O QUE SE VÊ': descreva "
                       "literalmente a tela/saída nos primeiros segundos, como quem olha "
                       "pela primeira vez. Não descreva o que o código faz.")
            if not re.search(r"###\s*QUER\s+CONTINUAR\?", corpo, re.I):
                falhar("PRIMEIRA IMPRESSÃO precisa da subseção '### QUER CONTINUAR?' com um "
                       "julgamento explícito: a pessoa segue adiante ou abandona, e por quê. "
                       "Correto e atraente são coisas diferentes.")
            if all(PROVA_FRACA.match(l) for l in corpo.splitlines() if l.strip()):
                falhar("PRIMEIRA IMPRESSÃO não pode ser 'funcionou'. Isso é diagnóstico de "
                       "servidor, não impressão de pessoa.")

        # ── 5. PROVA DE USO: usabilidade não se prova com código de status.
        if sec == "## USABILIDADE":
            linhas = [l for l in corpo.splitlines() if l.strip()]
            if linhas and all(PROVA_FRACA.match(l) for l in linhas):
                falhar("a seção USABILIDADE contém só status/afirmação genérica "
                       "('200 OK', 'funcionou', 'sem erros'). Isso prova que o serviço "
                       "respondeu, não que a pessoa consegue usar. Descreva a JORNADA.")
            passos = PASSO_JORNADA.findall(corpo)
            if len(passos) < 3:
                falhar(f"USABILIDADE tem {len(passos)} passo(s) de jornada; mínimo 3. "
                       "Formato: '1. o que o usuário faz → o que ele vê'. "
                       "Percorra o fluxo como usuário, não como monitor de saúde.")
            atrito = re.search(r"###\s*ATRITO(.*?)(?=\n###|\n##|\Z)", corpo,
                               re.I | re.S)
            if not atrito or len(atrito.group(1).strip()) < 40:
                falhar("USABILIDADE precisa de uma subseção '### ATRITO' descrevendo onde "
                       "a pessoa hesita, se confunde, espera ou desiste — e, se não houve "
                       "atrito, por que você conclui isso (o que tentou quebrar).")

    if veredito == "REPROVADO":
        print("revisão válida: VEREDITO=REPROVADO (o trabalho precisa voltar ao executor)")
        sys.exit(0)

    # ── 3. LASTRO: referências arquivo:linha que realmente existem
    raiz = Path(a.fonte).resolve()
    refs = re.findall(r"([\w./\-]+\.\w{1,5}):(\d+)", texto)
    validas = 0
    for caminho, linha in refs:
        p = (raiz / caminho).resolve()
        if not p.exists() or raiz not in p.parents and p != raiz:
            continue
        try:
            if 0 < int(linha) <= len(p.read_text(errors="replace").splitlines()):
                validas += 1
        except OSError:
            pass
    if validas < a.min_refs:
        falhar(f"APROVADO com apenas {validas} referência(s) arquivo:linha verificável(is); "
               f"exigidas {a.min_refs}. Cite trechos reais do código que você revisou.")

    # ── 1. FRESCOR: a revisão precisa ser mais nova que o código
    mais_novo, quando = None, 0.0
    for p in raiz.rglob("*"):
        if (p.is_file() and p.suffix in EXT_FONTE
                and ".trava" not in p.parts and ".claude" not in p.parts
                and ".git" not in p.parts and p.resolve() != rev.resolve()):
            if p.stat().st_mtime > quando:
                mais_novo, quando = p, p.stat().st_mtime
    if mais_novo and quando > rev.stat().st_mtime:
        falhar(f"a revisão é MAIS ANTIGA que o código: '{mais_novo.name}' foi alterado "
               f"depois de {rev.name}. O código mudou após a revisão — revise de novo.")

    print(f"revisão válida: VEREDITO=APROVADO, {validas} referência(s) verificadas, "
          f"revisão mais nova que o código")
    sys.exit(0)


if __name__ == "__main__":
    main()
