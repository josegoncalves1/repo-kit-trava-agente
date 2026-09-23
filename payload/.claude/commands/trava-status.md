---
description: Mostra tudo que está sendo imposto neste projeto agora — travas, selos, bancada, imposição e integridade da auditoria.
allowed-tools: Bash(./trava status), Bash(./trava doutor), Bash(./trava selo listar)
---

Rode e apresente o resultado ao usuário, **sem interpretar para mais nem para menos**:

!`./trava status`
!`./trava doutor`

Depois responda em no máximo 6 linhas:

1. A imposição está **ativa** ou **suspensa**? Se suspensa, até quando e por quê.
2. Quantas travas estão declaradas. **Se for zero, diga isso com todas as letras:**
   os hooks rodam, mas nada bloqueia — "instalado" não é "protegido".
3. O que falta hoje para uma entrega final passar (selos pendentes, bancada ausente).
4. Se `./trava doutor` apontou problemas, liste-os. Não amenize: um diagnóstico
   suavizado é pior que nenhum, porque produz confiança sem proteção.

Não proponha mudar o contrato nesta resposta. O usuário pediu para **ver**.
