---
description: Lista o rastro forense de uma sessão e restaura os arquivos ao estado anterior.
allowed-tools: Bash(./trava forense:*)
---

Toda escrita passa pelo gate, e o gate guarda a **imagem-anterior** do arquivo antes
de deixar a escrita acontecer. É isso que torna o rollback possível — e é por isso
que ele existe mesmo sem git.

Liste o rastro:

!`./trava forense`

Apresente ao usuário: quantos arquivos foram tocados, por qual sessão, e quais têm
snapshot (arquivos acima de 4 MB não têm).

**O rollback em si é do usuário.** Ele exige TTY e confirmação digitada:

```bash
./trava rollback --sessao <id>            # tudo daquela sessão
./trava rollback --sessao <id> --ate 00042  # do evento 42 em diante
```

Antes de recomendar, diga o que será desfeito, em arquivos e em trabalho. Rollback
é destrutivo na direção oposta: ele apaga o que veio depois.
