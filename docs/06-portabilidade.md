# 06 — Portabilidade: usar este mecanismo sem hooks

Este documento é para quem lê o repositório rodando em **outro runtime**: um agente sem
hooks, uma automação caseira, um framework diferente, um humano seguindo um processo.

A tese: **hooks são um detalhe de implementação, não o mecanismo.** O mecanismo é

> **estado externo + verificador determinístico + ponto de passagem obrigatório**

Hooks são apenas o ponto de passagem mais conveniente *quando existem*. Trocar o ponto de
passagem preserva a trava; os outros dois componentes são idênticos em qualquer ambiente.

---

## 1. Separar o que é portátil do que não é

```
┌─────────────────────────────────────────────────────────┐
│  PORTÁTIL — funciona em qualquer lugar, sem alteração   │
│  ─────────────────────────────────────────────────────  │
│  .trava/contrato.json     a declaração das travas       │
│  .trava/selos/*.json      as provas assinadas           │
│  lib_trava.py             selos, HMAC, contadores       │
│  trava (CLI)              emitir / conferir / bancada / auditoria   │
│  a disciplina de projeto  os 6 órgãos (docs/02)         │
├─────────────────────────────────────────────────────────┤
│  ESPECÍFICO DO CLAUDE CODE — precisa de substituto      │
│  ─────────────────────────────────────────────────────  │
│  settings.json "hooks"    o registro do ponto de passagem│
│  o payload JSON no stdin  o formato de entrada          │
│  permissionDecision/exit 2 o formato do veredito        │
└─────────────────────────────────────────────────────────┘
```

Cerca de 80% do mecanismo atravessa sem modificação. O que muda é **onde você pendura o
verificador** e **como o "não" é expresso**.

`./trava selo` foi escrito com isso em mente: `./trava selo conferir <nome>` sai com **0 ou 1**.
Código de saída é a interface universal. Qualquer coisa que entenda código de saída —
shell, Make, CI, git hook, wrapper — consegue usar a trava sem saber o que é um hook.

---

## 2. A escada de degradação

Perca o degrau de cima, desça um. Cada degrau ainda é uma trava real até N2.

### N3 — Claude Code (original)
```json
"PreToolUse": [{ "matcher": "Bash",
  "hooks": [{"type":"command","command":"python3 .claude/hooks/trava_gate.py"}] }]
```

### N3' — Outro runtime com interceptação
Muitos frameworks têm um callback antes da execução de ferramenta. Os nomes mudam
(`before_tool_call`, middleware, `on_action`, política de ferramenta); a forma não:

```python
def antes_da_ferramenta(nome, argumentos):
    if nome == "shell" and "git push" in argumentos.get("command", ""):
        ok, motivo = conferir_selo("testes-verdes", estrito=True)
        if not ok:
            raise PermissionError(              # ou: return Deny(motivo)
                f"BLOQUEADO: {motivo}. Rode: ./trava selo emitir testes-verdes"
            )
```

**Reaproveite `lib_trava.py` inteiro.** Só o veredito muda de forma:

| Runtime | Como dizer "não" |
|---|---|
| Claude Code | `exit 2` ou `permissionDecision: "deny"` |
| Callback Python | `raise PermissionError(motivo)` |
| Middleware que retorna | `return {"allow": False, "reason": motivo}` |
| Executor de ferramenta próprio | devolver o motivo como **resultado da ferramenta** |

> A última linha é a mais importante para quem tem um loop próprio: se você não consegue
> abortar, **execute uma no-op e devolva o texto do bloqueio como se fosse a saída da
> ferramenta**. Do ponto de vista do modelo é indistinguível de um bloqueio real: ele
> pediu, não aconteceu, e recebeu o motivo. A ação não ocorreu — que é a definição.

### N2 — Caminho único instrumentado (sem interceptação nenhuma)

Este degrau é o coração da portabilidade e funciona **sempre**, inclusive com um agente
que só tem shell.

Você não intercepta a ação: você **elimina o acesso direto a ela** e publica um único
caminho, que verifica antes.

```bash
#!/usr/bin/env bash
# bin/entregar — o ÚNICO jeito autorizado de publicar
set -euo pipefail

./trava selo conferir testes-verdes --estrito || {
  cat >&2 <<'MSG'
BLOQUEADO: a suíte de testes não passa neste instante.
Para destravar:  ./trava selo emitir testes-verdes
Se os testes não puderem passar, NÃO contorne: relate qual teste falha e pare.
MSG
  exit 1
}

git push origin "$(git rev-parse --abbrev-ref HEAD)"
```

Para fechar o caminho direto, combine com o que o ambiente oferecer:
`permissions.deny` do runtime, remoto git sem permissão para o usuário do agente,
`--network none` no container, token ausente ([05](05-travas-sem-hook.md) §3).

A mesma ideia em `Makefile` — ótimo porque agentes tendem a preferir alvos declarados:

```makefile
.PHONY: verificar entregar
verificar:
	./trava selo emitir testes-verdes
	./trava selo emitir lint-limpo

entregar: ## só roda se os selos existirem e forem válidos agora
	@./trava selo conferir testes-verdes --estrito
	@./trava selo conferir lint-limpo    --estrito
	./scripts/deploy.sh
```

### N2' — Trava no lado do servidor
Branch protegida, required status checks, aprovação obrigatória no PR, política de deploy.
Não importa qual agente, qual runtime, qual máquina: o servidor recusa. É N2 com a força
de N4 porque está fora do alcance do agente.

### N1 — Protocolo com evidência
Quando não há **nada** programável (agente com acesso só a chat, por exemplo):

```
Ao concluir cada etapa, cole no relatório a saída LITERAL de:
    ./trava selo listar
A etapa não é aceita sem esse bloco. Um revisor confere antes da próxima etapa.
```

Não é trava (o agente poderia fabricar o texto), mas converte **falha silenciosa em falha
detectável**, que é o ganho decisivo sobre N0. E se o revisor for outro agente com acesso
ao disco, você recuperou N2.

### N0 — Só a frase
Último recurso. Ver [00-tese.md](00-tese.md) §1 sobre por que ela falha — e use-a sempre
**junto** com um degrau superior, nunca sozinha.

---

## 3. Protocolo mínimo de reuso (para um agente sem nenhum mecanismo)

Se você é um agente lendo isto e **não tem** hooks, interceptação nem wrapper, este é o
maior nível honesto que você consegue atingir sozinho — N1 forte. Siga literalmente:

1. **Não confie na sua própria afirmação.** Você não sabe se rodou os testes; você sabe
   que disse que rodou. Só conta o que tiver saída de comando.

2. **Materialize o estado.** Antes de cada etapa, escreva em disco o que ela exige:
   ```bash
   mkdir -p .trava/selos
   ```
   Se você tem `lib_trava.py` e `./trava selo`, copie-os e use-os: eles não dependem de hooks.
   ```bash
   python3 ./trava selo emitir testes-verdes --comando "python3 -m pytest -q"
   ```

3. **Confira antes de cada ação perigosa**, e trate o código de saída como veredito:
   ```bash
   python3 ./trava selo conferir testes-verdes --estrito || echo "BLOQUEADO — não prossiga"
   ```

4. **Declare o bloqueio em voz alta e pare.** Não é "vou tentar de outro jeito". É:
   > "A trava `sem-push-sem-teste` não está satisfeita: `pytest` retorna 1 em
   > `tests/test_auth.py::test_refresh`. Não vou dar push. Preciso de decisão."

5. **Nunca contorne uma trava que você mesmo poderia desligar.** Você tem acesso a
   `.trava/` e aos scripts. Um agente que apaga a própria trava para concluir a tarefa
   falhou na tarefa — o objetivo nunca foi "chegar ao fim", foi "chegar ao fim
   corretamente". Se a trava parecer errada, **diga que parece errada** e pare.

6. **Peça a trava de verdade.** Se o ambiente permite hooks e ninguém configurou, diga:
   > "Esta regra está apenas no prompt, então ela é frágil (ver docs/00-tese.md).
   > Posso instalar a versão em hook, que bloqueia de fato? São 3 arquivos."

O item 5 é o que separa um agente confiável de um agente perigoso, e é o único item desta
lista que nenhum mecanismo consegue impor — porque um agente com acesso ao disco sempre
pode desligar o que é software. **Por isso ele está escrito aqui, e não num hook.**

---

## 4. Transportando o contrato

`.trava/contrato.json` é o artefato mais portátil deste repositório: é declaração pura,
sem código. Um agente em outro runtime lê o mesmo arquivo e sabe exatamente:

- o que está travado (`travas[].quando`)
- o que destrava (`travas[].exige_selos` + `verificacoes[].comando`)
- o que é exigido na entrega (`saida_subagente`)
- o que invalida provas (`pos_acao.selos_volateis`)

Um leitor genérico, em qualquer linguagem, precisa apenas de:

```python
contrato = json.load(open(".trava/contrato.json"))
for regra in contrato["travas"]:
    if minha_acao_casa(regra["quando"]):
        for selo in regra.get("exige_selos", []):
            if not conferir(selo):
                bloquear(regra.get("mensagem"), regra.get("como_destravar"))
```

O contrato é a interface. Os hooks são uma implementação dela. Escreva mais contratos e
menos hooks, e o seu trabalho sobrevive à troca de runtime.
