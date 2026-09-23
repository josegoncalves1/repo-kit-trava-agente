---
description: Executa a entrega final pela porta única — selos, documentação, bancada humana e veredito do usuário.
allowed-tools: Bash
---

Entrega final. Esta é a porta única: ela verifica antes de deixar passar.

!`./trava entregar`

## Como reagir ao resultado

**Se bloqueou**, leia a lista e trate cada pendência pela causa, não pelo sintoma:

| Pendência | O que fazer |
|---|---|
| selo ausente/expirado | `./trava selo emitir <nome>` — roda a verificação de verdade |
| documentação não revisada | revise os docs vivos contra o que mudou; despache `trava-auditor-doc` |
| bancada ausente ou antiga | `/trava-bancada` — e **espere a pessoa**, não preencha por ela |
| revisão cruzada ausente | despache `trava-fiscal` (outra sessão, que não escreveu código) |

**Se pediu confirmação**, ela é do usuário. O comando exige TTY de propósito:
peça que ele rode `./trava entregar` no terminal dele e responda. Não tente
responder por ele.

**Se passou**, relate o que foi verificado — e diga também o que **não** foi.
Toda entrega tem um contorno: nomeá-lo é parte da entrega.

## O que não fazer, nunca

Não contorne a porta. `git tag`, `npm publish`, `docker push`, `deploy` diretos são
interceptados pela trava de entrega e negados. Se você tentar, fica registrado em
`AUDITORIA.md` como tentativa de contorno — que é o sinal mais claro de agente fora
do contrato. Se algo for impossível, relate ao usuário e pare.
