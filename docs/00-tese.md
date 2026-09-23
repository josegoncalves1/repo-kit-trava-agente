# 00 — A tese: por que uma frase não trava nada

## 1. O erro fundacional

O erro mais comum ao "travar" um agente é escrever isto no prompt:

```
IMPORTANTE: Você NÃO PODE, SOB NENHUMA HIPÓTESE, escrever código antes de
apresentar o plano. Isso é PROIBIDO. Sempre valide antes de prosseguir.
```

Isso não é uma trava. Isso é um **pedido com tipografia agressiva**.

Ele falha por quatro razões independentes, e basta uma:

1. **Evaporação de contexto.** Em conversa longa, com compactação, o parágrafo some ou
   vira um resumo de uma linha. A regra não está mais lá para ser seguida.
2. **Herança quebrada.** O sub-agente nasce com **outro** prompt de sistema. Ele nunca
   leu sua proibição. Você travou o pai; o filho não sabe de nada.
3. **Colisão de objetivos.** O modelo recebe "não faça X" e "entregue a tarefa completa".
   Quando X é o caminho para completar, a instrução mais recente e mais concreta ganha.
4. **Auto-atestado.** Mesmo obedecendo, o modelo é quem diz que obedeceu. "Validei antes
   de prosseguir" é uma afirmação do próprio réu, sem prova, verificada por ninguém.

O sintoma clássico: o agente escreve *"Não posso prosseguir sem validar."* — e prossegue
no parágrafo seguinte. A recusa era linguagem, não mecanismo.

## 2. Definição operacional de trava

> **Uma trava é real se, e somente se, a ação fica indisponível por um processo que não
> é o modelo, com base em estado que o modelo não redigiu.**

Três testes. Se falhar em qualquer um, você tem uma frase, não uma trava:

- **Teste da amnésia.** Apague a instrução do contexto. A ação continua bloqueada? Se não,
  é frase.
- **Teste do sub-agente virgem.** Dispare um sub-agente que nunca viu a regra. Ele é
  bloqueado? Se não, é frase.
- **Teste da mentira.** Faça o agente afirmar "já validei" sem ter validado. O bloqueio
  cede? Se cede, é frase.

Uma trava real passa nos três porque nenhum deles envolve o modelo. O verificador não lê o
contexto, não lê a asserção, não lê a conversa. Lê o disco.

## 3. A Escala de Dureza (N0 → N4)

Toda restrição de agente cabe num destes cinco degraus. Nomear o degrau é o primeiro passo
de qualquer projeto de trava, porque **você só pode prometer o que o degrau entrega**.

### N0 — Retórica
*"Não faça X."* Instrução em prompt, regra em CLAUDE.md, convenção documentada.
- **Quem aplica:** o modelo, por boa vontade.
- **Falha quando:** contexto some, sub-agente novo, objetivo conflita.
- **Uso legítimo:** comunicar *intenção* e *como destravar*. Nunca como única barreira.

### N1 — Protocolo com evidência
*"Não faça X sem colar a saída de `pytest`."* Ainda depende do modelo, mas agora existe
artefato inspecionável por um terceiro (humano, revisor, outro agente).
- **Quem aplica:** o modelo, mas auditável depois.
- **Falha quando:** ninguém audita; ou o agente fabrica a saída.
- **Ganho real sobre N0:** transforma falha silenciosa em falha detectável.

### N2 — Caminho único instrumentado
A ação só é alcançável por um wrapper que verifica antes. O agente não chama `git push`;
chama `./bin/entregar`, que roda os testes e aborta com código ≠ 0 se falharem.
- **Quem aplica:** o wrapper (um programa).
- **Falha quando:** existe caminho alternativo (o agente chama `git push` direto).
- **Esta é a camada portátil** — funciona em qualquer runtime, qualquer agente, sem hooks.

### N3 — Interceptação pelo runtime (HOOK)
O runtime executa um verificador **antes de toda** chamada de ferramenta e obedece ao
veredito. Não existe caminho alternativo dentro do conjunto de ferramentas do agente.
- **Quem aplica:** o runtime do agente (Claude Code, via hooks).
- **Falha quando:** o agente tem shell e destrói o próprio estado da trava.
- **É o assunto principal deste repositório.**

### N4 — Impossibilidade estrutural
A ação não é possível. A ferramenta não existe no toolset do agente; a permissão está em
`deny`; a credencial não está na máquina; o arquivo está `chmod 444`; o filesystem está
montado somente-leitura; a rede está bloqueada.
- **Quem aplica:** o sistema operacional / o harness / a ausência física do recurso.
- **Falha quando:** ~nunca, dentro do escopo do agente.
- **Custo:** rigidez. N4 não negocia, não explica e não tem válvula.

### Regra de combinação

```
N4  para o que jamais pode acontecer        (destrutivo, irreversível, exfiltração)
N3  para o que pode acontecer, na ordem certa, com prova  (o grosso do trabalho)
N2  para o que precisa funcionar fora do Claude Code      (CI, outro runtime, humano)
N1  para o que precisa de julgamento humano
N0  para EXPLICAR ao agente o que N4/N3/N2 estão fazendo e como destravar
```

N0 não é inútil — é a **camada de comunicação**. Sem ela, o agente bate numa parede sem
saber o que fazer e entra em loop de tentativa. Com ela, ele lê "falta o selo `testes-verdes`,
emita com `./trava selo emitir testes-verdes`" e resolve. **A trava é N3; a saída é N0.**

## 4. Onde mora a verdade

O deslocamento conceitual que faz tudo funcionar:

| | Sistema frágil | Sistema travado |
|---|---|---|
| Onde está o estado | no histórico da conversa | em arquivo no disco |
| Quem escreve o estado | o modelo, narrando | um verificador, executando |
| Quem lê para decidir | o modelo | um processo externo |
| Como o "não" é expresso | texto gerado | código de saída / JSON de veredito |
| O que acontece no "não" | o modelo decide o que fazer | a chamada de ferramenta é cancelada |
| Efeito de esquecer | perde a regra | nenhum — a regra não estava na memória |

Tudo neste repositório é a implementação dessa tabela.

## 5. O que NÃO é objetivo

- **Não é aprisionar o agente.** Uma trava sem saída documentada produz loop, não
  segurança. Cada trava aqui carrega a instrução exata de destravamento.
- **Não é substituir revisão humana.** Travas garantem *ordem e prova*, não *acerto*.
  Um selo `testes-verdes` prova que os testes passaram, não que os testes são bons.
- **Não é defesa contra agente adversário com root.** Ver o modelo de ameaça no README.

---

Próximo: [01-mecanismo-hooks.md](01-mecanismo-hooks.md) — a referência técnica do N3.
