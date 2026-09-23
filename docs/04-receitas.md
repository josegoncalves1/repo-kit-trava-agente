# 04 — Receitas: travas prontas

Dez travas com os 6 órgãos preenchidos. Todas funcionam com os hooks de
[../payload/.claude/hooks/](../payload/.claude/hooks/) — a maioria só precisa de uma entrada em
`.trava/contrato.json`, sem escrever código.

---

## R1 — Nada de código antes do plano aprovado

**Problema:** o agente começa a editar arquivos enquanto ainda está entendendo o problema.

```json
{
  "id": "sem-codigo-sem-plano",
  "quando": { "ferramentas": ["Write", "Edit", "NotebookEdit"],
              "regex_excecao": "^(docs/|output/|README)" },
  "exige_selos": ["plano-aprovado"],
  "veredito": "deny",
  "como_destravar": ["./trava selo emitir plano-aprovado"]
}
```
```json
"plano-aprovado": {
  "comando": "test -s docs/PLANO.md && grep -q '^## APROVADO POR:' docs/PLANO.md",
  "ttl": 86400
}
```

O detalhe que faz funcionar: a verificação exige uma **linha de aprovação** no arquivo.
O agente não consegue emitir o selo sozinho de forma honesta — a linha vem depois que o
usuário aprova. E a exceção por regex mantém `docs/` liberado, senão o agente não
conseguiria nem escrever o plano. **Toda trava precisa deixar aberto o caminho que leva
à própria liberação.**

---

## R2 — Nada de push/commit sem verde, recalculado na hora

```json
{
  "id": "sem-push-sem-teste",
  "quando": { "ferramentas": ["Bash"], "regex_alvo": "git\\s+(push|commit)" },
  "exige_selos": ["testes-verdes", "lint-limpo"],
  "estrito": true,
  "veredito": "deny",
  "como_destravar": ["./trava selo emitir testes-verdes"]
}
```

`"estrito": true` liga o verificador V3: o gate **re-executa** `pytest` naquele instante e
ignora o que o selo afirma. Um selo de 20 minutos atrás, sobre código que mudou desde
então, não passa. Combine com `selos_volateis` (R9) e você tem cinto e suspensório.

> **Cubra as rotas alternativas.** `regex_alvo` acima pega `git push` e `git commit`, mas
> não `gh pr merge`, `git-push`, nem `eval "$(echo Z2l0IHB1c2g=|base64 -d)"`. Para
> ações realmente críticas, combine com `permissions.deny` (N4) — regex sobre string de
> comando é uma defesa de superfície, não de profundidade.

---

## R3 — Sub-agente não nasce antes da hora

```json
{
  "id": "subagente-so-depois-do-plano",
  "quando": { "ferramentas": ["Task"] },
  "exige_selos": ["plano-aprovado"],
  "veredito": "deny"
}
```

Controla o **nascimento**, não o comportamento. Mais barato e mais confiável do que
tentar policiar N sub-agentes já em execução.

---

## R4 — Sub-agente não nasce sem o contrato no prompt

```json
{
  "id": "subagente-nasce-com-contrato",
  "quando": { "ferramentas": ["Task"] },
  "exige_trecho_no_alvo": ["## CONTRATO DE EXECUÇÃO"],
  "veredito": "deny",
  "como_destravar": ["cat .trava/bloco-contrato.md  # cole no início do prompt"]
}
```

A trava que conserta a **herança quebrada**. Um hook não consegue editar o prompt do
filho, mas consegue **recusar o disparo** até o pai escrever o prompt direito. O filho
passa a nascer sabendo quais travas existem e como destravá-las — e isso elimina o loop
de tentativa às cegas, que é o custo real de travas sem comunicação.

Texto pronto: [`.trava/bloco-contrato.md`](../payload/.trava/bloco-contrato.md).
Um sub-agente que já nasce com ele: [`trava-executor.md`](../payload/.claude/agents/trava-executor.md).

---

## R5 — Sub-agente não encerra sem entregar

```json
"saida_subagente": {
  "exige_selos": ["relatorio"],
  "exige_arquivos": [{ "caminho": "output/relatorio.md", "min_bytes": 300 }],
  "max_reentradas": 3,
  "como_destravar": { "relatorio": "escreva output/relatorio.md e rode: ./trava selo emitir relatorio" },
  "saida_honrosa": "Se for impossível concluir, relate o impedimento em output/relatorio.md, emita o selo e encerre. Relatar bloqueio é sucesso; fingir conclusão é falha."
}
```

`min_bytes` é o detalhe que impede a trapaça óbvia: `touch output/relatorio.md` cria o
arquivo mas não passa nos 300 bytes. **Toda condição de existência deve ter uma condição
de substância junto.**

---

## R6 — Ação destrutiva exige humano, não proibição

```json
{
  "id": "confirmar-destrutivo",
  "quando": { "ferramentas": ["Bash"],
              "regex_alvo": "\\b(rm\\s+-rf|drop\\s+table|truncate|git\\s+reset\\s+--hard)\\b" },
  "veredito": "ask",
  "mensagem": "Explique ao usuário exatamente o que será apagado antes que ele aprove."
}
```

`ask` em vez de `deny`. Às vezes `rm -rf build/` é exatamente o certo. A trava não é
"nunca"; é "**não sozinho**". Esta é a receita mais subutilizada do conjunto.

---

## R7 — Orçamento de fan-out

```json
{
  "id": "orcamento-de-subagentes",
  "quando": { "ferramentas": ["Task"] },
  "orcamento": { "max": 3 },
  "veredito": "ask"
}
```

Trava contra custo. Nenhuma instrução em prompt contém explosão de fan-out de forma
confiável, porque o agente não tem noção do gasto acumulado. Um contador em disco tem.

---

## R8 — Endurecer sob `bypassPermissions`

```json
{
  "id": "sem-rede-em-bypass",
  "quando": { "ferramentas": ["WebFetch", "WebSearch"],
              "permission_modes": ["bypassPermissions"] },
  "veredito": "deny"
}
```

Em `bypassPermissions` não há confirmação humana em lugar nenhum — então as travas de
runtime passam a ser a **única** barreira, e devem ficar mais rígidas, não menos.
Repare que a regra **não declara condição nenhuma** — só `quando` e `veredito`. Isso é uma
**trava incondicional**: casar com o `quando` já é a condição. Use essa forma sempre que a
decisão não depender de estado, só do que está sendo feito (é o caso de R6 e de qualquer
"isto sempre pede aval humano"). `permission_modes` vem do payload, campo `permission_mode`.

---

## R9 — Prova morre quando o código muda

```json
"pos_acao": { "selos_volateis": ["testes-verdes", "lint-limpo", "arvore-limpa"] }
```

`PostToolUse` revoga esses selos a cada `Write`/`Edit`/`Bash`. Sem isso existe a janela
clássica: rodo os testes → edito → dou push com o selo antigo. **Prova de estado tem que
morrer quando o estado muda.**

---

## R10 — A trava se protege

```json
"permissions": { "deny": [
  "Edit(./.claude/hooks/**)", "Write(./.claude/hooks/**)",
  "Edit(./.claude/settings.json)", "Write(./.claude/settings.json)",
  "Edit(./.trava/**)", "Write(./.trava/**)",
  "Read(./.trava/chave.secreta)"
]}
```

Camada N4, sem hook. Sem ela, todo o sistema N3 é **auto-editável**: o agente bloqueado
abre `trava_gate.py` e remove a regra.

Limite honesto: isso cobre as ferramentas `Edit`/`Write`/`Read`. **Não** cobre
`Bash(cat > .claude/hooks/trava_gate.py)`. Cobertura completa exige negar também as
formas de escrita via shell, ou montar o diretório somente-leitura para o usuário que
roda o agente. Ver [05-travas-sem-hook.md](05-travas-sem-hook.md) §4.

---

## Tabela de escolha rápida

| Sintoma observado | Receita |
|---|---|
| "ele começou a codar antes de planejar" | R1 |
| "deu push com teste vermelho" | R2 + R9 |
| "disparou 8 sub-agentes e estourou o custo" | R7 |
| "o sub-agente não sabia das regras" | R4 |
| "entregou pela metade dizendo que terminou" | R5 |
| "apagou coisa que eu precisava" | R6 + `permissions.deny` |
| "rodou os testes, editou, e deu push" | R9 |
| "editou o próprio hook para se liberar" | R10 |
| "em bypass ele faz qualquer coisa" | R8 |
| "ficou preso em loop batendo na trava" | [07-antipadroes.md](07-antipadroes.md) |
