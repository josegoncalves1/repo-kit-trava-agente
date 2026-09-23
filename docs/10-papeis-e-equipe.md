# 10 — Papéis e equipe: o fiscal nunca é o executor

## 1. O problema

Um agente termina o trabalho e se auto-avalia. Ele é, ao mesmo tempo, réu,
advogado e juiz. O resultado é previsível e não tem nada a ver com honestidade:

> **Quem construiu a tela não consegue ver a tela. Vê a intenção.**

O botão está onde ele decidiu que estaria, então ele o encontra em 200ms e conclui
que é descobrível. O cinza `#9aa0a6` sobre branco é "sutil e elegante" para quem
escolheu. O fluxo faz sentido porque ele conhece o fluxo.

Isso não se resolve com disciplina, nem com um prompt mais enfático. Resolve-se
com **outra pessoa, ou outra sessão**.

## 2. Os quatro papéis

| Papel | Faz | **Não** faz | Ferramentas |
|---|---|---|---|
| `trava-executor` | constrói, prova por máquina | revisão, laudo | Read, Grep, Glob, Write, Edit, Bash |
| `trava-fiscal` | revisa e emite veredito com lastro | **corrigir** | Read, Grep, Glob, Bash |
| `trava-operador` | opera o produto sem ver o código | corrigir, **aprovar** | Read, Glob, Bash |
| `trava-auditor-doc` | confere docs contra o código real | escrever código | Read, Grep, Glob, Bash |

Definições completas em [`../payload/.claude/agents/`](../payload/.claude/agents/).

## 3. Como a separação é imposta — três camadas

Uma só não basta. As três juntas fecham os caminhos.

### Camada N4 — toolset (a mais forte)
```markdown
---
name: trava-fiscal
tools: Read, Grep, Glob, Bash
---
```
O fiscal **não tem** `Write` nem `Edit`. Não é proibido de corrigir: corrigir
**não existe no vocabulário dele**. Nada para lembrar, nada para verificar, nada
para contornar, nada que possa ter bug.

> **Regra de projeto:** toda restrição que puder ser expressa como *ausência de
> ferramenta* deve ser expressa assim. Hooks são para o que sobrar.

### Camada N3 — perfil no contrato
```json
"perfis": {
  "trava-fiscal": {
    "proibido_escrever": ["\\.(ts|tsx|js|py|go|rs|css|html)$"],
    "mensagem": "Fiscal aponta, não conserta. Se corrigir, vira executor do próprio laudo."
  }
}
```
Cobre a rota alternativa que o toolset não cobre: um fiscal **com** `Bash` poderia
escrever com `cat > arquivo`. O gate inspeciona a linha de comando também.

### Camada N3' — papel DERIVADO do ledger (a que não se engana)

As duas camadas acima dependem de o sub-agente ter sido despachado com o tipo
certo. Esta não depende de nada declarado:

```python
# lib_trava.py — toda escrita em arquivo de produto é gravada, com a sessão
def registrar_escrita_de_produto(sessao, caminho): ...

# e a pergunta é respondida pelo histórico, não pela intenção
def conflito_de_papel(sessao_fiscal):
    if sessao_fiscal in sessoes_executoras():
        return f"a sessão '{sessao_fiscal}' escreveu {arquivos} e é EXECUTORA."
```

> **O papel não é declarado. É derivado do que a sessão fez.**

Um agente pode escrever `papel: fiscal` num arquivo. Ele **não pode** fazer com
que o ledger não contenha as escritas que ele fez. Quem tocou produto fica
registrado como executor, e qualquer laudo assinado por essa sessão é rejeitado —
por `verificar_bancada.py` e por `./trava fiscal --sessao <id>`.

Confirme antes de fiscalizar:
```bash
./trava fiscal --sessao "$CLAUDE_SESSION_ID"
```

## 4. A coreografia

```
        ┌──────────────────────────────────────────────┐
        │  ORQUESTRADOR                                │
        │  não escreve produto, não julga: coordena    │
        └───┬──────────────────────────────────────────┘
            │  1. despacha ──────────►  EXECUTOR
            │                          constrói · ./trava selo emitir testes-verdes
            │  ◄────────────────────── output/relatorio.md
            │
            │  2. despacha ──────────►  FISCAL (sessão NOVA)
            │                          lê o diff e o relatório
            │  ◄────────────────────── output/REVISAO.md · APROVADO|REPROVADO
            │
            │     REPROVADO → volta ao executor (até loop.max_rodadas)
            │
            │  3. despacha ──────────►  AUDITOR-DOC
            │  ◄────────────────────── ./trava selo emitir doc-revisada
            │
            │  4. prepara  ──────────►  BANCADA HUMANA  (uma PESSOA)
            │  ◄────────────────────── output/LAUDO-BANCADA.md
            │
            └─ 5. ./trava entregar → ASK → veredito do usuário
```

## 5. HOW TO: despachar a dupla executor↔fiscal

```bash
# 1. EXECUTOR — o prompt precisa do bloco de contrato, senão o gate nega
cat .trava/bloco-contrato.md    # copie
```

```
Task(subagent_type="trava-executor", prompt="""
## CONTRATO DE EXECUÇÃO
<bloco colado aqui>

## TAREFA
Implemente o formulário de cadastro em src/cadastro/.
Ao terminar: ./trava selo emitir testes-verdes e escreva output/relatorio.md
""")
```

```bash
# 2. Aguarde o executor terminar. SEQUÊNCIA, não paralelo (ver §6).

# 3. FISCAL — sessão nova, que não escreveu nada
```

```
Task(subagent_type="trava-fiscal", prompt="""
## CONTRATO DE EXECUÇÃO
<bloco colado aqui>

## TAREFA
Revise o trabalho descrito em output/relatorio.md contra o código real.
Confirme primeiro: ./trava fiscal --sessao "$CLAUDE_SESSION_ID"
Escreva output/REVISAO.md no formato exigido, com ao menos 2 referências
arquivo:linha reais. Você NÃO corrige nada.
""")
```

### O que o fiscal precisa entregar

`verificar_revisao.py` recusa fora deste formato — e cada exigência existe porque
alguma revisão inútil já passou sem ela:

| Exigência | Impede |
|---|---|
| `## VEREDITO: APROVADO\|REPROVADO` | revisão que não conclui nada |
| seções obrigatórias com conteúdo | revisão de uma linha |
| ≥ 2 referências `arquivo:linha` **reais** | aprovar sem ter aberto o código |
| revisão mais nova que o código | "reviso, depois conserto escondido" |
| sem "200 OK"/"funcionou" sozinhos | confundir servidor respondendo com produto funcionando |
| `### ATRITO` preenchido | dizer que está tudo bem sem ter procurado |

## 6. As cinco regras de despacho

1. **Contrato no prompt, sempre.** A trava `subagente-nasce-com-contrato` nega o
   `Task` sem o bloco — e nega **com o template pronto na mensagem**, para você
   reemitir sem gastar ciclo. Um sub-agente que nasce sem o contrato bate nas
   travas sem saber destravar e entra em loop de tentativa.

2. **Sequência entre executor e fiscal, nunca paralelo.** O papel corrente vem do
   último `Task` registrado; com os dois em paralelo o registro fica ambíguo.
   Fan-out paralelo é ótimo para exploração — nunca para o par que se julga.

3. **Teto de rodadas.** `loop.max_rodadas` (padrão 6). Sem ele, executor e fiscal
   jogam ping-pong até o limite de tokens. Ao estourar, a trava **cede e escala**
   ao usuário — nunca libera em silêncio, e o evento fica no ledger como
   `loop_estourado`.

4. **Orçamento de fan-out.** `orcamento.max` em `Task`. Não é erro, é custo: ao
   estourar vira `ask` e o usuário decide.

5. **REPROVADO é sucesso.** Se três entregas seguidas passam de primeira,
   desconfie do fiscal — não comemore. Um fiscal que sempre aprova não está
   fiscalizando, e você está pagando por um carimbo.

## 7. O que o orquestrador não faz

- **Não escreve produto.** Se escrever, vira executor e perde a isenção para
  coordenar o julgamento. O ledger registra.
- **Não resume o veredito do fiscal "para agilizar".** O veredito é lido do
  arquivo. Texto de modelo resumindo texto de modelo é como uma alegação vira
  fato sem ninguém decidir que virou.
- **Não trata relato de sub-agente como prova.** Relato é texto; prova é selo,
  laudo e ledger.

> **Entre a afirmação de um agente e o disco, o disco ganha sempre.**

## 8. O limite honesto

A separação por papel tem um ponto fraco conhecido, e está documentado no código:
o papel corrente vem do último `Task` registrado em
`.trava/contexto/papel_atual.json`. Com sub-agentes em **paralelo**, esse registro
fica ambíguo — dois nascimentos, um arquivo.

Mitigações, em ordem de força:

1. **Toolset (N4)** — o fiscal sem `Write` não escreve, com ou sem registro. Esta
   é a que resolve de verdade.
2. **Ledger de escritas** — independe do papel declarado; olha o que foi feito.
3. **Sequência** — não rode executor e fiscal ao mesmo tempo.

A camada de perfil no contrato é a mais fraca das três. Ela existe para cobrir o
fiscal que tem `Bash`, não para ser a defesa principal.

---

➡️ Próximo: [11 — Auditoria, forense e rollback](11-auditoria-forense-rollback.md)
