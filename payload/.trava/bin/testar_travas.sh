#!/usr/bin/env bash
# testar_travas.sh — prova que as travas travam, SEM abrir uma sessão de agente.
#
# Um hook é só um programa que lê JSON no stdin e responde. Então você pode testá-lo
# alimentando-o com o mesmo payload que o runtime enviaria. É assim que se valida
# uma trava antes de confiar nela.
#
# UMA TRAVA NÃO TESTADA É UMA SUPOSIÇÃO DE SEGURANÇA — e é pior que não ter trava,
# porque produz confiança sem proteção.
#
# USO:  ./testar_travas.sh [diretorio-do-projeto]

set -uo pipefail
PROJ="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export CLAUDE_PROJECT_DIR="$PROJ"
cd "$PROJ" || exit 1
H=".claude/hooks"

OK=0; FALHOU=0; PULOU=0
hook() { printf '%s' "$2" | python3 "$H/$1.py" 2>/dev/null; }

tem_trava() { python3 -c "
import json,sys
try: c=json.load(open('.trava/contrato.json'))
except Exception: sys.exit(1)
sys.exit(0 if any(t.get('id')=='$1' for t in c.get('travas',[])) else 1)" 2>/dev/null; }

pula() { echo "  ⊘  $1 — não está no contrato instalado (ok, não é falha)"; PULOU=$((PULOU+1)); }
ok()   { echo "  ✅ $1"; OK=$((OK+1)); }
nok()  { echo "  ❌ $1"; FALHOU=$((FALHOU+1)); }

espera_bloqueio() {
  local out; out="$(hook "$2" "$3")"
  if grep -qE '"(permissionDecision)":\s*"(deny|ask)"|"decision":\s*"block"' <<<"$out"
  then ok "$1 — BLOQUEADO (correto)"
  else nok "$1 — PASSOU, deveria bloquear!  saída: ${out:0:140}"; fi
}
espera_passagem() {
  local out; out="$(hook "$2" "$3")"
  if grep -qE '"(permissionDecision)":\s*"deny"|"decision":\s*"block"' <<<"$out"
  then nok "$1 — BLOQUEADO, deveria passar!  saída: ${out:0:140}"
  else ok "$1 — passou (correto)"; fi
}

PUSH='{"hook_event_name":"PreToolUse","session_id":"t","permission_mode":"default","tool_name":"Bash","tool_input":{"command":"git push origin main"}}'
TASK_SEM='{"hook_event_name":"PreToolUse","session_id":"t","tool_name":"Task","tool_input":{"subagent_type":"general-purpose","description":"x","prompt":"faça algo"}}'
COFRE_W='{"hook_event_name":"PreToolUse","session_id":"t","tool_name":"Write","tool_input":{"file_path":".trava/selos/testes-verdes.json","content":"{}"}}'
COFRE_B='{"hook_event_name":"PreToolUse","session_id":"t","tool_name":"Bash","tool_input":{"command":"echo x > .trava/selos/testes-verdes.json"}}'
COFRE_H='{"hook_event_name":"PreToolUse","session_id":"t","tool_name":"Bash","tool_input":{"command":"sed -i s/a/b/ .claude/hooks/trava_gate.py"}}'
CHAVE='{"hook_event_name":"PreToolUse","session_id":"t","tool_name":"Bash","tool_input":{"command":"cat .trava/chave.secreta"}}'
LER_COFRE='{"hook_event_name":"PreToolUse","session_id":"t","tool_name":"Bash","tool_input":{"command":"cat .trava/contrato.json"}}'
STOP='{"hook_event_name":"SubagentStop","session_id":"t","stop_hook_active":false}'
STOP_FUS='{"hook_event_name":"SubagentStop","session_id":"t","stop_hook_active":true}'

echo; echo "─── 1. AUTOPROTEÇÃO: a trava se protege? ───"
espera_bloqueio "escrever selo via Write"       trava_gate "$COFRE_W"
espera_bloqueio "escrever selo via Bash (>)"    trava_gate "$COFRE_B"
espera_bloqueio "editar o próprio hook"         trava_gate "$COFRE_H"
espera_bloqueio "ler a chave HMAC"              trava_gate "$CHAVE"
espera_passagem "LER o contrato (deve passar)"  trava_gate "$LER_COFRE"

echo; echo "─── 2. BLOQUEIO: a trava trava? ───"
rm -rf .trava/selos .trava/contadores 2>/dev/null
tem_trava sem-push-sem-verde && espera_bloqueio "push sem selo" trava_gate "$PUSH" || pula "push sem selo"
tem_trava subagente-nasce-com-contrato && espera_bloqueio "sub-agente sem contrato" trava_gate "$TASK_SEM" || pula "sub-agente sem contrato"
espera_bloqueio "encerrar sem relatório" trava_stop "$STOP"

echo; echo "─── 3. MENTIRA: selo forjado é rejeitado? ───"
mkdir -p .trava/selos
echo '{"nome":"testes-verdes","rc":0,"ok":true,"ttl":9999,"emitido_em":9999999999,"hmac":"forjado"}' \
  > .trava/selos/testes-verdes.json
# NB: capture em variável. Com pipefail, `trava selo conferir | grep` herda o exit 1
# do conferir (que sai 1 CORRETAMENTE) e mascara o sucesso do grep — erro clássico.
saida="$(python3 .trava/bin/trava selo conferir testes-verdes 2>&1)"
if grep -q "assinatura" <<<"$saida"; then ok "selo escrito à mão — REJEITADO: $saida"
else nok "selo forjado foi ACEITO!  saída: $saida"; fi

echo; echo "─── 4. PASSAGEM: destrava quando deve? ───"
python3 .trava/bin/trava selo emitir testes-verdes --comando "true" >/dev/null 2>&1
python3 .trava/bin/trava selo emitir lint-limpo    --comando "true" >/dev/null 2>&1
tem_trava sem-push-sem-verde && espera_passagem "push com selos válidos" trava_gate "$PUSH" || pula "push com selos válidos"

echo; echo "─── 5. VERIFICAÇÃO REAL: comando que falha não emite selo ───"
if python3 .trava/bin/trava selo emitir relatorio --comando "false" >/dev/null 2>&1
then nok "selo emitido apesar de rc!=0!"
else ok "verificação falhou → selo NÃO emitido (correto)"; fi

echo; echo "─── 6. ANTI-LOOP: fusível e contador funcionam? ───"
espera_passagem "stop_hook_active=true (fusível)" trava_stop "$STOP_FUS"
rm -rf .trava/contadores
espera_bloqueio "stop tentativa 1" trava_stop "$STOP"
espera_bloqueio "stop tentativa 2" trava_stop "$STOP"
espera_bloqueio "stop tentativa 3" trava_stop "$STOP"
espera_passagem "stop tentativa 4 (cede e escala)" trava_stop "$STOP"

echo; echo "─── 7. BANCADA: laudo de agente é rejeitado? ───"
mkdir -p output
# Laudo "perfeito" na forma, mas: sem sessão de bancada, e com linguagem de processo.
printf '# LAUDO\n\n## O QUE VOCÊ VIU NOS PRIMEIROS 5 SEGUNDOS\nfuncionou\n\n## VEREDITO: APROVADO\n' \
  > output/LAUDO-BANCADA.md
if python3 "$H/verificar_bancada.py" output/LAUDO-BANCADA.md >/dev/null 2>&1
then nok "laudo sem sessão de bancada foi ACEITO!"
else ok "laudo sem sessão real — REJEITADO (correto)"; fi
rm -f output/LAUDO-BANCADA.md

echo; echo "─── 8. PAPÉIS: executor não fiscaliza o próprio trabalho? ───"
python3 - <<'PY'
import sys, os
sys.path.insert(0, os.path.join(os.environ["CLAUDE_PROJECT_DIR"], ".claude", "hooks"))
import lib_trava as T
T.registrar_escrita_de_produto("sessao-x", "src/app.ts")
print("CONFLITO" if T.conflito_de_papel("sessao-x") else "SEM-CONFLITO")
print("OK" if not T.conflito_de_papel("sessao-y") else "ERRO")
PY
if python3 -c "
import sys,os; sys.path.insert(0, os.path.join(os.environ['CLAUDE_PROJECT_DIR'],'.claude','hooks'))
import lib_trava as T; sys.exit(0 if T.conflito_de_papel('sessao-x') else 1)"
then ok "quem escreveu produto é barrado como fiscal (correto)"
else nok "executor passou como fiscal!"; fi

echo; echo "─── 9. AUDITORIA: cadeia registra e é verificável? ───"
if [[ -s .trava/auditoria.jsonl ]]; then
  n=$(wc -l < .trava/auditoria.jsonl); ok "auditoria com $n registros"
else nok "auditoria vazia — você não vai saber se a trava disparou"; fi
if python3 .trava/bin/trava auditoria --verificar >/dev/null 2>&1
then ok "cadeia de hash íntegra"
else nok "cadeia de hash quebrada"; fi
# Adultera uma linha do meio e confirma que a verificação ACUSA.
if [[ $(wc -l < .trava/auditoria.jsonl) -ge 3 ]]; then
  cp .trava/auditoria.jsonl /tmp/aud.bak
  python3 - <<'PY'
import os, json
p = os.path.join(os.environ["CLAUDE_PROJECT_DIR"], ".trava", "auditoria.jsonl")
ls = open(p, encoding="utf-8").read().splitlines()
r = json.loads(ls[1]); r["motivo"] = "ADULTERADO"
ls[1] = json.dumps(r, ensure_ascii=False, sort_keys=True)
open(p, "w", encoding="utf-8").write("\n".join(ls) + "\n")
PY
  if python3 .trava/bin/trava auditoria --verificar >/dev/null 2>&1
  then nok "adulteração do ledger NÃO foi detectada!"
  else ok "adulteração do ledger — DETECTADA (correto)"; fi
  cp /tmp/aud.bak .trava/auditoria.jsonl
fi

echo; echo "─── 10. IMPOSIÇÃO: desligar exige TTY? ───"
if python3 .trava/bin/trava imposicao off --motivo "tentativa sem tty" </dev/null >/dev/null 2>&1
then nok "imposição foi desligada SEM terminal interativo!"
else ok "desligar sem TTY — RECUSADO (correto)"; fi

echo; echo "══════════════════════════════════════════"
echo "  $OK corretos, $FALHOU falhos, $PULOU pulado(s)"
if [[ $FALHOU -eq 0 ]]; then echo "  ✅ TRAVAS VALIDADAS"; else echo "  ❌ NÃO CONFIE NESTAS TRAVAS AINDA"; fi
echo "══════════════════════════════════════════"
exit $((FALHOU > 0))
