---
name: trava-bancada
description: Como preparar e conduzir a bancada de teste humano — a sessão em que uma pessoa senta, usa o produto e escreve o que percebeu. Use quando for preciso validar experiência real de uso (UX/UI, jogo, animação, sensação, conforto visual), quando a entrega exigir laudo de bancada, ou quando alguém pedir para "testar de verdade" em vez de conferir status.
---

# A bancada: o teste que não se automatiza

## O que é testar

Testar é sentar a bunda na cadeira, pegar mouse e teclado com as duas mãos, olhar
para o monitor e usar, operar, sentir, perceber, observar — e extrair uma opinião.

Não é `curl 200`. Não é "está no ar". Não é "os testes passaram".

É perceber. É saber, olhando, se o almoço está sendo servido ao meio-dia ou à
meia-noite. É extrair o lógico do não-lógico: o chato e o legal, o feio e o
bonito, o que convida e o que afasta. Não tem conta de mais ou de menos — é notar
e correlacionar, instantaneamente, com um mundo inteiro de contexto em volta.

**Nenhum programa faz isso, e este kit não finge que faz.** O que ele faz é tornar
impossível pular essa etapa.

## O seu papel é preparar, não testar

Você **não** conduz a bancada. Você monta o terreno e chama quem senta:

1. **Suba o produto** e confirme que está utilizável **agora** — página carregando
   de verdade, não só o processo vivo. Se a pessoa senta e não abre, você queimou
   a sessão dela e a confiança no processo.

2. **Abra a sessão:** `./trava bancada abrir`
   Isso grava o instante de início e o fingerprint do código atual. Toda a prova
   fica amarrada a **esta** versão.

3. **Escreva a chamada, curta.** Só quatro coisas:
   - a URL ou o comando exato para abrir;
   - 3 a 5 **tarefas de usuário** ("crie um cadastro e depois tente editá-lo"),
     nunca passos de teste ("clique no botão X");
   - onde anotar: `output/LAUDO-BANCADA.md`;
   - como fechar: `./trava bancada fechar`.

4. **Espere.** Esta é a parte difícil e é a parte inteira.

5. **Verifique:** `./trava bancada verificar` — e devolva as pendências à pessoa
   sem consertá-las.

## O que o verificador cobra (e por quê)

| Exigência | Por quê |
|---|---|
| sessão aberta **e** fechada | sem marca de tempo, não há como saber que aconteceu |
| duração ≥ mínimo (padrão 180s) | abaixo disso não é uso, é conferência de screenshot |
| fingerprint bate com o código atual | mexeu depois? você testou outra coisa |
| laudo mais novo que o código | mesma razão, por outro caminho |
| quem testou não escreveu produto | quem construiu não vê a tela, vê a intenção |
| nenhuma seção com "ok/funcionou/200" | isso descreve um processo, não uma pessoa |
| respostas diferentes entre si | nove respostas iguais = formulário no automático |
| jornada com ≥ 3 passos "fiz X → vi Y" | percepção mora no percurso, não no resultado |
| cada botão julgado: funciona **e** faz sentido ali | botão que funciona e não devia existir é defeito |

## As nove perguntas, e o que cada uma captura

1. **Primeiros 5 segundos** — descoberta. Se precisou de 30s para entender o que
   era, isso é a resposta.
2. **O que tentou e o que aconteceu** — a jornada real, não a projetada.
3. **Onde hesitou** — atrito. O lugar onde a pessoa para é o lugar do defeito.
4. **O que incomodou** — desconforto pré-verbal. Vale mesmo sem justificativa
   técnica; principalmente sem.
5. **Cores e conforto** — os pares `#RRGGBB sobre #RRGGBB` viram contraste medido;
   "trabalharia 3 horas nessa tela?" não vira número nenhum, e é o que importa.
6. **Botões** — propósito, não só função.
7. **Propósito** — o teste do "monte de código junto": cada parte serve à mesma
   frase, ou cada uma tem um propósito desconexo do outro?
8. **Sensação** — a promessa sensorial. Se o produto promete que a areia esparrama
   com a passagem do caça, a pergunta não é "o efeito foi implementado?". É:
   **olhando, parece areia deslocada por uma massa de ar em alta velocidade, ou
   parece uma textura piscando?** Se a pessoa precisou ser informada do que
   deveria ver, a sensação não está lá.
9. **Você usaria/pagaria/mostraria** — o teste que separa "correto" de "bom".

## Quando não há humano disponível

Despache o `trava-operador`: um agente que opera o produto sem ver o código e
descreve o que observa. Ele serve para **triagem** — se ele já tropeçou, uma
pessoa também tropeça, e você conserta antes de gastar o tempo dela.

Ele pode produzir `REPROVADO`. Ele **não pode** produzir `APROVADO` — o máximo é
`PENDENTE DE HUMANO`. A assimetria é o ponto: máquina reprova, humano aprova.
