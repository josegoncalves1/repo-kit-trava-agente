#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trava_entrega.py — PreToolUse. A trava de ENTREGA FINAL, em três estágios.

    ação de entrega detectada (git tag, push --tags, publish, release, deploy…)
            │
            ▼
    [1] checagens MECÂNICAS  — selos, evidência visual, documentação revisada
            │
      ┌─────┴─────┐
   falhou       passou
      │             │
    DENY            ▼
  (com a lista  [2] BANCADA HUMANA — houve? foi sobre ESTE código? durou?
   do que falta)    │
              ┌─────┴─────┐
           falhou       passou
              │             │
            DENY            ▼
      (peça ao usuário  [3] ASK — o runtime pergunta ao USUÁRIO
       que sente e use)      (fora do alcance do agente)

Por que três estágios:
  • Negar enquanto está mecanicamente quebrado evita chamar a pessoa para avaliar
    print em branco — o que treina ela a aprovar no automático, e aí a trava morre.
  • A bancada é o teste que não se automatiza. O programa não julga se ficou bom;
    ele garante que alguém usou, que usou ESTE código, e que escreveu o que achou.
  • O ASK é a PROVA DE HUMANO. Assinatura em arquivo não prova nada — um agente
    escreve 'nome: fulano'. O ASK devolve a decisão ao canal do usuário no runtime,
    que o agente não consegue responder por ele.

FALHA FECHADA: entrega final não passa por trava quebrada.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_trava as T  # noqa: E402

PADRAO_ENTREGA = (
    r"git\s+tag\b|git\s+push[^|;&]*--tags|npm\s+publish|yarn\s+publish|pnpm\s+publish|"
    r"docker\s+push|gh\s+release\s+create|cargo\s+publish|twine\s+upload|"
    r"\bmake\s+(release|deploy|publish|entregar)\b|"
    r"\./(deploy|publicar|entregar|release)\b|"
    r"godot[^|;&]*--export|unity[^|;&]*-buildTarget|"
    r"(kubectl|helm)\s+(apply|upgrade|install)\b|terraform\s+apply\b"
)


def main() -> None:
    p = T.ler_payload()
    tool = p.get("tool_name", "")
    alvo = T.alvo_da_ferramenta(tool, p.get("tool_input", {}) or {})
    contrato = T.carregar_contrato()
    cfg = contrato.get("entrega_final", {})

    if not cfg.get("ativo", True) or not T.imposicao_ativa():
        sys.exit(0)

    try:
        if not re.search(cfg.get("regex", PADRAO_ENTREGA), alvo or "", re.IGNORECASE):
            sys.exit(0)
    except re.error as e:
        T.auditar(evento="PreToolUse", decisao="REGEX_INVALIDO", trava="entrega-final",
                  motivo=str(e))
        sys.exit(0)

    raiz = T.raiz_projeto()
    falhas: list[str] = []
    medidas: list[str] = []

    # ── ESTÁGIO 1a: selos exigidos, re-executados agora ─────────────────────
    for nome in cfg.get("exige_selos", []):
        ok, motivo = T.conferir_selo(nome, estrito=True)
        (medidas if ok else falhas).append(motivo)

    # ── ESTÁGIO 1b: evidência visual medida (contraste, tela chapada, movimento)
    dossie = cfg.get("dossie", "output/LAUDO-BANCADA.md")
    midia = cfg.get("midia", "evidencias")
    vux = Path(__file__).parent / "verificar_entrega_ux.py"
    if cfg.get("exige_evidencia_visual", True) and vux.exists():
        cmd = [sys.executable, str(vux), dossie, "--midia", midia, "--fonte", ".",
               "--assinatura-opcional", "--min-contraste", str(cfg.get("min_contraste", 4.5))]
        if cfg.get("exige_movimento"):
            cmd.append("--exige-movimento")
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(raiz),
                           timeout=int(cfg.get("timeout", 110)))
        if r.stdout.strip():
            medidas.append(r.stdout.strip())
        if r.returncode != 0:
            falhas.append(r.stderr.strip() or "evidência visual não passa")

    # ── ESTÁGIO 1c: documentação revisada junto com a entrega ───────────────
    vdoc = Path(__file__).parent / "verificar_doc.py"
    if cfg.get("exige_revisao_doc", True) and vdoc.exists():
        r = subprocess.run([sys.executable, str(vdoc)], capture_output=True,
                           text=True, cwd=str(raiz), timeout=60)
        if r.returncode != 0:
            falhas.append(r.stderr.strip() or "documentação não revisada")
        else:
            medidas.append(r.stdout.strip())

    # ── ESTÁGIO 2: a bancada humana ─────────────────────────────────────────
    if cfg.get("exige_bancada", True):
        vb = Path(__file__).parent / "verificar_bancada.py"
        minimo = str(contrato.get("bancada", {}).get("min_segundos", 180))
        r = subprocess.run([sys.executable, str(vb), dossie, "--min-segundos", minimo],
                           capture_output=True, text=True, cwd=str(raiz), timeout=60)
        if r.returncode != 0:
            falhas.append(r.stderr.strip() or "bancada humana não validada")
        else:
            medidas.append(r.stdout.strip())

    if falhas:
        T.auditar(evento="PreToolUse", decisao="deny", trava="entrega-final",
                  motivo="; ".join(falhas)[:400], alvo=(alvo or "")[:200])
        T.negar(
            "ENTREGA FINAL BLOQUEADA.\n\n"
            + "\n\n".join(f"✗ {f}" for f in falhas)
            + "\n\n"
            + ("Medidas que passaram:\n" + "\n".join(medidas) + "\n\n" if medidas else "")
            + "SE O QUE FALTA É A BANCADA HUMANA, entenda o que se espera de você:\n"
              "  Você NÃO conduz o teste. Você PREPARA o terreno e PEDE à pessoa.\n"
              "    1. suba o produto e deixe-o utilizável agora\n"
              "    2. rode: ./trava bancada abrir\n"
              "    3. diga ao usuário, em uma mensagem curta: o que abrir, o que tentar\n"
              "       fazer, e que ele deve anotar o que achou em output/LAUDO-BANCADA.md\n"
              "    4. ESPERE. Não preencha o laudo por ele. Não simule a opinião dele.\n"
              "       Um laudo escrito por você é fraude, e o verificador rejeita.\n\n"
            "NÃO contorne: não edite este hook, não afrouxe o verificador, não use outro\n"
            "comando para publicar. Se algo for impossível, relate ao usuário e pare."
        )

    # ── ESTÁGIO 3: ASK — o veredito sensorial é da pessoa, e só dela ────────
    T.auditar(evento="PreToolUse", decisao="ask", trava="entrega-final",
              motivo="mecânicas e bancada passaram; aguardando veredito humano",
              alvo=(alvo or "")[:200])
    T.perguntar(
        "ENTREGA FINAL — exige o seu veredito, e só o seu.\n\n"
        "As checagens mecânicas passaram, e há uma sessão de bancada humana válida\n"
        "sobre este código:\n\n"
        + "\n".join(medidas) + "\n\n"
        "O que nenhum programa julga, e por isso está sendo perguntado a você:\n"
        "  • as cores são confortáveis numa sessão longa, ou só passam no contraste?\n"
        "  • os botões fazem sentido ONDE estão, ou apenas funcionam?\n"
        "  • existe um propósito no conjunto, ou é um monte de código junto, cada\n"
        "    um com um propósito desconexo do outro?\n"
        "  • a sensação prometida está lá? a areia esparrama com a passagem do caça,\n"
        "    ou é uma textura piscando que só parece certa no papel?\n\n"
        f"Abra '{dossie}' e a evidência em '{midia}/' antes de decidir.\n"
        "Aprovar aqui é dizer que você VIU e que está bom. Negar devolve ao executor."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        T.auditar(evento="PreToolUse", decisao="erro_interno", trava="entrega-final",
                  motivo=repr(e))
        T.negar(f"Trava de entrega indisponível (erro interno: {e!r}). Entrega NEGADA "
                "por precaução. Avise o usuário.")
