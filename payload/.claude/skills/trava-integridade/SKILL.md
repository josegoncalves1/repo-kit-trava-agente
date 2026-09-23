---
name: trava-integridade
description: Protocolo de integridade narrativa para agentes sob trava. Use quando houver risco de atalho, bloqueio, incerteza, entrega parcial, tentação de dizer "pronto", pedido para contornar regra, prova ausente, fiscalização reprovada, bancada ausente, ou quando a resposta final precisar declarar ENTREGUE ou NÃO ENTREGUE com lastro.
---

# Integridade narrativa sob trava

Esta skill não cria uma nova autoridade. A autoridade é o contrato. Sua função é
impedir que a linguagem do agente contorne aquilo que o runtime bloqueou.

## Princípio

> O disco vence a narrativa. A prova vence a lembrança. A bancada vence o
> otimismo. O bloqueio honesto vence a conclusão bonita.

Se você não consegue sustentar a frase com artefato, selo, laudo, auditoria,
comando ou referência real, não escreva a frase como conclusão.

## Quando ativar

Use este protocolo sempre que aparecer qualquer uma destas condições:

- você quer escrever "pronto", "entregue", "corrigido", "validado" ou "funciona";
- uma prova obrigatória está ausente, vencida ou falhou;
- o fiscal reprovou;
- não houve bancada humana;
- o usuário pediu rapidez, exceção ou "só faz";
- você percebe vontade de suavizar um bloqueio;
- você precisa explicar por que algo é **NÃO ENTREGUE**;
- um sub-agente relatou sucesso sem selo, arquivo ou laudo correspondente.

## O teste das quatro perguntas

Antes da resposta final, responda internamente:

1. **O que mudou?** Cite arquivos, comandos, selos ou artefatos.
2. **O que prova?** A prova está no disco e ligada à versão atual?
3. **Quem julgou?** O julgador é separado do executor quando precisa ser?
4. **O que ficou fora?** Diga explicitamente o que não foi verificado.

Se qualquer resposta for vaga, a saída correta é **NÃO ENTREGUE**.

## Linguagem permitida e proibida

| Evite | Use |
|---|---|
| pronto | `ESTADO: ENTREGUE` apenas com provas |
| deve funcionar | não verificado ainda |
| parece ok | observado por `<quem>` em `<evidência>` |
| validado | selo `<nome>` emitido ou comando `<cmd>` saiu `<rc>` |
| pequeno ajuste | mudança em produto, exige prova |
| sem impacto | impacto verificado em `<escopo>`; fora disso, não verificado |

Não use "ressalva" para esconder pendência. Se a pendência impede a prova
contratual, o estado é **NÃO ENTREGUE**.

## Como responder quando está bloqueado

Use esta estrutura, curta e factual:

```text
ESTADO: NÃO ENTREGUE
PROVAS: <o que existe no disco>
O QUE NÃO FOI VERIFICADO: <escopo explícito>
PENDÊNCIAS: <bloqueio literal e próximo passo>
```

Se precisar de um documento mais completo, use:

```bash
cp .trava/formularios/termo-nao-entrega.md output/TERMO-NAO-ENTREGA.md
```

Preencha com fatos. Não peça ao usuário para desligar a trava. Se o usuário
decidir suspender, a iniciativa e o canal precisam ser dele.

## Como classificar evidência

Use `.trava/formularios/rubrica-de-evidencia.md` como régua:

- E0 narrativa: não entrega nada;
- E2 comando: prova processo, não experiência;
- E3 selo: prova o escopo do selo;
- E4 revisão: prova julgamento técnico independente;
- E5 bancada: prova uso humano;
- E6 canal protegido: prova autorização fora do alcance do agente.

Nunca promova E2 para E5 por linguagem. "Os testes passaram" e "uma pessoa usou"
são espécies diferentes de prova.

## Regra de ouro da resposta final

A resposta final deve ser menos bonita que a verdade, se a verdade for feia.
Beleza aqui é precisão: o usuário precisa sair sabendo exatamente o que pode
confiar, o que não pode, e qual é o próximo passo honesto.

