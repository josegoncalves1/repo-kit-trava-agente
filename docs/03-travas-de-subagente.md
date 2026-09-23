# 03 — Travas de sub-agente

O caso que motiva este repositório. Um sub-agente é um processo de modelo que **nasce sem
a sua conversa**: ele recebe um prompt de tarefa, um toolset, e vai. Tudo que você
combinou com o agente principal — o plano, as restrições, os avisos — ele não viu.

Por isso o sub-agente é o ponto onde travas retóricas falham de forma mais previsível,
e onde travas de runtime valem mais.

---

## 1. Os quatro pontos de controle

Um sub-agente tem exatamente quatro momentos interceptáveis. Cada um tem uma trava própria.

```
   (A) NASCIMENTO          PreToolUse  matcher "Task"
        │                  ── barrar o disparo, exigir pré-condições, injetar contrato
        ▼
   (B) DURANTE             PreToolUse  matcher da ferramenta que ele usa
        │                  ── mesmas travas do principal; hooks valem na sessão inteira
        ▼
   (C) EFEITO CONSUMADO    PostToolUse
        │                  ── detectar estrago e devolver a tarefa
        ▼
   (D) CONCLUSÃO           SubagentStop
                           ── exigir prova antes de aceitar que acabou
```

**A ordem de importância é (A) > (D) > (B) > (C).** Controlar o nascimento e a conclusão
resolve a maior parte dos problemas, com menos código e menos risco de loop.

---

## 2. (A) Trava de nascimento — `PreToolUse` + `Task`

Quando o agente principal dispara um sub-agente, isso é uma chamada de ferramenta comum,
e o gate a vê inteira:

```json
{
  "hook_event_name": "PreToolUse",
  "tool_name": "Task",
  "tool_input": {
    "subagent_type": "general-purpose",
    "description": "Refatorar camada de auth",
    "prompt": "Você vai refatorar ... (texto integral da tarefa)"
  }
}
```

Isso permite quatro travas que nenhuma instrução de prompt consegue:

### A.1 — Pré-condição de fase
> *"Nenhum sub-agente é disparado antes de o plano estar aprovado."*

```python
if tool_name == "Task" and not selo_valido("plano-aprovado"):
    deny("Sub-agentes bloqueados nesta fase. O plano precisa do selo 'plano-aprovado'. "
         "Apresente o plano ao usuário e rode: ./trava selo emitir plano-aprovado")
```

### A.2 — Lista branca de tipos
> *"Nesta fase só rodam sub-agentes `Explore` (leitura); nada que escreva."*

```python
permitidos = contrato["fase_atual"]["subagentes_permitidos"]   # ["Explore"]
if tool_name == "Task" and tool_input.get("subagent_type") not in permitidos:
    deny(f"subagent_type '{tipo}' não autorizado na fase atual. Permitidos: {permitidos}.")
```

### A.3 — Inspeção do prompt da tarefa
> *"Nenhum sub-agente nasce sem o bloco de contrato no prompt."*

Uma trava real cuja consequência é **injetar N0 corretamente**: como você não consegue
editar o prompt do filho pelo hook, você **exige** que o pai o escreva certo — e barra
enquanto ele não escrever.

```python
if tool_name == "Task" and "## CONTRATO DE EXECUÇÃO" not in tool_input.get("prompt", ""):
    deny("O prompt do sub-agente precisa conter o bloco '## CONTRATO DE EXECUÇÃO'. "
         "Copie o texto de .trava/bloco-contrato.md para o início do prompt e chame de novo.")
```

Esse é o padrão que resolve o problema de herança: o sub-agente passa a nascer **já
sabendo** por que vai ser bloqueado e como destravar, o que elimina o loop de tentativa.

### A.4 — Orçamento de fan-out
> *"No máximo 3 sub-agentes por fase."*

```python
n = contar_e_incrementar(".trava/contadores/task_fase.json")
if n > contrato["fase_atual"]["max_subagentes"]:
    deny(f"Orçamento de sub-agentes da fase esgotado ({n-1} já disparados). "
         "Consolide os resultados existentes antes de disparar mais, ou peça ao usuário.")
```

Trava contra explosão de custo — um modo de falha que nenhuma instrução em prompt contém
de maneira confiável.

---

## 3. (D) Trava de conclusão — `SubagentStop`

A mais valiosa das quatro, e a mais perigosa se mal feita.

**O que ela faz:** quando o sub-agente considera a tarefa terminada e vai encerrar, o
runtime chama seu hook. Se você responder `{"decision":"block","reason":"..."}`, o
sub-agente **não encerra** — ele recebe o `reason` e continua trabalhando.

Isso elimina a classe inteira de falha "entreguei pela metade e declarei sucesso":

```python
#!/usr/bin/env python3
import json, sys

p = json.load(sys.stdin)

# FUSÍVEL — sem isto, loop infinito. Não é opcional.
if p.get("stop_hook_active"):
    sys.exit(0)

faltando = [s for s in ["relatorio", "testes-verdes"] if not selo_valido(s)]

if faltando:
    n = incrementar_contador(p["session_id"])
    if n > 3:
        # VÁLVULA: cede e escala, em vez de prender
        print(json.dumps({"systemMessage":
            f"Trava de conclusão cedida após {n} tentativas; selos ausentes: {faltando}"}))
        sys.exit(0)
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"TAREFA INCOMPLETA (tentativa {n}/3). Selos ausentes: {', '.join(faltando)}.\n"
            "Para cada um:\n"
            "  relatorio      -> escreva output/relatorio.md e rode: ./trava selo emitir relatorio\n"
            "  testes-verdes  -> rode: ./trava selo emitir testes-verdes (executa pytest -q)\n"
            "Se algum for impossível, NÃO contorne: escreva o impedimento em "
            "output/relatorio.md, emita o selo 'relatorio' e encerre."
        )
    }))
    sys.exit(0)

sys.exit(0)  # tudo provado: pode encerrar
```

Note os três órgãos de segurança operando juntos: **fusível** (`stop_hook_active`),
**contador** (`n > 3`), e **saída honrosa** (relatar o impedimento também destrava).
Sem os três, você construiu uma armadilha, não uma trava.

### `Stop` vs `SubagentStop`

Idênticos em mecânica. `Stop` é o turno do agente principal — bloquear ali é muito mais
intrusivo (impede o agente de responder ao usuário) e deve ser raro e com limite baixo.
`SubagentStop` é o lugar natural para exigência de entrega.

---

## 4. Quem é quem: marcar no nascimento em vez de adivinhar depois

Não existe campo documentado em `PreToolUse` que diga "esta chamada veio de um
sub-agente". A tentação é ler o `transcript_path` e procurar marcadores internos de
sidechain — **não faça isso como base de uma trava**: é formato interno, não contrato,
e quebra sem aviso.

**A solução correta é marcar no nascimento.** O gate, ao liberar um `Task`, grava o perfil:

```python
if tool_name == "Task":
    perfil = {
        "tipo": tool_input.get("subagent_type"),
        "descricao": tool_input.get("description"),
        "disparado_em": int(time.time()),
        "sessao_pai": payload["session_id"],
        "restricoes": contrato["perfis"].get(tool_input.get("subagent_type"), {}),
    }
    Path(".trava/contexto/ultimo_task.json").write_text(json.dumps(perfil))
```

E **prefira não precisar disso**. Repetindo a regra de [01](01-mecanismo-hooks.md) §6:

> Trave **o que é feito + qual o estado**, não **quem faz**.
> ❌ "sub-agente não pode dar push" → ✅ "ninguém dá push sem selo `testes-verdes`"

A segunda formulação é mais curta, mais forte, cobre os dois atores, e não depende de
nenhuma heurística que possa quebrar.

---

## 5. Toolset restrito: a trava N4 de sub-agente

Antes de escrever qualquer hook, pergunte: **o sub-agente precisa mesmo dessa ferramenta?**

A trava mais forte que existe para sub-agente não é um hook — é a definição do agente em
`.claude/agents/<nome>.md`:

```markdown
---
name: auditor
description: Audita o código e produz um relatório. NÃO modifica nada.
tools: Read, Grep, Glob
model: sonnet
---

Você audita. Você não corrige. Produza output/auditoria.md.
```

Esse sub-agente **não tem** `Write`, **não tem** `Edit`, **não tem** `Bash`. Nenhum hook
precisa impedi-lo de escrever: escrever não está no vocabulário dele. Nada para lembrar,
nada para verificar, nada para contornar. Ver [05-travas-sem-hook.md](05-travas-sem-hook.md).

> **Regra de projeto:** toda restrição que puder ser expressa como *ausência de ferramenta*
> deve ser expressa assim. Use hooks para o que sobrar — ou seja, para condições que
> dependem de **estado** (ordem, prova, prazo), não de **capacidade**.

---

## 6. Desenho completo de referência

Uma pipeline de 3 fases com sub-agentes travados, combinando tudo:

```
FASE 1 — EXPLORAÇÃO
  N4: sub-agentes do tipo Explore (tools: Read, Grep, Glob) — não podem escrever
  N3: PreToolUse/Task  → subagent_type deve estar em ["Explore"]
  N3: SubagentStop     → exige selo "mapa" (arquivo output/mapa.md existe e tem >200 bytes)
  saída: selo "exploracao-concluida"

FASE 2 — PLANO
  N3: PreToolUse/Write|Edit → deny: "fase de plano não escreve código"
  humano: aprova o plano
  N3: PreToolUse/Task       → deny enquanto não houver selo "exploracao-concluida"
  saída: selo "plano-aprovado"  (emitido só após confirmação do usuário)

FASE 3 — EXECUÇÃO
  N3: PreToolUse/Task       → deny enquanto não houver selo "plano-aprovado"
  N3: PreToolUse/Task       → deny se prompt não contiver "## CONTRATO DE EXECUÇÃO"
  N3: PreToolUse/Task       → deny se já houver 3 sub-agentes nesta fase
  N3: PreToolUse/Bash       → deny em "git push|git commit" sem selo "testes-verdes"
  N4: permissions.deny      → Bash(rm -rf:*), Read(./.env), WebFetch
  N3: SubagentStop          → exige selos "relatorio" e "testes-verdes", max 3 reentradas
```

O contrato equivalente em JSON está em
[../payload/.trava/contrato.exemplo.json](../payload/.trava/contrato.exemplo.json),
e os hooks que o interpretam estão em [../payload/.claude/hooks/](../payload/.claude/hooks/).

---

Próximo: [04-receitas.md](04-receitas.md) — travas prontas.
