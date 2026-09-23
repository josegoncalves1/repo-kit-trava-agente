#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar_doc.py — a trava da DOCUMENTAÇÃO REVISADA JUNTO COM A ENTREGA.

O problema: documentação envelhece em silêncio. O código muda, o README continua
descrevendo o produto de três versões atrás, e ninguém percebe até alguém de fora
tentar usar — e falhar seguindo a própria documentação do projeto.

Regra deste verificador, e é simples:

    Se o PRODUTO mudou, a DOCUMENTAÇÃO tem que ter sido olhada depois.

Três exigências, todas mecânicas:

  1. FRESCOR      o doc alterado mais recentemente é MAIS NOVO que o último
                  arquivo de produto alterado. Se o código mudou depois do doc,
                  o doc descreve outra coisa.
  2. COBERTURA    todo doc declarado como "vivo" no contrato existe e tem
                  substância. Um README de 3 linhas não documenta nada.
  3. CONSISTÊNCIA os comandos citados nos docs existem de fato (arquivos e
                  scripts referenciados). Documentação que manda rodar um script
                  que não existe é pior que documentação nenhuma.

Uso:  verificar_doc.py [--docs README.md docs/] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_trava as T  # noqa: E402

FALHAS: list[str] = []


def falha(m: str) -> None:
    FALHAS.append(m)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", nargs="*", default=None)
    ap.add_argument("--min-bytes", type=int, default=400)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    raiz = T.raiz_projeto()
    cfg = T.carregar_contrato().get("documentacao", {})
    alvos = a.docs or cfg.get("vivos") or ["README.md"]
    min_bytes = int(cfg.get("min_bytes", a.min_bytes))

    docs: list[Path] = []
    for alvo in alvos:
        p = raiz / alvo
        if p.is_dir():
            docs += sorted(p.rglob("*.md"))
        elif p.exists():
            docs.append(p)
        else:
            falha(f"documento declarado como vivo não existe: {alvo}")

    if not docs:
        falha("nenhum documento encontrado. Declare os docs vivos em "
              ".trava/contrato.json → documentacao.vivos")
        print("\n".join(f"  ✗ {f}" for f in FALHAS), file=sys.stderr)
        return 1

    # ── 1. FRESCOR ──────────────────────────────────────────────────────────
    produto = T.arquivos_de_produto()
    if produto:
        mais_novo_prod = max(produto, key=lambda p: p.stat().st_mtime)
        mais_novo_doc = max(docs, key=lambda p: p.stat().st_mtime)
        if mais_novo_prod.stat().st_mtime > mais_novo_doc.stat().st_mtime:
            falha(f"o código mudou DEPOIS da documentação: "
                  f"'{mais_novo_prod.relative_to(raiz)}' é mais novo que "
                  f"'{mais_novo_doc.relative_to(raiz)}'. "
                  f"Revise a documentação e ajuste o que mudou — ou, se nada mudou "
                  f"para o leitor, toque o arquivo depois de reler e confirmar.")

    # ── 2. COBERTURA ────────────────────────────────────────────────────────
    for d in docs:
        n = d.stat().st_size
        if n < min_bytes:
            falha(f"{d.relative_to(raiz)} tem {n} bytes (mínimo {min_bytes}). "
                  f"Documento vivo com conteúdo simbólico não documenta nada.")

    # ── 3. CONSISTÊNCIA: o que os docs mandam rodar existe? ─────────────────
    # Pega caminhos citados em blocos de código e em `crases`, e confere.
    citados: set[str] = set()
    for d in docs:
        texto = d.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"[`\s(]((?:\./|scripts/|bin/|src/)[\w./-]+\.\w{1,6})", texto):
            citados.add(m.group(1))
    faltando = []
    for c in sorted(citados):
        alvo = raiz / c.lstrip("./")
        if not alvo.exists():
            faltando.append(c)
    if faltando:
        falha(f"a documentação cita {len(faltando)} caminho(s) que não existem: "
              f"{', '.join(faltando[:6])}{'…' if len(faltando) > 6 else ''}. "
              f"Documentação que manda rodar o que não existe é pior que nenhuma.")

    rel = {"aprovado": not FALHAS, "docs": [str(d.relative_to(raiz)) for d in docs],
           "falhas": FALHAS}
    if a.json:
        print(json.dumps(rel, indent=2, ensure_ascii=False))
    elif FALHAS:
        print("DOCUMENTAÇÃO NÃO REVISADA:", file=sys.stderr)
        for f in FALHAS:
            print(f"  ✗ {f}", file=sys.stderr)
    else:
        print(f"  ✅ documentação revisada junto com a entrega "
              f"({len(docs)} documento(s) vivos, mais novos que o código)")

    T.auditar(evento="doc", decisao="ok" if not FALHAS else "pendente",
              trava="verificar_doc", motivo=f"{len(FALHAS)} falha(s)")
    return 1 if FALHAS else 0


if __name__ == "__main__":
    sys.exit(main())
