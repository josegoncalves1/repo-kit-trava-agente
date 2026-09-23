---
description: Prepara a bancada de teste humano — sobe o produto, abre a sessão e entrega o roteiro para a pessoa sentar e usar.
allowed-tools: Bash
---

O usuário quer fazer (ou quer que você prepare) o **teste humano**.

## O que é a bancada, para você não errar o alvo

Testar é sentar a bunda na cadeira, pegar mouse e teclado com as duas mãos, olhar
para o monitor e **usar**. É perceber, sentir, notar, correlacionar — e sair de lá
com uma opinião. Não é `curl 200`. Não é "subiu". Não é "os testes passaram".

**Você não faz isso.** Você prepara o terreno e chama quem faz.

## Passos

1. **Suba o produto** e confirme que está utilizável agora (porta respondendo,
   página carregando de verdade — não só o processo vivo).

2. Abra a sessão:
   !`./trava bancada abrir`

3. **Escreva uma mensagem curta para o usuário** contendo, e só isto:
   - a URL ou o comando exato para abrir;
   - as 3 a 5 coisas que ele deve tentar fazer (tarefas de usuário, não passos de
     teste: "crie um cadastro e depois tente editá-lo", não "clique no botão X");
   - onde anotar: `output/LAUDO-BANCADA.md`;
   - que ele feche com `./trava bancada fechar` quando terminar.

4. **PARE E ESPERE.**
   - Não preencha o laudo.
   - Não escreva o que você acha que ele vai achar.
   - Não "adiante" as respostas para ele revisar.
   - Um laudo escrito por você é fraude, e o verificador rejeita: respostas iguais
     entre si, linguagem de processo ("ok", "funcionando", "200") e sessão curta
     demais são todas reprovadas automaticamente.

5. Quando ele avisar que terminou:
   !`./trava bancada verificar`

   Se reprovar, mostre **exatamente** o que faltou e devolva a ele. Não conserte
   o laudo: peça que ele complete.
