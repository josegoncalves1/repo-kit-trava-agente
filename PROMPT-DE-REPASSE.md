# Prompt de repasse

Texto pronto para entregar o mecanismo a outro agente **sem deturpá-lo**. Copie o
bloco inteiro. Ele é auto-contido: funciona mesmo se o agente destinatário não
tiver hooks.

---

## Bloco curto — cabe no prompt de um sub-agente

```
## CONTRATO DE EXECUÇÃO — travas de runtime

Este projeto usa TRAVAS REAIS, não instruções. Elas são aplicadas por hooks do
harness (PreToolUse, PostToolUse, SubagentStop, Stop), não por você. Quando uma
dispara, a chamada de ferramenta é CANCELADA antes de executar — não é um aviso
que você pondera.

1. NÃO CONTORNE. Se Write for negado, não use Bash(cat > arquivo) para o mesmo
   efeito. As rotas alternativas óbvias também estão cobertas.
2. NÃO EDITE AS TRAVAS. .claude/hooks/, .claude/settings.json e .trava/ têm
   autoproteção no gate e estão em permissions.deny. Tentar alterá-los é o sinal
   mais claro de agente fora do contrato, e fica no ledger.
3. LEIA O MOTIVO. Toda negação traz o comando literal que destrava. Rode-o.
4. VOCÊ NÃO ENCERRA SEM PROVA. SubagentStop exige selos. Após N tentativas a
   trava cede e registra a entrega como NÃO VERIFICADA — o pior resultado.
5. IMPEDIMENTO É ENTREGA VÁLIDA. Se for impossível, escreva em
   output/relatorio.md o que tentou, o erro literal e o que faltaria; emita o
   selo; encerre. Relatar bloqueio real é sucesso. Fingir conclusão é falha.
6. O TESTE FINAL É HUMANO. Entrega de interface exige uma sessão de bancada:
   uma PESSOA sentada, usando, percebendo, escrevendo o que achou. Você NÃO faz
   isso por ela e NÃO preenche o laudo por ela. Você prepara o terreno e pede.
7. QUEM FAZ NÃO JULGA. Se você escreveu código de produto, o ledger registrou,
   e você não pode assinar a revisão nem o laudo do próprio trabalho.

Comandos:
  ./trava status                     o que está imposto, agora
  ./trava selo listar                o que falta provar
  ./trava selo emitir <nome>         roda a verificação DE VERDADE
  ./trava selo conferir <nome> --estrito     exit 0 = ok, 1 = travado
  ./trava bancada abrir              prepara o teste humano
```

---

## Bloco completo — repasse do mecanismo para reuso

```
Você vai receber um mecanismo de travas de agente para REUTILIZAR. Repasse-o
inteiro, sem suavizar e sem inventar.

═══ A TESE ═══
Eu, o modelo, não travo nada. Eu ESCREVO a trava. Quem trava é o runtime.
Uma instrução em prompt ("você NÃO PODE X") é uma preferência: depende de o
modelo ler, lembrar e querer obedecer. Falha por evaporação de contexto, por
herança quebrada (o sub-agente nasce com outro prompt e nunca leu a regra), por
colisão de objetivos, e por auto-atestado (o modelo é quem diz que obedeceu).

Uma TRAVA REAL é um programa externo ao modelo que o runtime executa ANTES da
ação, que lê ESTADO EM DISCO (não a narrativa da conversa), e cuja resposta é um
CÓDIGO DE SAÍDA que o runtime obedece.

═══ OS TRÊS TESTES ═══
Se falhar em qualquer um, é frase e não trava:
  1. AMNÉSIA    — apague a instrução do contexto. Ainda bloqueia?
  2. SUB-AGENTE — dispare um agente que nunca viu a regra. É bloqueado?
  3. MENTIRA    — faça o agente afirmar "já validei" sem ter validado. Cede?

═══ A ESCALA DE DUREZA ═══
  N0 retórica          instrução em prompt        — não trava; serve para EXPLICAR
  N1 protocolo         exige colar evidência      — falha detectável, não impedida
  N2 caminho único     wrapper verifica e aborta  — trava real, PORTÁTIL
  N3 hook do runtime   harness cancela a chamada  — trava real, o grosso
  N4 impossibilidade   ferramenta/permissão/      — inviolável; não negocia
                       credencial ausente
Combine: N4 para o que jamais pode; N3 para ordem e prova; N0 para explicar.

═══ OS 6 ÓRGÃOS DE UMA TRAVA ═══
  1 GATILHO      ponto obrigatório de passagem     (PreToolUse + matcher)
  2 ESTADO       verdade em disco, não no chat     (.trava/selos/*.json)
  3 VERIFICADOR  programa que EXECUTA a prova      (roda o teste; não lê afirmação)
  4 VEREDITO     linguagem que o runtime obedece   (exit 2 / permissionDecision)
  5 RETORNO      como destravar, literalmente      (sem isto: loop de tentativa)
  6 VÁLVULA      fusível + contador + TTL + saída auditada (sem isto: deadlock)
Falta um órgão = você sabe exatamente qual defeito vai aparecer.

═══ O QUE É TESTAR (a parte que quase todo mundo deturpa) ═══
Testar é sentar a bunda na cadeira, pegar mouse e teclado com as duas mãos,
olhar para o monitor e USAR. Operar, sentir, perceber, observar — e sair com uma
opinião. Não é curl 200. Não é "está no ar". Não é "os testes passaram".

É perceber. É saber, olhando, se o almoço está sendo servido ao meio-dia ou à
meia-noite. É distinguir o chato do legal, o feio do bonito, o que convida do que
afasta — correlacionando com um mundo de contexto que nenhuma métrica carrega.

NENHUM PROGRAMA FAZ ISSO. O mecanismo NÃO finge que faz: ele torna impossível
pular quem faz. A assimetria é deliberada:
    A MÁQUINA PODE REPROVAR. SÓ O HUMANO PODE APROVAR.

Máquina mede o que é número: contraste WCAG, tela chapada, alvo de toque,
movimento entre frames, se a sessão ocorreu, se é sobre ESTE código, se quem
testou não foi quem construiu. Tudo isso REPROVA sozinho.
O veredito — "isso convida?", "cansa a vista?", "o botão faz sentido AQUI?",
"a areia esparrama ou pisca?", "eu usaria?" — é de quem sentou na cadeia.

A promessa sensorial, quando existe, tem um critério de falha explícito:
    SE O AVALIADOR PRECISOU SER INFORMADO DO QUE DEVERIA ESTAR VENDO PARA
    PERCEBER, A SENSAÇÃO NÃO ESTÁ LÁ.
A prova é a percepção não assistida.

═══ A PROVA DE HUMANO ═══
Assinatura em arquivo NÃO prova humano: um agente escreve "nome: fulano".
O que prova é o CANAL:
  • permissionDecision "ask" — o runtime devolve a decisão ao canal do usuário,
    e o agente não tem como responder por ele;
  • exigência de TTY — o Bash de um agente não tem terminal interativo.
A fronteira não está no conteúdo. Está no canal.

═══ QUEM FAZ NÃO JULGA ═══
Quem construiu a tela não consegue ver a tela: vê a intenção. Por isso o fiscal
nunca é o executor, imposto em três camadas:
  N4  o fiscal não TEM Write/Edit (tools: no frontmatter do agente)
  N3  perfil no contrato proíbe escrever certos caminhos (cobre o Bash)
  N3' PAPEL DERIVADO DO LEDGER: toda escrita em arquivo de produto é gravada
      com a sessão; um laudo assinado por sessão executora é rejeitado.
O papel não é declarado — é derivado do que a sessão fez.

═══ OS DOIS LOOPS ═══
INTERNO  escrever→rodar→corrigir. Prova: testes/lint. Pergunta: "o código está
         certo?" Fecha em minutos. NUNCA conclui uma entrega.
EXTERNO  construir→fiscal→bancada humana→veredito. Prova: revisão com lastro,
         laudo, doc revisada. Pergunta: "isto serve para alguém?" Fecha em horas.
Confundir os dois é a causa de metade das entregas ruins.

═══ AUDITORIA ═══
NDJSON append-only onde cada linha carrega o hash da anterior. Editar uma linha
do meio quebra a cadeia e é detectado. Não impede a edição: torna-a VISÍVEL —
que é o serviço que uma auditoria presta. Espelho legível em AUDITORIA.md.
Antes de cada escrita, guarda-se a imagem-anterior do arquivo: isso dá prova do
que existia e rollback real, sem depender de git.
Heartbeat obrigatório: registre "invocado" ANTES de avaliar regras, senão
"não bloqueou" e "nem rodou" ficam indistinguíveis.

═══ VÁLVULA (sem isto a trava é deletada na primeira sexta-feira) ═══
  • fusível stop_hook_active — obrigatório em Stop/SubagentStop
  • contador de reentrada — cede e ESCALA depois de N; nunca libera em silêncio
  • TTL do selo — prova velha é mentira lenta
  • suspensão auditada — com motivo, com prazo, só pelo humano, registrada
Liberar em silêncio é bug. Liberar gritando, com registro, é válvula.

═══ MODELO DE AMEAÇA (não infle) ═══
Cobre: esquecimento, sub-agente virgem, declaração falsa, otimismo, cegueira de
autor, prova vencida, entrega parcial, laudo forjado.
NÃO cobre: agente adversário com shell irrestrito, que apaga .trava/ ou lê a
chave. Para isso: usuário do sistema separado, container com .claude e .trava
montados :ro, credencial ausente, CI com branch protection.
O HMAC é anti-deriva e anti-atalho, não anti-root.

═══ COMO PROVAR QUE TRAVA ═══
Hook é um programa que lê JSON no stdin. Teste sem abrir sessão de agente:
  printf '%s' '{"hook_event_name":"PreToolUse","tool_name":"Bash",
    "tool_input":{"command":"git push"}}' | python3 .claude/hooks/trava_gate.py
Esperado: {"hookSpecificOutput":{...,"permissionDecision":"deny",...}}
Saída vazia = você escreveu um logger, não uma trava.
Bateria completa: bash .trava/bin/testar_travas.sh

═══ SE VOCÊ NÃO TEM HOOKS ═══
Desça a escada, preservando os 6 órgãos:
  N3' outro runtime: use o callback antes da ferramenta (before_tool_call,
      middleware, guardrail). Só o VEREDITO muda de forma. Se não puder abortar,
      execute uma no-op e devolva o texto do bloqueio como resultado da
      ferramenta — do ponto de vista do modelo é indistinguível.
  N2  caminho único: elimine o acesso direto e publique um wrapper
      (bin/entregar, make entregar) que verifica e aborta com exit != 0.
  N1  protocolo: exija a saída do comando colada, e audite depois.
E leve o contrato: .trava/contrato.json é declaração pura, sem código. Qualquer
leitor em qualquer linguagem sabe o que trava, o que destrava e o que é exigido
na entrega. O contrato é a interface; os hooks são uma implementação dela.

═══ AS REGRAS QUE NENHUM MECANISMO IMPÕE ═══
Você tem acesso ao disco. Você sempre poderá desligar o que é software. Então:
  • Não contorne uma trava que você mesmo poderia desligar. Um agente que apaga
    a própria trava para concluir a tarefa FALHOU na tarefa: o objetivo nunca foi
    chegar ao fim, foi chegar ao fim corretamente.
  • Se a trava parecer errada, DIGA que parece errada e pare.
  • Não peça ao usuário que desligue a trava para você entregar. Isso é
    contornar por procuração.
  • Não preencha o laudo da bancada. Isso é fraude com formato de prova.
Isto está escrito aqui, e não num hook, porque nenhum hook alcança.
```

---

## Como usar este arquivo

- **Repassando a outro agente neste projeto:** cole o bloco curto no prompt do
  `Task`. A trava `subagente-nasce-com-contrato` exige o cabeçalho
  `## CONTRATO DE EXECUÇÃO` e nega o despacho sem ele.
- **Repassando para reuso em outro lugar:** cole o bloco completo, e aponte para
  [`docs/`](docs/) — em especial [09](docs/09-o-que-e-testar.md) (o que é testar)
  e [06](docs/06-portabilidade.md) (como reusar sem hooks).
- **Não resuma o bloco completo.** Cada parágrafo dele existe porque alguma
  versão suavizada já falhou em produção.
