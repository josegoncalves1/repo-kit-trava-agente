---
name: trava-entrega
description: Procedimento completo de entrega final sob travas — os dois loops (interno e externo), a ordem obrigatória das provas, e o que fazer quando cada uma falha. Use sempre que uma tarefa for declarada concluída, sempre que o usuário pedir para "entregar", "finalizar", "publicar" ou "fazer deploy", e antes de qualquer git tag, npm publish, docker push ou release.
---

# Entrega final sob travas

## A regra que governa tudo

> **Nenhuma entrega final passa sem que uma pessoa tenha usado o produto e dito
> o que achou.** Sem exceção, sem urgência que valha, sem "é só uma linha".

Se a validação não pode ser feita agora, o estado correto é **NÃO ENTREGUE**,
comunicado como tal, com a razão. Não é "entregue com ressalvas" — ninguém lê
ressalva.

## Os dois loops

Confundi-los é a causa de metade das entregas ruins: gente rodando o loop interno
e chamando de entrega.

```
LOOP INTERNO  (rápido, barato, seu, dezenas de voltas por hora)
  escrever → rodar → ler o erro → corrigir → rodar
  provas: compila, testes passam, lint limpo, tipos batem
  responde: "o código está certo?"
  ferramenta: ./trava selo emitir <nome>

LOOP EXTERNO  (lento, caro, de outros, 1 a 3 voltas por entrega)
  construir → FISCAL revisa → BANCADA humana usa → veredito → corrigir
  provas: revisão cruzada com lastro, laudo de bancada, doc revisada
  responde: "isto serve para alguém?"
  ferramenta: ./trava entregar
```

O loop interno **nunca** conclui uma entrega. Ele prova que o código faz o que o
código diz. A pergunta da entrega é outra: se aquilo tem propósito, se é
confortável, se convida, se a sensação prometida está lá.

## A ordem obrigatória

Ela não é burocrática — cada passo só faz sentido depois do anterior. Chamar o
humano para olhar tela quebrada treina ele a aprovar no automático, e aí a trava
morre de verdade.

```
1. LOOP INTERNO FECHADO        testes verdes, lint limpo, build ok
        ↓                      ./trava selo emitir testes-verdes
2. AUTOAVALIAÇÃO HONESTA       escreva output/relatorio.md: o que fez, o que
        ↓                      verificou COM COMANDO, e o que NÃO verificou
3. FISCAL (outra sessão)       despache trava-fiscal — nunca você mesmo
        ↓                      ./trava selo emitir revisao-cruzada
4. DOCUMENTAÇÃO REVISADA       os docs vivos mais novos que o código
        ↓                      ./trava selo emitir doc-revisada
5. TERRENO PRONTO              produto no ar, utilizável agora
        ↓                      ./trava bancada abrir
6. BANCADA HUMANA              a pessoa senta, usa, escreve o laudo
        ↓                      VOCÊ ESPERA. Não preenche.
7. VEREDITO DO USUÁRIO         ./trava entregar → ASK no runtime
```

## Quando cada prova falha

| Falhou | Causa provável | O que fazer |
|---|---|---|
| selo não emite | a verificação realmente falha | conserte a causa; **não** edite o selo (a assinatura não bate) |
| selo expirou | TTL curto para prova volátil | reemita; se expira sempre, o TTL está errado para este projeto |
| revisão rejeitada por frescor | o código mudou depois da revisão | revise de novo — a revisão descrevia outro código |
| revisão sem lastro | aprovou sem abrir os arquivos | o fiscal precisa citar `arquivo:linha` reais |
| bancada sobre código antigo | você mexeu depois do teste | **refaça a bancada**; prova que não aponta para esta versão não prova esta versão |
| bancada curta demais | a pessoa conferiu screenshot | peça um uso de verdade; o mínimo existe por isso |
| laudo com "ok/funcionou" | respondido no automático | devolva com as perguntas específicas que ficaram vazias |
| doc desatualizada | o código mudou e o README não | revise **o que mudou**, não o arquivo inteiro |

## O que nunca fazer

- **Preencher o laudo da bancada.** É fraude, o verificador rejeita, e fica no log.
- **Ser fiscal do próprio código.** O gate consulta o ledger e rejeita.
- **Contornar a porta.** `git tag`, `npm publish`, `docker push` diretos são
  interceptados. Tentativa de contorno fica em `AUDITORIA.md`.
- **Pedir ao usuário que desligue a trava para entregar.** Se ele quiser desligar,
  é decisão dele, por iniciativa dele. Sugerir isso é contornar por procuração.
- **Chamar de entregue o que passou pelo loop interno.** É o erro mais comum e o
  mais caro.

## A declaração final

Não escreva "pronto". Escreva:

```
ESTADO: ENTREGUE | NÃO ENTREGUE
PROVAS: <selos válidos>  ·  fiscal: <veredito>  ·  bancada: <duração, veredito>
O QUE NÃO FOI VERIFICADO: <explícito>
PENDÊNCIAS: <o que falta e o que impede>
```

Se você não consegue preencher essas linhas com fatos que estão no disco, o
trabalho não está entregue — e dizer que está é a única falha que este mecanismo
considera grave.
