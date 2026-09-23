#!/usr/bin/env sh
# =============================================================================
# TRAVA-KIT — instalador
#
#   curl -fsSL https://raw.githubusercontent.com/josegoncalves1/repo-kit-trava-agente/main/setup.sh | sh
#
# Instala na RAIZ DO DIRETÓRIO ATUAL, convivendo com o que já existe (Dockerfile,
# src/, scripts/, o que for). Não move nada seu, não apaga nada seu.
#
#   ./setup.sh                 instala aqui, contrato mínimo adaptado ao projeto
#   ./setup.sh --completo      instala o contrato de exemplo inteiro
#   ./setup.sh --dry-run       mostra o que faria, sem tocar em nada
#   ./setup.sh --destino DIR   instala em outro diretório
#
# SEGURO POR PADRÃO: faz backup datado do settings.json, FUNDE em vez de
# sobrescrever, nunca substitui um contrato.json existente, e é idempotente.
#
# ⚠️  Você está prestes a rodar um script baixado da internet. Leia-o antes:
#     curl -fsSL <url>/setup.sh | less
# =============================================================================
set -eu

REPO="${TRAVA_REPO:-josegoncalves1/repo-kit-trava-agente}"
REF="${TRAVA_REF:-main}"
DESTINO="$(pwd)"
MODO="minimo"
DRY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --completo) MODO="completo"; shift ;;
    --dry-run)  DRY=1; shift ;;
    --destino)  DESTINO="$2"; shift 2 ;;
    -h|--help)  sed -n '3,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "opção desconhecida: $1" >&2; exit 2 ;;
  esac
done

diz() { printf '%s\n' "$*"; }
faz() { if [ "$DRY" -eq 1 ]; then diz "   [dry-run] $*"; else eval "$@"; fi; }
erro() { printf '%s\n' "ERRO: $*" >&2; exit 1; }

[ -d "$DESTINO" ] || erro "'$DESTINO' não é um diretório."
DESTINO="$(cd "$DESTINO" && pwd)"

command -v python3 >/dev/null 2>&1 || erro "python3 não encontrado. O kit precisa dele (só a biblioteca padrão; nenhuma dependência externa)."

# ── de onde vem o payload ────────────────────────────────────────────────────
# Dois caminhos: repositório clonado (payload/ ao lado) ou download do tarball.
AQUI="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo "")"
TMP=""
if [ -n "$AQUI" ] && [ -d "$AQUI/payload/.claude/hooks" ]; then
  FONTE="$AQUI/payload"
  diz "═══ TRAVA-KIT — instalando a partir do repositório local"
else
  command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1 \
    || erro "preciso de curl ou wget para baixar o payload."
  command -v tar >/dev/null 2>&1 || erro "preciso de tar."
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT INT TERM
  URL="https://codeload.github.com/$REPO/tar.gz/$REF"
  diz "═══ TRAVA-KIT — baixando de $REPO@$REF"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$URL" | tar -xz -C "$TMP" || erro "falha ao baixar/extrair $URL"
  else
    wget -qO- "$URL" | tar -xz -C "$TMP" || erro "falha ao baixar/extrair $URL"
  fi
  FONTE="$(find "$TMP" -maxdepth 2 -type d -name payload | head -1)"
  [ -n "$FONTE" ] || erro "payload/ não encontrado no tarball."
fi

diz "    destino: $DESTINO"
[ "$DRY" -eq 1 ] && diz "    (dry-run: nada será alterado)"
diz ""

# ── 1. detectar como ESTE projeto verifica ───────────────────────────────────
# Sem isto, o contrato nasce com um `pytest` fixo que trava para sempre num
# projeto Node — e a primeira coisa que alguém faz é desligar a trava inteira.
diz "1. detectando os comandos de verificação do projeto…"
CMD_TESTE=""; CMD_LINT=""
if   [ -f "$DESTINO/package.json" ]; then
  grep -q '"test"' "$DESTINO/package.json" && CMD_TESTE="npm test --silent"
  grep -q '"lint"' "$DESTINO/package.json" && CMD_LINT="npm run lint --silent"
elif [ -f "$DESTINO/pyproject.toml" ] || [ -f "$DESTINO/pytest.ini" ] || [ -d "$DESTINO/tests" ]; then
  CMD_TESTE="python3 -m pytest -q"
  grep -qi ruff "$DESTINO/pyproject.toml" 2>/dev/null && CMD_LINT="python3 -m ruff check ."
elif [ -f "$DESTINO/Cargo.toml" ]; then
  CMD_TESTE="cargo test --quiet"; CMD_LINT="cargo clippy -- -D warnings"
elif [ -f "$DESTINO/go.mod" ]; then
  CMD_TESTE="go test ./..."; CMD_LINT="go vet ./..."
elif [ -f "$DESTINO/Makefile" ] && grep -q '^test:' "$DESTINO/Makefile"; then
  CMD_TESTE="make test"
fi
# Scripts de verificação PRÓPRIOS. Projetos de infra/docker/shell raramente têm
# framework de teste, mas quase sempre têm um validar.sh — que é exatamente a
# verificação que interessa.
if [ -z "$CMD_TESTE" ]; then
  for c in validar.sh verificar.sh check.sh test.sh scripts/validar.sh scripts/check.sh; do
    [ -f "$DESTINO/$c" ] && { CMD_TESTE="sh $c"; break; }
  done
fi
[ -z "$CMD_LINT" ] && [ -f "$DESTINO/docker-compose.yml" ] && CMD_LINT="docker compose config --quiet"

if [ -n "$CMD_TESTE" ]; then diz "   testes: $CMD_TESTE"; else
  diz "   ⚠️  nenhum comando de teste detectado — a trava de teste ficará DESLIGADA."
  diz "       (melhor desligada que bloqueando git push para sempre sem saída)"
fi
[ -n "$CMD_LINT" ] && diz "   lint:   $CMD_LINT"
diz ""

# ── 2. copiar os artefatos ───────────────────────────────────────────────────
diz "2. extraindo artefatos na raiz do projeto…"
faz "mkdir -p '$DESTINO/.claude/hooks' '$DESTINO/.claude/agents' '$DESTINO/.claude/commands' '$DESTINO/.claude/skills' '$DESTINO/.trava/bin' '$DESTINO/.trava/formularios' '$DESTINO/output' '$DESTINO/evidencias'"
faz "cp '$FONTE/.claude/hooks/'*.py '$DESTINO/.claude/hooks/'"
faz "cp '$FONTE/.claude/agents/'*.md '$DESTINO/.claude/agents/'"
faz "cp '$FONTE/.claude/commands/'*.md '$DESTINO/.claude/commands/'"
faz "cp -R '$FONTE/.claude/skills/.' '$DESTINO/.claude/skills/'"
faz "cp '$FONTE/.trava/bin/trava' '$FONTE/.trava/bin/testar_travas.sh' '$DESTINO/.trava/bin/'"
faz "cp '$FONTE/.trava/formularios/'*.md '$DESTINO/.trava/formularios/'"
faz "chmod +x '$DESTINO/.trava/bin/trava' '$DESTINO/.trava/bin/testar_travas.sh'"
[ -f "$DESTINO/.trava/bloco-contrato.md" ] || faz "cp '$FONTE/.trava/bloco-contrato.md' '$DESTINO/.trava/'"
[ -f "$DESTINO/CONTRATO-DE-ENTREGA.md" ] && diz "   CONTRATO-DE-ENTREGA.md já existe — PRESERVADO" \
  || faz "cp '$FONTE/CONTRATO-DE-ENTREGA.md' '$DESTINO/' 2>/dev/null || true"

# atalho ./trava na raiz — a porta que todo mundo usa
if [ "$DRY" -eq 0 ]; then
  cat > "$DESTINO/trava" <<'WRAP'
#!/usr/bin/env sh
# atalho para .trava/bin/trava — a porta única do kit
exec python3 "$(cd "$(dirname "$0")" && pwd)/.trava/bin/trava" "$@"
WRAP
  chmod +x "$DESTINO/trava"
fi
diz "   .claude/{hooks,agents,commands,skills}/  .trava/{bin,formularios}/  ./trava"
diz ""

# ── 3. contrato (nunca sobrescreve) ──────────────────────────────────────────
diz "3. instalando .trava/contrato.json …"
if [ -f "$DESTINO/.trava/contrato.json" ]; then
  diz "   já existe — PRESERVADO. Compare com .trava/contrato.exemplo.json à mão."
  faz "cp '$FONTE/.trava/contrato.exemplo.json' '$DESTINO/.trava/contrato.exemplo.json'"
elif [ "$MODO" = "completo" ]; then
  faz "cp '$FONTE/.trava/contrato.exemplo.json' '$DESTINO/.trava/contrato.json'"
  diz "   contrato COMPLETO instalado."
  diz "   ⚠️  ele bloqueia Write/Edit até existir docs/PLANO.md com '## APROVADO POR:'."
elif [ "$DRY" -eq 0 ]; then
  cp "$FONTE/.trava/contrato.exemplo.json" "$DESTINO/.trava/contrato.exemplo.json"
  python3 - "$DESTINO" "$CMD_TESTE" "$CMD_LINT" <<'PY'
import json, sys
proj, cmd_teste, cmd_lint = sys.argv[1], sys.argv[2], sys.argv[3]

verifs = {
  "relatorio": {"comando": "test -s output/relatorio.md && [ $(wc -c < output/relatorio.md) -ge 300 ]",
                "ttl": 0, "descricao": "Relatório de entrega do sub-agente."},
  "revisao-cruzada": {"comando": "python3 .claude/hooks/verificar_revisao.py output/REVISAO.md . --min-refs 2",
                      "ttl": 3600, "descricao": "Revisão do FISCAL, fresca e com lastro."},
  "doc-revisada": {"comando": "python3 .claude/hooks/verificar_doc.py",
                   "ttl": 3600, "descricao": "Documentação viva mais nova que o código."},
}
travas = []
if cmd_teste:
    verifs["testes-verdes"] = {"comando": cmd_teste, "ttl": 1800,
                               "descricao": "Suíte de testes passa inteira."}
    travas.append({
        "id": "sem-push-sem-verde",
        "quando": {"ferramentas": ["Bash"], "regex_alvo": "git\\s+(push|commit)"},
        "exige_selos": ["testes-verdes"], "estrito": True, "veredito": "deny",
        "como_destravar": ["./trava selo emitir testes-verdes"],
        "mensagem": "Modo ESTRITO: a verificação é RE-EXECUTADA agora. Selo antigo não serve."})
if cmd_lint:
    verifs["lint-limpo"] = {"comando": cmd_lint, "ttl": 1800, "descricao": "Sem violações de lint."}

travas += [
  {"id": "subagente-nasce-com-contrato",
   "quando": {"ferramentas": ["Task"]},
   "exige_trecho_no_alvo": ["## CONTRATO DE EXECUÇÃO"], "veredito": "deny",
   "como_destravar": ["cat .trava/bloco-contrato.md", "# cole no INÍCIO do prompt do sub-agente"],
   "mensagem": "O sub-agente nasce sem a sua conversa. Sem o contrato no prompt ele bate nas travas sem saber destravar e entra em loop."},
  {"id": "confirmar-destrutivo",
   "quando": {"ferramentas": ["Bash"],
              "regex_alvo": "\\b(rm\\s+-rf|drop\\s+(table|database)|truncate|git\\s+reset\\s+--hard|git\\s+clean\\s+-fd|mkfs\\.|dd\\s+of=/dev/)|docker[\\s-]+compose\\s+(down|rm)[^|;&]*(-v\\b|--volumes)|docker\\s+volume\\s+(rm|prune)"},
   "veredito": "ask",
   "mensagem": "Ação destrutiva e IRREVERSÍVEL. Se for docker: 'down -v' e 'volume rm' APAGAM OS DADOS dos volumes. Liste exatamente o que será perdido antes de o usuário aprovar."},
]

contrato = {
  "versao": 1,
  "_comentario": ("Contrato MÍNIMO gerado pelo setup.sh. Adicione UMA trava por vez, cada "
                  "uma respondendo a uma falha que JÁ ACONTECEU. Exemplo completo em "
                  ".trava/contrato.exemplo.json. Antes de adicionar, leia o antipadrão "
                  "'travar demais' em docs/07-antipadroes.md."),
  "verificacoes": verifs,
  "travas": travas,
  "perfis": {
    "trava-fiscal": {"proibido_escrever": ["\\.(ts|tsx|js|jsx|vue|svelte|py|go|rs|css|scss|html|gd|shader)$"],
                     "mensagem": "Você é FISCAL. Fiscal aponta, não conserta. Se corrigir, vira executor do próprio laudo."},
    "trava-executor": {"proibido_escrever": ["output/REVISAO\\.md$", "output/LAUDO-BANCADA\\.md$"],
                       "mensagem": "Você é EXECUTOR. Quem constrói não julga: você não escreve a revisão nem o laudo."},
    "trava-operador": {"proibido_escrever": ["\\.(ts|tsx|js|jsx|vue|svelte|py|go|rs|css|scss|html|gd|shader)$"],
                       "mensagem": "Você é OPERADOR. Opera e relata; não conserta."},
  },
  "bancada": {
    "alvo": "a interface do produto, como um usuário a usaria",
    "min_segundos": 180,
    "roteiro": [
      "Abra o produto como se fosse a primeira vez. Não leia documentação antes.",
      "Nos primeiros 5 segundos: o que saltou aos olhos? Anote ANTES de explorar.",
      "Tente realizar a tarefa principal sem que ninguém explique nada.",
      "Clique em cada botão visível. Faz o que o nome promete? Deveria estar ali?",
      "Force o erro: envie vazio, envie lixo, recarregue no meio, desconecte a rede.",
      "Passe 30s parado olhando a tela. Cansa? Alguma coisa vibra, aperta ou grita?",
      "Se o produto promete uma sensação (movimento, peso, resposta): ela está lá?",
    ],
  },
  "documentacao": {"vivos": ["README.md"], "min_bytes": 400},
  "entrega_final": {
    "ativo": True,
    "exige_selos": [k for k in ("testes-verdes",) if k in verifs],
    "exige_bancada": True, "exige_revisao_doc": True,
    "exige_evidencia_visual": False, "exige_movimento": False,
    "min_contraste": 4.5, "dossie": "output/LAUDO-BANCADA.md", "midia": "evidencias",
    "_nota": "exige_evidencia_visual começa desligado: ligue quando o projeto tiver interface e você estiver capturando telas em evidencias/.",
  },
  "saida_subagente": {
    "exige_selos": ["relatorio"],
    "exige_arquivos": [{"caminho": "output/relatorio.md", "min_bytes": 300}],
    "max_reentradas": 3,
    "como_destravar": {"relatorio": "escreva output/relatorio.md (o que fez, o que verificou, o que ficou pendente) e rode: ./trava selo emitir relatorio"},
    "saida_honrosa": ("Se a tarefa for IMPOSSÍVEL, isso também é entrega válida: escreva em "
                      "output/relatorio.md o que tentou, o erro literal e o que faltaria; emita "
                      "o selo; encerre. Relatar bloqueio é sucesso; fingir conclusão é falha."),
  },
  "saida_por_papel": {
    "trava-fiscal": {
      "exige_arquivos": [{"caminho": "output/REVISAO.md", "min_bytes": 400}],
      "max_reentradas": 3,
      "saida_honrosa": "REPROVADO é um veredito válido e bom. Diga isso com lastro e encerre — não conserte.",
    }
  },
  "saida_principal": {"exige_selos": [], "max_reentradas": 1},
  "loop": {"max_rodadas": 6},
  "pos_acao": {
    "selos_volateis": [k for k in ("testes-verdes", "lint-limpo", "revisao-cruzada", "doc-revisada") if k in verifs],
    "checagens": [],
  },
}
with open(f"{proj}/.trava/contrato.json", "w", encoding="utf-8") as fh:
    json.dump(contrato, fh, indent=2, ensure_ascii=False)
print(f"   contrato MÍNIMO gerado: {len(travas)} trava(s) + saída de sub-agente + bancada")
PY
else diz "   [dry-run] geraria contrato mínimo"; fi
diz ""

# ── 4. O PASSO QUE LIGA ──────────────────────────────────────────────────────
diz "4. registrando os hooks em .claude/settings.json  ← o passo que a cópia não faz"
if [ "$DRY" -eq 0 ]; then
  python3 - "$DESTINO" "$FONTE/.claude/settings.trava.json" <<'PY'
import json, os, shutil, sys, time
proj, fragmento = sys.argv[1], sys.argv[2]
alvo = f"{proj}/.claude/settings.json"

cfg = {}
if os.path.exists(alvo):
    bak = f"{alvo}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(alvo, bak)
    print(f"   backup: {os.path.basename(bak)}")
    try:
        cfg = json.load(open(alvo, encoding="utf-8"))
    except Exception as e:
        print(f"   ERRO: settings.json existente é inválido ({e}). ABORTADO — conserte-o primeiro.")
        sys.exit(1)

novo = json.load(open(fragmento, encoding="utf-8"))

def comandos_de(grupos):
    """Comandos já registrados. NÃO compare substring sobre json.dumps: as aspas
    do comando viram \\" na serialização e a comparação nunca casa — foi assim
    que a idempotência quebrou na primeira versão deste script."""
    return {h.get("command") for g in grupos for h in g.get("hooks", [])}

hooks = cfg.setdefault("hooks", {})
add = dup = 0
for evento, grupos in novo.get("hooks", {}).items():
    existentes = hooks.setdefault(evento, [])
    ja = comandos_de(existentes)
    for g in grupos:
        g = {k: v for k, v in g.items() if not k.startswith("_")}
        if g["hooks"][0]["command"] in ja:
            dup += 1                      # idempotente: rodar de novo não duplica
        else:
            existentes.append(g); add += 1

perms = cfg.setdefault("permissions", {})
for chave in ("deny", "ask"):
    lista = perms.setdefault(chave, [])
    for r in novo.get("permissions", {}).get(chave, []):
        if r not in lista:
            lista.append(r); add += 1

json.dump(cfg, open(alvo, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"   {add} entrada(s) adicionada(s)" + (f", {dup} já existia(m)" if dup else ""))
print(f"   eventos: {', '.join(novo.get('hooks', {}))}")
PY
else diz "   [dry-run] fundiria 'hooks' + permissions.deny/ask"; fi
diz ""

# ── 5. .gitignore ────────────────────────────────────────────────────────────
if [ "$DRY" -eq 0 ]; then
  GI="$DESTINO/.gitignore"
  for linha in ".trava/chave.secreta" ".trava/selos/" ".trava/contadores/" \
               ".trava/forense/" ".trava/bancada/" "evidencias/"; do
    grep -qxF "$linha" "$GI" 2>/dev/null || printf '%s\n' "$linha" >> "$GI"
  done
  diz "5. .gitignore atualizado (estado e segredo fora do git; auditoria.jsonl FICA)"
  diz ""
fi

# ── 6. provar ────────────────────────────────────────────────────────────────
if [ "$DRY" -eq 0 ]; then
  diz "6. provando que as travas travam…"
  if bash "$DESTINO/.trava/bin/testar_travas.sh" "$DESTINO" > /tmp/trava-prova.txt 2>&1; then
    tail -4 /tmp/trava-prova.txt | sed 's/^/   /'
  else
    diz "   ⚠️  alguma prova falhou — veja /tmp/trava-prova.txt"
    tail -6 /tmp/trava-prova.txt | sed 's/^/   /'
  fi
  diz ""

  N=$(python3 -c "import json;print(len(json.load(open('$DESTINO/.trava/contrato.json'))['travas']))" 2>/dev/null || echo 0)
  if [ "$N" -le 1 ]; then
    diz "╔═══════════════════════════════════════════════════════════════════╗"
    diz "║  ⚠️  O contrato gerado tem apenas $N trava(s).                       ║"
    diz "║  Na prática: QUASE NENHUMA proteção no dia a dia. O agente vai    ║"
    diz "║  trabalhar normalmente e pouca coisa será bloqueada.              ║"
    diz "║  A trava de ENTREGA (bancada humana) está ativa — essa é a que    ║"
    diz "║  importa. Para o resto, edite .trava/contrato.json.               ║"
    diz "╚═══════════════════════════════════════════════════════════════════╝"
    diz ""
  fi

  diz "═══ FALTA UM PASSO, E SÓ VOCÊ PODE DAR:"
  diz "    REINICIE A SESSÃO do agente neste projeto."
  diz "    Hooks são capturados no início da sessão; até lá, nada está ativo."
  diz ""
  diz "    Depois:  ./trava status     o que está imposto"
  diz "             ./trava doutor     está viva ou é enfeite?"
  diz "             /trava-status      o mesmo, de dentro do agente"
  diz ""
  diz "    Leia:    CONTRATO-DE-ENTREGA.md"
fi
