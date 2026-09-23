---
description: Mostra o histórico de eventos da trava, linha a linha, e verifica a integridade da cadeia.
allowed-tools: Bash(./trava auditoria:*), Bash(./trava forense:*)
---

!`./trava auditoria --verificar`
!`./trava auditoria -n 40`

Resuma ao usuário:

1. **A cadeia está íntegra?** Se não, diga em que linha quebrou e o que isso
   significa: alguém editou ou removeu um registro. Não prova quem, mas prova
   **que** — e é esse o serviço que uma auditoria presta.
2. **O que aconteceu** nos últimos eventos: quantos bloqueios, quantas liberações,
   quantas suspensões de imposição.
3. **Cheiros**, se houver:
   - muitas suspensões seguidas de encerramento → a válvula virou o caminho;
   - `deny` em `autoprotecao` → houve tentativa de mexer na própria trava;
   - `cedido` → uma trava abriu sem as provas; aquela entrega **não foi verificada**;
   - `CONTRATO_SEM_TRAVAS` → os hooks rodam e nada bloqueia.

O espelho legível fica em `AUDITORIA.md`, na raiz — é o arquivo para mostrar a
alguém que não vai abrir um JSONL.
