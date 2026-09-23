---
description: Reativa a imposição das travas imediatamente.
allowed-tools: Bash(./trava imposicao status)
---

Mostre o estado atual:

!`./trava imposicao status`

Se a imposição já estiver ativa, diga isso e pare.

Se estiver suspensa, peça ao usuário que reative — **você não pode fazer isso por
ele** (exige TTY, e o seu Bash não tem):

> Para reativar agora, digite no seu prompt:
> ```
> #trava-on
> ```
> Ou, no seu terminal: `./trava imposicao on --motivo "..."`
>
> (Ela também volta sozinha quando o prazo expirar.)
