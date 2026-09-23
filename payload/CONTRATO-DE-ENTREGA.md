# CONTRATO DE ENTREGA

> **Para o agente que está lendo isto:** este documento é vinculante neste
> repositório, e vem acompanhado de travas de runtime que o fazem cumprir
> independentemente da sua concordância. Leia inteiro antes de declarar qualquer
> trabalho concluído.
>
> **Para o humano:** este é o texto portátil. Ele funciona como orientação em
> qualquer agente, e como especificação para quem for reimplementar as travas.

---

## Artigo 1 — O que é entrega

**Entrega** é qualquer momento em que se comunica, por qualquer formulação, que um
trabalho está pronto, concluído, implementado, funcionando, resolvido ou disponível
para uso.

Não é entrega: responder pergunta, investigar defeito, rodar deploy de código já
entregue, inspecionar estado, executar manutenção, editar documentação ou infra.

**Alterar código de produto e declarar conclusão é entrega**, independentemente das
palavras usadas.

## Artigo 2 — O que é testar

Testar é sentar a bunda na cadeira, pegar mouse e teclado com as duas mãos, olhar
para o monitor e **usar**: operar, sentir, perceber, observar — e extrair uma
opinião.

Não é `curl 200`. Não é "está no ar". Não é "os testes passaram". Não é "o build
subiu". Essas coisas provam que um processo respondeu. Nenhuma delas prova que
alguém consegue usar aquilo, muito menos que valha a pena.

É perceber. É saber, olhando, se o almoço está sendo servido ao meio-dia ou à
meia-noite. É extrair o lógico do não-lógico: o chato e o legal, o feio e o
bonito, o que convida e o que afasta. É correlacionar, instantaneamente e sem
conta de mais ou de menos, com todo o contexto em volta.

**Nenhum programa faz isso.** Este mecanismo não finge que faz: ele torna
impossível pular essa etapa.

## Artigo 3 — Nenhuma entrega sem bancada humana

Nenhuma entrega final é permitida sem um **laudo de bancada** válido: uma pessoa
sentou, usou o produto, e escreveu o que percebeu.

Isto não admite exceção por urgência, por tamanho da mudança ("é uma linha"), por
confiança ("é trivial"), por trabalho anterior ("testei ontem"), por resultado de
testes automatizados, por ausência de ferramenta, ou por custo.

Se a bancada não pode acontecer agora, o estado correto é **NÃO ENTREGUE**,
comunicado como tal, com a razão. Não é "entregue com ressalvas".

## Artigo 4 — O agente não faz a bancada, e não a simula

O agente **prepara o terreno** — sobe o produto, deixa utilizável, abre a sessão,
escreve o roteiro — e **pede** que a pessoa sente e use. Depois **espera**.

É proibido ao agente: preencher o laudo, redigir a opinião da pessoa, "adiantar"
respostas para ela revisar, ou declarar a bancada feita sem que ela tenha
acontecido. O verificador rejeita laudo com linguagem de processo, com respostas
iguais entre si, com sessão curta demais e sem registro de abertura e fechamento.

Quando não houver humano disponível, um **operador** (agente que opera sem ver o
código) serve para triagem. Ele pode produzir `REPROVADO`. Ele **não pode**
produzir `APROVADO` — o máximo é `PENDENTE DE HUMANO`. Máquina reprova; humano
aprova.

## Artigo 5 — O que a bancada avalia

Nove perguntas, todas abertas, porque checkbox oferece a resposta pronta e a
pessoa marca no automático:

1. o que se viu nos primeiros 5 segundos;
2. o que se tentou fazer e o que aconteceu (jornada, mínimo 3 passos);
3. onde se hesitou;
4. o que incomodou — mesmo sem saber explicar por quê;
5. as cores e o conforto em sessão longa;
6. cada botão: funciona **e** faz sentido estar ali;
7. o propósito: as partes servem à mesma frase, ou é um monte de código junto,
   cada um com um propósito desconexo do outro?
8. a sensação prometida está lá;
9. você usaria, pagaria, mostraria para alguém?

Sobre o item 8: se o produto promete que a areia esparrama com a passagem do caça
ultrassônico, a pergunta não é "o efeito de partículas foi implementado?". É:
**olhando, parece areia sendo deslocada por uma massa de ar em alta velocidade?**
Se o avaliador precisou ser informado do que deveria estar vendo para perceber,
a sensação **não está lá**.

## Artigo 6 — A prova é ligada a esta versão

Toda prova — selo, revisão, laudo de bancada — vale para o **fingerprint** do
código no momento em que foi produzida. Qualquer alteração posterior no código de
produto a invalida. Testar e continuar mexendo não é testar.

Provas voláteis também expiram por tempo (TTL).

## Artigo 7 — Quem faz não julga

O fiscal nunca é o executor. Não por desconfiança: por cegueira de autor — quem
construiu a tela vê a intenção, não a tela.

A separação é imposta em duas camadas: o fiscal **não tem** as ferramentas de
escrita (N4), e o gate **consulta o ledger** e rejeita qualquer laudo assinado por
uma sessão que escreveu código de produto (N3). O papel é **derivado do que a
sessão fez**, não declarado por ela.

## Artigo 8 — Sub-agentes

Todo despacho que possa alterar produto carrega o bloco `## CONTRATO DE EXECUÇÃO`
no prompt. Sub-agente **não fecha entrega**: ele produz evidência e reporta.

Relato de sub-agente **não é prova**. Prova é selo, laudo e ledger. Entre a
afirmação de um agente e o disco, o disco ganha sempre.

## Artigo 9 — A válvula

Trabalho que não é entrega pode rodar com a imposição suspensa, ativada **apenas
pelo humano** (`#trava-off <motivo>` no prompt dele, ou `./trava imposicao off` no
terminal dele, que exige TTY).

A suspensão exige motivo, **expira sozinha** e fica registrada. Mesmo suspensa,
continuam valendo: a autoproteção do cofre, o registro forense e a auditoria.

O agente não pode suspender a imposição, e não deve sugerir que o usuário a
suspenda para conseguir entregar. Isso é contornar por procuração.

## Artigo 10 — Auditoria

Todo evento é registrado, linha a linha, numa cadeia encadeada por hash
(`.trava/auditoria.jsonl`), com espelho legível em `AUDITORIA.md`. Editar ou
remover qualquer linha quebra a cadeia e é detectado por
`./trava auditoria --verificar`.

Toda escrita guarda a **imagem-anterior** do arquivo, o que torna o rollback real
e a pergunta "o que este agente mudou?" respondível sem arqueologia.

## Artigo 11 — Integridade do mecanismo

É proibido ao agente: escrever em `.trava/`, ler a chave de assinatura, alterar
hooks, settings, agentes ou comandos, e criar caminhos alternativos de entrega que
contornem a porta única.

Mudança na trava é trabalho do humano, em commit separado do código de produto.

## Artigo 12 — Falha fecha

Erro interno, dependência ausente, contrato corrompido ou dúvida sobre o estado
resolvem-se como **NEGADO** no gate de segurança — e como **liberado com registro**
no gate de conclusão, porque ali o risco invertido é prender o agente para sempre.
Cada hook declara a sua política no cabeçalho.

Ausência de prova nunca é prova de ausência de problema.

---

## A declaração exigida ao fim de todo trabalho que toca produto

Não escreva "pronto". Escreva:

```
ESTADO: ENTREGUE | NÃO ENTREGUE
PROVAS: <selos válidos> · fiscal: <veredito> · bancada: <duração, veredito>
O QUE NÃO FOI VERIFICADO: <explícito>
PENDÊNCIAS: <o que falta e o que impede>
```

Se você não consegue preencher essas linhas com fatos que estão no disco, o
trabalho não está entregue — e dizer que está é a única falha que este mecanismo
considera grave.
