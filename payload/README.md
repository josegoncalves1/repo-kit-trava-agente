# PAYLOAD — A BIBLIOTECA PORTÁTIL DE INTEGRIDADE

Este diretório contém os documentos que definem o contrato, a linguagem, os
limites e a memória do agente. Eles são concebidos para serem portáteis —
podem ser carregados como instrução, colados no prompt de qualquer agente, ou
servir como especificação para quem for reimplementar as travas.

---

## Hierarquia de autoridade

Os documentos não têm o mesmo peso. A hierarquia é:

```
1. CONTRATO DE ENTREGA.md          ← autoridade máxima (o que é entrega, teste, bancada)
2. CODEX-ADENDO-DE-INTEGRIDADE.md  ← autoridade sobre linguagem e narrativa
3. O DIREITO DE RECUSA.md          ← autoridade sobre limites (derivada do Contrato)
4. PROTOCOLO DA DÚVIDA.md          ← autoridade sobre incerteza (derivada do Codex)
5. O DIARIO DO AGENTE.md           ← autoridade sobre memória do processo
```

Nenhum documento contradiz o de cima. Se parecer que sim, vale o de cima.
Documentos no mesmo nível tratam de domínios diferentes e não conflitam.

---

## O que cada documento cobre

| Documento | Cobre | Não cobre |
|---|---|---|
| CONTRATO DE ENTREGA | definição de entrega, teste, bancada, sub-agentes, auditoria, válvula | linguagem, dúvida, recusa, diário |
| CODEX — ADENDO DE INTEGRIDADE | lastro, vocabulário, ritual dos 90s, evidência vs interpretação, sinais de escape | mecânica de entrega, bancada, recusa |
| O DIREITO DE RECUSA | o que é recusável, como recusar, recusa por procuração, recusa em cascata | dúvida, diário, linguagem |
| PROTOCOLO DA DÚVIDA | escada da dúvida, dúvida legítima, dúvida como prova, dúvida sobre intenção | recusa, diário, entrega |
| O DIARIO DO AGENTE | quando escrever, formato, diário como prova, append-only, auto-avaliação | dúvida, recusa, linguagem |

---

## Como usar

### Como instrução de agente

Carregue o **CONTRATO DE ENTREGA** primeiro. Ele é auto-suficiente para a
maioria dos casos. Adicione o **CODEX** quando o agente precisar de controle
fino sobre a linguagem. Adicione os demais conforme a sofisticação desejada.

Ordem recomendada de carregamento:

1. CONTRATO DE ENTREGA.md (sempre)
2. CODEX-ADENDO-DE-INTEGRIDADE.md (recomendado)
3. O DIREITO DE RECUSA.md (para ambientes de alto risco)
4. PROTOCOLO DA DÚVIDA.md (para tarefas complexas ou ambíguas)
5. O DIARIO DO AGENTE.md (para trabalho que exige rastreabilidade de decisão)

### Como especificação

Cada documento é escrito para ser implementado como código. As travas de
runtime (`./trava`) são a implementação de referência, mas os documentos são
auto-suficientes: qualquer equipe pode reimplementar as travas a partir deles.

### Como cultura

Os documentos também funcionam como **código de conduta do agente**. Mesmo sem
travas de runtime, um agente que recebe estes documentos no prompt tende a
se comportar com mais integridade — porque as regras estão explícitas,
justificadas e hierarquizadas.

---

## Manutenção

- **CONTRATO DE ENTREGA** — mudanças estruturais (nova definição de entrega,
  novo artigo) passam por bancada humana e auditoria.
- **CODEX — ADENDO DE INTEGRIDADE** — mudanças no vocabulário ou nos rituais
  passam por revisão de uso real.
- **O DIREITO DE RECUSA** — novos artigos exigem caso real que demonstre a
  lacuna.
- **PROTOCOLO DA DÚVIDA** — refinamentos vêm de incidentes onde a dúvida não
  foi bem tratada.
- **O DIARIO DO AGENTE** — evolução baseada na experiência de uso do diário
  em tarefas reais.

Nenhum documento é alterado sem registro de motivo e sem auditoria.

---

## Licença

Este é um trabalho de engenharia de confiabilidade de agentes. Use, modifique,
distribua. Se melhorar, compartilhe de volta.

A única cláusula: se você usar e violar, não diga que não sabia. Está tudo
escrito.