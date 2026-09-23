# 01 — O mecanismo: hooks do Claude Code (referência técnica)

Este é o documento que não pode ser parafraseado com aproximações. Nomes de evento,
nomes de campo e códigos de saída são **contrato literal** com o runtime. Errar uma
maiúscula desliga a trava — silenciosamente, o que é o pior modo de falha possível.

---

## 1. O que é um hook, mecanicamente

Um hook é um **comando de shell** que o runtime do Claude Code executa em momentos
definidos do ciclo de vida da sessão.

```
            ┌──────────────────────────────────────────────┐
            │  runtime (Claude Code)                        │
            │                                               │
  modelo ──▶│  quer chamar Bash(rm -rf build)               │
            │        │                                      │
            │        ▼                                      │
            │  [ evento PreToolUse ]                        │
            │        │  escreve JSON no stdin do hook       │
            │        ▼                                      │
            │   $ python3 .claude/hooks/trava_gate.py  ◀────┼──── SEU CÓDIGO
            │        │  lê stdin, decide, responde          │
            │        ▼                                      │
            │   exit 2  /  {"permissionDecision":"deny"}    │
            │        │                                      │
            │        ▼                                      │
            │   CHAMADA CANCELADA. Bash nunca roda.         │
            │   modelo recebe o motivo como resultado.      │
            └──────────────────────────────────────────────┘
```

Três propriedades que fazem disso uma trava e não um conselho:

1. **Execução não-opcional.** O runtime executa o hook. O modelo não pode pular, não
   precisa lembrar, não sabe sequer que existe (até bater nele).
2. **Processo separado.** O hook é um programa com acesso total ao disco, à rede, a
   qualquer verificador. Ele *roda testes de verdade*, não avalia texto.
3. **Veredito vinculante.** O runtime cancela a chamada. Não é um aviso que o modelo
   "considera" — a ferramenta não executa.

> **Cobertura de sub-agentes:** hooks são configurados **por sessão**, e a sessão inclui
> as sidechains dos sub-agentes disparados via `Task`. Uma chamada de `Bash` feita por um
> sub-agente dispara `PreToolUse` exatamente como a do agente principal. É por isso que
> hook trava sub-agente e prompt não trava.

---

## 2. Os eventos

| Evento | Quando dispara | Pode bloquear? | O que bloquear significa |
|---|---|---|---|
| `PreToolUse` | antes de executar uma ferramenta | ✅ **sim** | a ferramenta não roda |
| `PostToolUse` | depois de a ferramenta retornar | ⚠️ parcial | já rodou; devolve erro ao modelo para ele corrigir |
| `UserPromptSubmit` | quando o usuário envia prompt, antes do modelo ver | ✅ sim | o prompt é descartado; também permite **injetar contexto** |
| `Stop` | quando o agente **principal** vai encerrar o turno | ✅ **sim** | o agente é obrigado a continuar trabalhando |
| `SubagentStop` | quando um **sub-agente** (`Task`) vai encerrar | ✅ **sim** | o sub-agente é obrigado a continuar |
| `SessionStart` | início/retomada de sessão | ❌ não | injeta contexto inicial (bom para publicar o contrato) |
| `SessionEnd` | fim de sessão | ❌ não | limpeza, arquivamento da auditoria |
| `PreCompact` | antes de compactar o contexto | ❌ não | momento de persistir estado que sumiria |
| `Notification` | quando o runtime notifica o usuário | ❌ não | integrações externas |

As travas vivem em **três** desses: `PreToolUse` (impedir), `SubagentStop`/`Stop`
(exigir conclusão), `PostToolUse` (reagir ao consumado). Os demais são apoio.

---

## 3. Entrada: o JSON que chega no stdin

Todo hook recebe **um objeto JSON no stdin**. Campos comuns a todos os eventos:

```json
{
  "session_id":      "ab12…",
  "transcript_path": "/home/user/.claude/projects/<slug>/<session>.jsonl",
  "cwd":             "/home/user/projetos/app",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse"
}
```

`permission_mode` é um de: `default`, `acceptEdits`, `plan`, `bypassPermissions`.
Útil para endurecer travas quando a sessão está em `bypassPermissions`.

### Campos adicionais por evento

**`PreToolUse`**
```json
{
  "hook_event_name": "PreToolUse",
  "tool_name":  "Bash",
  "tool_input": { "command": "rm -rf build", "description": "limpa build" }
}
```

**`PostToolUse`** — igual ao acima, mais:
```json
{ "tool_response": { "stdout": "...", "stderr": "...", "interrupted": false } }
```

**`UserPromptSubmit`**
```json
{ "hook_event_name": "UserPromptSubmit", "prompt": "texto digitado pelo usuário" }
```

**`Stop` e `SubagentStop`**
```json
{ "hook_event_name": "SubagentStop", "stop_hook_active": false }
```
> ⚠️ **`stop_hook_active` é o fusível anti-loop.** Ele vem `true` quando o turno atual já
> está acontecendo *por causa* de um bloqueio anterior deste mesmo hook. Se você bloquear
> de novo sem checar, cria recursão infinita. **Sempre comece o hook de Stop com:**
> `if payload.get("stop_hook_active"): sys.exit(0)`

**`SessionStart`** — `{"source": "startup" | "resume" | "clear" | "compact"}`
**`SessionEnd`** — `{"reason": "..."}`
**`PreCompact`** — `{"trigger": "manual" | "auto", "custom_instructions": "..."}`

### O formato de `tool_input` por ferramenta

É aqui que o gate decide *o que* está sendo feito. Os campos que importam:

| Ferramenta | Campo a inspecionar | Exemplo |
|---|---|---|
| `Bash` | `command` | `"git push origin main"` |
| `Write` | `file_path`, `content` | `"/app/src/db.py"` |
| `Edit` | `file_path`, `old_string`, `new_string` | |
| `Read` | `file_path` | |
| `Task` | `subagent_type`, `description`, `prompt` | disparo de sub-agente |
| `WebFetch` | `url` | |
| `Glob` / `Grep` | `pattern`, `path` | |

---

## 4. Saída: as duas formas de dar o veredito

Existem **duas vias**, e é importante não confundi-las.

### Via A — código de saída (simples, universal)

| Código | Efeito |
|---|---|
| `0` | Sucesso. `stdout` vai para o transcript (modo verbose). Em `UserPromptSubmit` e `SessionStart`, o `stdout` é **injetado no contexto do modelo**. |
| `2` | **ERRO BLOQUEANTE.** O `stderr` é entregue ao modelo. O runtime bloqueia conforme o evento. |
| outro | Erro não-bloqueante. `stderr` vai ao usuário. A execução **continua**. |

O que `exit 2` bloqueia, por evento:

| Evento | Efeito do `exit 2` |
|---|---|
| `PreToolUse` | ferramenta **não roda**; `stderr` vai ao modelo |
| `PostToolUse` | ferramenta já rodou; `stderr` vai ao modelo (ele pode corrigir) |
| `UserPromptSubmit` | prompt **descartado**; `stderr` vai só ao **usuário** |
| `Stop` | encerramento **bloqueado**; `stderr` vai ao modelo |
| `SubagentStop` | encerramento do sub-agente **bloqueado**; `stderr` vai ao sub-agente |
| `SessionStart`, `SessionEnd`, `PreCompact`, `Notification` | não bloqueia; `stderr` ao usuário |

Forma mínima de uma trava funcional — isto **já é** uma trava real:

```bash
#!/usr/bin/env bash
payload=$(cat)
cmd=$(printf '%s' "$payload" | jq -r '.tool_input.command // ""')
if [[ "$cmd" == *"git push"* ]] && [[ ! -f .trava/selos/testes-verdes.json ]]; then
  echo "BLOQUEADO: push exige o selo 'testes-verdes'. Emita com: ./trava selo emitir testes-verdes" >&2
  exit 2
fi
exit 0
```

### Via B — JSON estruturado no stdout (preciso, com mais controle)

Sai com **código 0** e imprime um objeto JSON. Campos comuns a todos os eventos:

```json
{
  "continue": true,
  "stopReason": "texto mostrado ao usuário quando continue=false",
  "suppressOutput": false,
  "systemMessage": "aviso exibido ao usuário"
}
```

> `"continue": false` **encerra a sessão inteira** e tem precedência sobre qualquer
> `decision`. É o freio de emergência, não a trava do dia a dia.

**`PreToolUse` — o veredito de permissão:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Falta o selo 'plano-aprovado'. Rode: ./trava selo emitir plano-aprovado"
  }
}
```
- `"allow"` — libera, **pulando o sistema de permissões**. O motivo vai ao transcript.
- `"deny"` — cancela a chamada. O motivo vai **ao modelo**. ← esta é a trava.
- `"ask"` — devolve ao usuário para confirmação manual. Meio-termo excelente para ações
  caras ou irreversíveis onde você quer um humano no laço em vez de um `no` absoluto.

**`PostToolUse`:**
```json
{
  "decision": "block",
  "reason": "O arquivo gravado não passa no linter. Corrija antes de seguir.",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "saída do ruff: ..."
  }
}
```

**`UserPromptSubmit`:**
```json
{
  "decision": "block",
  "reason": "motivo mostrado ao usuário",
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "CONTRATO VIGENTE: ... (isto entra no contexto do modelo)"
  }
}
```

**`Stop` / `SubagentStop` — a trava de conclusão:**
```json
{
  "decision": "block",
  "reason": "OBRIGATÓRIO: você ainda não emitiu o selo 'relatorio'. Gere output/relatorio.md e rode ./trava selo emitir relatorio. Só então encerre."
}
```
> Em `Stop`/`SubagentStop`, `reason` é **obrigatório** quando `decision` é `block` — é o
> único texto que o agente recebe para saber como prosseguir. `reason` vazio = agente preso.

**`SessionStart`:**
```json
{ "hookSpecificOutput": { "hookEventName": "SessionStart", "additionalContext": "..." } }
```

### Qual via usar

| Situação | Via |
|---|---|
| Bloqueio simples, um script curto, qualquer linguagem | **A** — `exit 2` |
| Precisa de `allow` explícito ou de `ask` (humano no laço) | **B** — JSON |
| Precisa injetar contexto (`additionalContext`) | **B** — JSON |
| Precisa encerrar a sessão (`continue:false`) | **B** — JSON |
| Quer o texto do motivo formatado com precisão para o modelo | **B** — JSON |

Os exemplos deste repositório usam **B** para `PreToolUse` e `Stop`, porque o campo
`reason`/`permissionDecisionReason` é o canal onde se entrega a **instrução de
destravamento** — e essa instrução é o que separa uma trava de um deadlock.

---

## 5. Configuração

### Onde

| Arquivo | Escopo | Uso típico |
|---|---|---|
| `~/.claude/settings.json` | usuário, todos os projetos | travas pessoais globais |
| `<projeto>/.claude/settings.json` | projeto, versionado no git | **travas da equipe** ← o lugar certo |
| `<projeto>/.claude/settings.local.json` | projeto, não versionado | ajustes locais |
| configuração gerenciada da organização | administrada | políticas corporativas |

### Forma

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Write|Edit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/trava_gate.py\"",
            "timeout": 15
          }
        ]
      },
      {
        "matcher": "Task",
        "hooks": [
          { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/trava_gate.py\"" }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/trava_stop.py\"" }
        ]
      }
    ]
  }
}
```

Regras do `matcher`:
- É comparado com o **nome da ferramenta**, e aceita **regex**: `"Write|Edit"`, `"Notebook.*"`.
- É **sensível a maiúsculas**. `"bash"` não casa com `Bash`. Este é o erro nº 1.
- `"*"` (ou omitir) casa com todas as ferramentas.
- Eventos sem ferramenta (`UserPromptSubmit`, `Stop`, `SubagentStop`, `SessionStart`,
  `SessionEnd`, `PreCompact`) **não usam** `matcher` — omita o campo.
- **Todos** os grupos cujo matcher casa executam, e os hooks de um grupo rodam **em
  paralelo**. Não presuma ordem entre hooks.
- Se qualquer hook bloquear, a ação é bloqueada. Bloqueio é OR, não consenso.

### Ambiente do hook

- `$CLAUDE_PROJECT_DIR` — caminho absoluto da raiz do projeto. **Use sempre**, porque o
  `cwd` do hook não é garantido. Coloque entre aspas: caminhos têm espaços.
- `timeout` — segundos; padrão 60. Um hook lento trava a sessão inteira; mantenha o
  caminho rápido rápido (ver §7).
- O comando roda no shell do sistema, com as credenciais do usuário. **Um hook é código
  executando na sua máquina a cada chamada de ferramenta.** Revise o que instala.

### Ativação

Hooks são **capturados no início da sessão**. Editar `settings.json` com a sessão aberta
não liga a trava na hora — isso é proposital (evita que um agente com acesso a disco
reescreva as próprias travas no meio do caminho). Depois de editar:

1. Revise em `/hooks` (menu interativo), **e**
2. **Reinicie a sessão.**

Depois, valide de verdade com [08-provar-que-trava.md](08-provar-que-trava.md).
Nunca presuma que ligou.

---

## 6. Distinguir agente principal de sub-agente

Pergunta inevitável ao travar sub-agentes. A resposta honesta, em três partes:

**(a) `SubagentStop` é confiável.** Só dispara para sub-agentes. Se a trava é sobre a
*conclusão* de um sub-agente, use este evento e pronto — não há ambiguidade.

**(b) `PreToolUse` no `Task` é confiável e é o melhor ponto de controle.** Quando o agente
principal dispara um sub-agente, o runtime chama a ferramenta `Task`. Seu gate vê:
```json
{ "tool_name": "Task",
  "tool_input": { "subagent_type": "general-purpose", "description": "...", "prompt": "..." } }
```
Você pode **barrar o nascimento** do sub-agente (pré-condições não atendidas, tipo de
agente não autorizado, prompt sem a cláusula de contrato) — que é mais forte do que tentar
policiar o sub-agente depois.

**(c) Em `PreToolUse` genérico, NÃO há campo documentado dizendo "isto veio de um
sub-agente".** Existe a heurística de ler o `transcript_path` e procurar marcadores de
sidechain na última entrada — **é frágil**, depende de formato interno, e pode quebrar
numa atualização.

**A recomendação é não precisar dessa distinção.** Projete a trava sobre **o que está
sendo feito e qual é o estado**, não sobre **quem está fazendo**:

> ❌ "sub-agentes não podem dar push"
> ✅ "ninguém dá push sem o selo `testes-verdes`"

A segunda é mais simples, mais forte, e cobre os dois casos sem heurística. Quando a
identidade importa de verdade, marque-a explicitamente **no nascimento** (o gate do `Task`
grava `.trava/contexto/<id>.json` com o perfil daquele sub-agente) em vez de tentar
adivinhá-la depois. Ver [03-travas-de-subagente.md](03-travas-de-subagente.md) §4.

---

## 7. Regras de engenharia para hooks

1. **Falhe aberto ou falhe fechado — mas escolha, e documente.**
   Um hook que estoura exceção sai com código ≠ 0/2 → **não bloqueia**. Para travas de
   segurança, envolva tudo num `try/except` que **bloqueia** em caso de erro interno.
   Para travas de fluxo, deixe passar e registre no log. Decida por trava, não por acidente.

2. **Seja rápido no caminho comum.** O hook roda a cada chamada. Cheque primeiro o campo
   barato (`tool_name`, regex do comando) e só depois rode o verificador caro. Verificação
   pesada vira selo emitido *uma vez*, não re-execução a cada chamada.

3. **Nunca escreva no stdout sem necessidade.** Em `PreToolUse`, stdout **é parseado como
   JSON de veredito**. Um `print()` de debug perdido corrompe o veredito. Debug vai para
   `stderr` ou para arquivo de log.

4. **Toda negação carrega a receita de destravamento.** `reason` deve conter o comando
   literal que resolve. Sem isso o agente tenta variações às cegas → loop.

5. **Registre tudo.** Um JSONL append-only em `.trava/auditoria.jsonl` com
   `{ts, evento, ferramenta, decisao, trava, motivo}`. Sem auditoria você não sabe se a
   trava disparou, nem por quê — e não consegue distinguir "não bloqueou" de "nem rodou".

6. **Aspas nos caminhos.** `"$CLAUDE_PROJECT_DIR/.claude/hooks/x.py"`. Sempre.

7. **Determinismo.** O mesmo estado deve produzir o mesmo veredito. Nada de aleatoriedade,
   nada de rede num gate síncrono, nada de depender de relógio exceto por TTL explícito.

8. **Teste antes de confiar.** [08-provar-que-trava.md](08-provar-que-trava.md).

---

Próximo: [02-anatomia-da-trava.md](02-anatomia-da-trava.md) — como projetar uma trava do zero.
