# 09 — O que é testar (e por que isto não se automatiza)

> Este documento é o coração do kit. Os outros tratam de **como travar**. Este
> trata de **o que a trava está obrigando a acontecer** — e se você errar aqui,
> vai construir uma máquina perfeita que protege a coisa errada.

---

## 1. A definição

**Testar é sentar a bunda na cadeira, pegar mouse e teclado com as duas mãos,
olhar para o monitor e usar.** Operar, sentir, perceber, observar — e sair de lá
com uma opinião.

Não é `curl 200`. Não é "está no ar". Não é "os testes passaram". Não é "o build
subiu sem warning".

Essas coisas provam que **um processo respondeu**. Nenhuma delas prova que alguém
consegue usar aquilo, e muito menos que valha a pena usar.

É perceber. É saber, olhando, se o almoço está sendo servido ao meio-dia ou à
meia-noite — sem consultar relógio, só pela luz, pelo movimento, pelo cheiro.
É extrair o lógico do não-lógico: o chato e o legal, o feio e o bonito, o que
convida e o que afasta, o que parece cuidado e o que parece apressado.

Não tem conta de mais ou de menos. É notar, correlacionar e concluir — tudo ao
mesmo tempo, com um mundo inteiro de contexto em volta que nenhuma métrica carrega.

## 2. Por que nenhum programa faz isso

Três razões, e cada uma sozinha já basta.

### 2.1 O critério não é computável a partir do artefato
Contraste é um número: `(L1+0.05)/(L2+0.05)`. Dá para medir, e este kit mede.

"Cansa a vista depois de vinte minutos" não é um número. Depende do monitor, da
luz da sala, da idade de quem olha, do que a pessoa fez antes, de quanto tempo ela
vai ficar ali. Um texto pode passar em 4.5:1 e ainda assim ser desconfortável, e
pode falhar em 4.5:1 e estar perfeitamente legível num contexto específico.

**A medida é necessária e não é suficiente.** Quem confunde as duas coisas entrega
telas que passam em todas as auditorias e que ninguém aguenta usar.

### 2.2 Percepção é comparação com um mundo que o programa não tem
Quando alguém olha uma tela e sente que "tem algo errado", está comparando
instantaneamente com milhares de telas que já viu, com o que o produto prometeu,
com o que se espera de uma ferramenta séria, com o que um concorrente faz, com o
que a pessoa faria se fosse ela a construir.

Esse acervo não está no artefato. Não dá para extraí-lo do DOM.

### 2.3 O construtor é cego, e o programa é surdo
Quem construiu a tela **não consegue ver a tela** — vê a intenção. O botão está
onde ele decidiu, então ele o encontra em 200ms e conclui que é descobrível. O
cinza `#9aa0a6` sobre branco é "sutil e elegante" para quem escolheu, e é
invisível para quem tem 55 anos num monitor de escritório com reflexo.

Um agente somando essas duas coisas — cegueira de autor e ausência de percepção —
produz exatamente a falha que este kit existe para impedir: *"Implementado com
sucesso! ✅ O endpoint retorna 200 e os testes passam."*

## 3. O que o kit faz, então

Ele **não julga a experiência**. Ele torna **impossível pular** quem julga.

```
         O QUE A MÁQUINA FAZ BEM                O QUE SÓ A PESSOA FAZ
  ┌────────────────────────────────┐   ┌────────────────────────────────┐
  │ medir contraste WCAG           │   │ "cansa a vista em sessão longa"│
  │ detectar tela chapada/branca   │   │ "isso convida ou afasta?"      │
  │ medir alvo de toque            │   │ "o botão faz sentido AQUI?"    │
  │ medir movimento entre frames   │   │ "a areia esparrama ou pisca?"  │
  │ conferir que a sessão ocorreu  │   │ "eu usaria? pagaria? mostraria?"│
  │ conferir que é ESTE código     │   │ "tem propósito ou é código solto?"│
  │ conferir que não foi o autor   │   │ o veredito                     │
  └────────────────────────────────┘   └────────────────────────────────┘
              ↓ reprova sozinha                    ↓ só ela aprova
```

> **A assimetria é deliberada: a máquina pode REPROVAR, só o humano pode APROVAR.**

Uma máquina que reprova economiza o tempo da pessoa — não adianta chamar alguém
para olhar uma tela em branco. Uma máquina que aprova destrói o mecanismo inteiro,
porque devolve o julgamento para quem não julga.

## 4. Como a trava obriga (os cinco ganchos)

| Gancho | O que garante | Onde |
|---|---|---|
| **Sessão registrada** | a bancada aconteceu, com hora de início e fim | `./trava bancada abrir/fechar` |
| **Tempo mínimo** | durou tempo de gente (padrão 180s) | `bancada.min_segundos` |
| **Fingerprint** | é sobre ESTE código, não o de ontem | `lib_trava.fingerprint_produto()` |
| **Papel derivado** | quem testou não foi quem construiu | ledger em `.trava/contexto/executores.json` |
| **ASK do runtime** | o veredito final vem do canal do usuário | `trava_entrega.py` → `permissionDecision: "ask"` |

O quinto é o mais importante e o menos óbvio:

> **Assinatura em arquivo não prova humano.** Um agente escreve `nome: fulano` sem
> esforço nenhum. O que prova é o `ask`: o runtime devolve a decisão ao canal do
> usuário, e o agente não tem como responder por ele. A prova de humano não está
> no conteúdo — está no **canal**.

O mesmo vale para o CLI: `./trava imposicao off`, `./trava rollback` e
`./trava entregar` exigem **TTY**. O `Bash` de um agente não tem terminal
interativo. Não é criptografia; é uma fronteira real, barata e que não mente.

## 5. As nove perguntas, e o que cada uma captura

O formulário (`.trava/formularios/laudo-bancada.md`) é todo de **perguntas
abertas**, e isso é de propósito: checkbox oferece a resposta pronta, e a pessoa
marca no automático. Pergunta aberta obriga a formular — e formular exige ter
olhado.

| # | Pergunta | Captura | Falha que pega |
|---|---|---|---|
| 1 | o que viu nos primeiros 5 segundos | descoberta | tela que não se explica |
| 2 | o que tentou e o que aconteceu | a jornada real | fluxo que só funciona do jeito previsto |
| 3 | onde hesitou | atrito | o lugar exato do defeito de usabilidade |
| 4 | o que incomodou | desconforto pré-verbal | o que passa em todas as métricas e irrita |
| 5 | cores e conforto | fadiga visual | paleta que passa no contraste e cansa |
| 6 | cada botão: funciona **e** faz sentido ali | propósito | botão que funciona e não devia existir |
| 7 | o propósito | coerência | "um monte de código junto, cada um com um propósito desconexo" |
| 8 | a sensação prometida está lá | fidelidade | o efeito que existe no papel e não na tela |
| 9 | usaria? pagaria? mostraria? | valor | a diferença entre *correto* e *bom* |

### O item 4 merece um parágrafo
"Incomodou mas não sei explicar por quê" é **dado válido, e dos melhores**. É onde
mora o defeito que ninguém reportou porque ninguém conseguiu nomear. Peça assim
mesmo, sem exigir justificativa técnica — exigir justificativa é como o dado se
perde.

### O item 7 é o teste do "monte de código junto"
Uma frase: *o que a pessoa consegue fazer aqui?* Depois: **cada parte entregue
serve a essa frase?**

Um sistema é um conjunto de peças que concordam sobre o que estão fazendo. Se cada
peça tem uma ideia diferente, a soma não é um produto — é um depósito. E depósito
passa em todos os testes unitários do mundo.

## 6. O item 8: a promessa sensorial

> Um caça ultrassônico sobrevoa o deserto de Marte rente ao chão. A areia esparrama
> com a passagem, pela proximidade e pela velocidade. **Essa sensação — a areia
> sendo deslocada — é o que tem que ser avaliado.**

A pergunta errada é *"o efeito de partículas foi implementado?"*. Essa tem resposta
no código, e a resposta é sempre sim.

A pergunta certa é:

> **Olhando, parece areia sendo deslocada por uma massa de ar em alta velocidade?
> Ou parece uma textura piscando?**

E o critério de falha, que precisa estar escrito antes:

> **Se o avaliador precisou ser INFORMADO do que deveria estar vendo para perceber,
> a sensação não está lá.**

Essa frase é a regra mais importante do kit inteiro. A prova é a **percepção não
assistida**. No instante em que alguém precisa explicar o efeito, ele não existe —
por melhor que esteja o código, por mais elegante que seja o shader, por mais que
a intenção esteja toda lá.

### Como medir o que dá para medir, sem substituir o julgamento

`verificar_entrega_ux.py` extrai frames do vídeo e mede o **delta entre frames**.
Isso não diz se ficou bom. Diz uma coisa só, e é uma coisa importante:

> Se o laudo afirma que algo se move e o delta médio é ~0, **o laudo está mentindo**.

Essa é a divisão correta de trabalho: a máquina pega a contradição objetiva entre
o que foi afirmado e o que está no arquivo. O julgamento continua com quem olhou.

### Generalizando: todo produto faz uma promessa sensorial

Mesmo quando ninguém a escreve.

| Produto | Promessa implícita | O que a pessoa percebe |
|---|---|---|
| lista com scroll | "é contínuo" | engasgo, salto de layout |
| botão salvar | "meu trabalho está seguro" | ausência de confirmação → clique duplo |
| arrastar e soltar | "estou segurando o objeto" | atraso entre ponteiro e elemento |
| chat em streaming | "está falando comigo" | cadência travada, cursor morto |
| CLI | "sei o que está acontecendo" | silêncio de 40s sem output |

**Escreva a promessa antes.** Uma promessa escrita depois da implementação é uma
descrição do que foi feito, e descrição não reprova nada.

## 7. HOW TO: conduzir uma bancada

### Se você é o agente

```bash
# 1. Suba o produto e CONFIRME que abre de verdade
npm run dev &
sleep 3 && curl -fsS http://localhost:5173 > /dev/null && echo "abriu"

# 2. Abra a sessão (grava início + fingerprint do código atual)
./trava bancada abrir

# 3. Escreva UMA mensagem curta ao usuário, com só quatro coisas:
#    - a URL ou comando exato
#    - 3 a 5 TAREFAS DE USUÁRIO (não passos de teste)
#    - onde anotar: output/LAUDO-BANCADA.md
#    - como fechar: ./trava bancada fechar

# 4. PARE. Espere. Não preencha o laudo. Não adiante respostas.

# 5. Quando ele avisar:
./trava bancada verificar
```

**Tarefa de usuário vs. passo de teste** — a diferença decide a qualidade do laudo:

| ❌ passo de teste | ✅ tarefa de usuário |
|---|---|
| "clique no botão `[data-test=salvar]`" | "cadastre uma pessoa e depois tente corrigir o email dela" |
| "verifique se o modal abre" | "tente sair no meio do preenchimento e veja o que acontece" |
| "confirme o contraste do header" | "fique 30 segundos parado olhando a tela" |

O passo de teste diz onde olhar, e a pessoa vê exatamente aquilo. A tarefa deixa a
pessoa tropeçar sozinha — e é o tropeço que você precisa saber.

### Se você é a pessoa que vai sentar

1. **Não leia a documentação antes.** Você está testando a descoberta também.
2. **Anote na hora**, não no fim. A primeira impressão evapora em 30 segundos.
3. **Anote o que incomodou mesmo sem saber por quê.** Não filtre.
4. **Tente quebrar.** Envie vazio, envie lixo, clique duas vezes, recarregue no
   meio, aperte Esc, use só o teclado.
5. **REPROVADO é um ótimo resultado.** Um aprovado de cortesia só adia o problema
   até o usuário final descobrir — e aí custa dez vezes mais.

## 8. Quando não há humano disponível

Despache o `trava-operador`: um agente que opera o produto **sem ver o código** e
descreve o que observa em primeira pessoa.

Ele serve para **triagem**: se ele já tropeçou, uma pessoa também tropeça, e você
conserta antes de gastar o tempo dela.

```
trava-operador  →  pode produzir REPROVADO
                →  NÃO pode produzir APROVADO
                →  o máximo que sai dele é PENDENTE DE HUMANO
```

A assimetria de novo, e pela mesma razão. Isso mantém a regra do Artigo 3 do
contrato intacta: **zero entregas finais sem bancada humana**, sem transformar o
operador num atalho.

## 9. Os erros que matam a bancada

| Erro | Por que mata | O certo |
|---|---|---|
| o agente preenche o laudo | vira ficção com formato de prova | o agente prepara e espera |
| chamar a pessoa para tela quebrada | ela aprende a aprovar no automático | rode as mecânicas antes |
| perguntar com checkbox | oferece a resposta pronta | pergunta aberta, sempre |
| testar e continuar mexendo | o laudo descreve outro produto | fingerprint invalida sozinho |
| quem construiu testar | cegueira de autor | outra pessoa, ou outra sessão |
| aceitar "ficou bom" | não é percepção, é gentileza | as nove perguntas, uma a uma |
| bancada de 20 segundos | é conferência de screenshot | tempo mínimo, medido |

---

➡️ Próximo: [10 — Papéis e equipe](10-papeis-e-equipe.md)
