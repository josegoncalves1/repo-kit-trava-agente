#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trava_pos.py — hook de PostToolUse. A trava do fato consumado.

PreToolUse impede. PostToolUse NÃO impede (a ferramenta já rodou) — ele detecta
o efeito e devolve o erro ao modelo com {"decision":"block","reason":...}, o que
na prática REABRE a tarefa: o modelo é informado de que o que acabou de fazer é
inaceitável e precisa corrigir.

Use quando a condição só pode ser avaliada DEPOIS: "o arquivo que você escreveu
passa no linter?", "o comando deixou o repo sujo?".

  "PostToolUse": [
    { "matcher": "Write|Edit",
      "hooks": [ { "type": "command",
                   "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/trava_pos.py\"",
                   "timeout": 30 } ] }
  ]

Efeito colateral importante: uma escrita que muda o código INVALIDA provas antigas.
Este hook revoga os selos marcados como voláteis — é o que impede um selo
'testes-verdes' de ontem autorizar um push sobre o código de hoje.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_trava as T  # noqa: E402


def main() -> None:
    p = T.ler_payload()
    tool_name = p.get("tool_name", "")
    tool_input = p.get("tool_input", {}) or {}
    contrato = T.carregar_contrato()
    regra = contrato.get("pos_acao", {})

    # 1) INVALIDAÇÃO DE PROVA: mexeu no código, o selo de teste morreu.
    if tool_name in ("Write", "Edit", "NotebookEdit", "Bash"):
        for nome in regra.get("selos_volateis", []):
            if T.revogar_selo(nome):
                T.auditar(evento="PostToolUse", decisao="selo_revogado", trava=nome,
                          motivo=f"{tool_name} alterou o estado do projeto")

    # 2) VERIFICAÇÃO IMEDIATA sobre o arquivo recém-escrito.
    caminho = str(tool_input.get("file_path", ""))
    for chk in regra.get("checagens", []):
        if not caminho or not any(caminho.endswith(s) for s in chk.get("sufixos", [])):
            continue
        cmd = chk["comando"].replace("{arquivo}", caminho)
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               cwd=str(T.raiz_projeto()), timeout=int(chk.get("timeout", 30)))
        except Exception as e:  # noqa: BLE001
            T.auditar(evento="PostToolUse", decisao="checagem_erro", motivo=repr(e))
            continue
        if r.returncode != 0:
            saida = ((r.stdout or "") + (r.stderr or ""))[-1500:]
            T.auditar(evento="PostToolUse", decisao="bloqueado", trava=chk.get("id"),
                      motivo=f"rc={r.returncode} {cmd}")
            print(json.dumps({
                "decision": "block",
                "reason": (
                    f"A alteração em {caminho} NÃO passa na checagem '{chk.get('id')}'.\n"
                    f"Comando: {cmd}\nCódigo de saída: {r.returncode}\n\n"
                    f"Saída:\n{saida}\n\n"
                    "Corrija o arquivo agora. Não prossiga para o próximo passo e não "
                    "desabilite a checagem."
                ),
            }, ensure_ascii=False))
            sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        T.auditar(evento="PostToolUse", decisao="erro_interno", motivo=repr(e))
        sys.exit(0)
