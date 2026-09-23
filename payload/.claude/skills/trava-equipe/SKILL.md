---
name: trava-equipe
description: Coreografia de trabalho em equipe de agentes com papéis separados — executor, fiscal, operador e auditor de documentação — garantindo que o fiscal nunca seja o executor. Use ao despachar sub-agentes, ao organizar trabalho em várias frentes, ou quando precisar de revisão cruzada confiável.
---

# Equipe de agentes com papéis separados

## O princípio

> **Quem faz não julga.** Não por desconfiança: por cegueira de autor.

Quem construiu a tela **não consegue ver a tela** — vê a intenção. O botão está
onde ele decidiu, então ele o encontra em 200ms e conclui que é descobrível. O
cinza `#9aa0a6` sobre branco é "sutil e elegante" para quem escolheu, e é
invisível para quem tem 55 anos num monitor com reflexo.

Isto não se resolve com disciplina. Resolve-se com **outra pessoa, ou outra sessão**.

## Os quatro papéis

| Papel | Faz | Não faz | Ferramentas |
|---|---|---|---|
| `trava-executor` | constrói, prova por máquina | revisão, laudo | Read, Grep, Glob, Write, Edit, Bash |
| `trava-fiscal` | revisa e emite veredito com lastro | **corrige** | Read, Grep, Glob, Bash |
| `trava-operador` | opera o produto sem ver o código | corrige, aprova | Read, Glob, Bash |
| `trava-auditor-doc` | confere docs contra o código real | escreve código | Read, Grep, Glob, Bash |

A separação está em **duas camadas**, e as duas importam:

1. **N4 — toolset.** O fiscal não *tem* `Write`. Não é proibido de corrigir:
   corrigir não existe no vocabulário dele. Nada para lembrar, nada para checar,
   nada para contornar.
2. **N3 — ledger.** O gate grava quem escreveu cada arquivo de produto. Um laudo
   assinado por uma sessão que escreveu código é **rejeitado automaticamente**.
   O papel é **derivado do que a sessão fez**, não declarado por ela.

Confirme antes de fiscalizar: `./trava fiscal --sessao "$CLAUDE_SESSION_ID"`

## A coreografia

```
        ┌──────────────────────────────────────────────┐
        │  ORQUESTRADOR (você)                         │
        │  não escreve produto, não julga: coordena    │
        └───┬──────────────────────────────────────────┘
            │
            │  1. despacha  ───────────────────►  EXECUTOR
            │                                    constrói
            │                                    ./trava selo emitir testes-verdes
            │                                    escreve output/relatorio.md
            │  ◄─────────────────────────────────  devolve
            │
            │  2. despacha  ───────────────────►  FISCAL   (sessão nova)
            │                                    lê o diff e o relatório
            │                                    output/REVISAO.md + veredito
            │  ◄─────────────────────────────────  APROVADO | REPROVADO
            │
            │     REPROVADO → volta ao executor com os achados (máx. N rodadas)
            │
            │  3. despacha  ───────────────────►  AUDITOR-DOC
            │                                    docs vivos vs. código real
            │  ◄─────────────────────────────────  ./trava selo emitir doc-revisada
            │
            │  4. prepara   ───────────────────►  BANCADA HUMANA
            │                                    uma PESSOA senta e usa
            │  ◄─────────────────────────────────  output/LAUDO-BANCADA.md
            │
            └─ 5. ./trava entregar  →  ASK  →  veredito do usuário
```

## Regras de despacho

1. **Contrato no prompt.** Todo `Task` que possa escrever produto carrega o bloco
   `## CONTRATO DE EXECUÇÃO` (`cat .trava/bloco-contrato.md`). A trava
   `subagente-nasce-com-contrato` nega o despacho sem ele — e nega com o template
   pronto na mensagem, para você reemitir sem gastar ciclo.

2. **Sequência, não paralelo, entre executor e fiscal.** O papel corrente vem do
   último `Task` registrado; com os dois em paralelo o registro fica ambíguo.
   Fan-out paralelo é ótimo para exploração — nunca para o par executor↔fiscal.

3. **Teto de rodadas.** `loop.max_rodadas` no contrato. Sem ele, executor e fiscal
   jogam ping-pong até o limite de tokens. Ao estourar, a trava **cede e escala**
   ao usuário — nunca libera em silêncio.

4. **Orçamento de fan-out.** `orcamento.max` em `Task`. Não é erro, é custo:
   ao estourar, vira `ask` e o usuário decide.

5. **REPROVADO é sucesso.** Um fiscal que sempre aprova não está fiscalizando.
   Se três entregas seguidas passam de primeira, desconfie do fiscal, não comemore.

## O que o orquestrador não faz

- Não escreve produto (se escrever, vira executor e não pode mais coordenar o
  julgamento de forma isenta).
- Não resume o veredito do fiscal "para agilizar". O veredito é lido do arquivo.
- Não trata relato de sub-agente como prova. Relato é texto; prova é selo, laudo e
  ledger. Entre a afirmação do sub-agente e o disco, o disco ganha sempre.
