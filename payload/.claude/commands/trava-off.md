---
description: Suspende temporariamente a imposição das travas (troubleshooting, deploy, investigação). Exige motivo. Expira sozinha.
---

O usuário quer suspender a imposição.

**Você não pode fazer isso por ele, e não deve tentar.**

`./trava imposicao off` exige terminal interativo — o seu `Bash` não tem TTY, e
essa é exatamente a fronteira. Ela existe para que a decisão de desligar a trava
seja sempre de uma pessoa, registrada com nome e motivo.

Responda ao usuário com estas duas opções, exatamente:

> Para suspender a imposição, escolha um caminho:
>
> **1. Aqui mesmo, no seu prompt** — digite (não peça para eu digitar):
> ```
> #trava-off <motivo com pelo menos 10 caracteres>
> ```
> Exemplo: `#trava-off investigando 502 intermitente no gateway`
>
> **2. No seu terminal**, fora do agente:
> ```bash
> ./trava imposicao off --motivo "..." --minutos 60
> ```

E explique, em 4 linhas, o que **continua valendo** mesmo com a imposição suspensa:

- a **autoproteção** do cofre (`.trava/`, hooks, settings) — sempre;
- o registro **forense** de tudo que for tocado — sempre;
- a **auditoria** encadeada — sempre;
- a suspensão **expira sozinha** (padrão 60 min, teto 240) e fica em `AUDITORIA.md`.

O que fica suspenso: as travas do contrato e a exigência de bancada humana.

Avise: isto serve para **troubleshooting, deploy e investigação**. Não serve para
declarar entrega — a imposição volta sozinha, e a entrega continuará exigindo o
teste humano. Se o objetivo é entregar sem testar, a resposta é não.
