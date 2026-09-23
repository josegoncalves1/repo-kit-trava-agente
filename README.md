# TRAVA-KIT

**Travas reais para agentes e LLMs — mecanismos que bloqueiam de verdade, e que
obrigam toda entrega a passar por um teste humano de experiência real.**

```bash
cd /seu/projeto
curl -fsSL https://raw.githubusercontent.com/josegoncalves1/repo-kit-trava-agente/main/setup.sh | sh
```

Instala na raiz do projeto, convivendo com o que já existe. Requisito único:
`python3`. Nenhuma dependência externa.

---

## A frase que resume tudo

> **Eu, o modelo, não travo nada. Eu *escrevo* a trava. Quem trava é o runtime.**

Uma instrução em prompt (*"você NÃO PODE fazer X"*) é uma **preferência**: depende
de o modelo ler, lembrar e querer obedecer. Em cadeia longa, sob compactação de
contexto, ou com um sub-agente que nasceu sem aquele parágrafo, ela falha — e
falha **em silêncio**.

Uma trava real é um **programa externo ao modelo**, que o runtime executa *antes*
da ação, que lê **estado em disco** (não a narrativa da conversa), e cuja resposta
é um **código de saída que o runtime obedece**. O modelo pode discordar,
argumentar ou esquecer: a chamada não acontece do mesmo jeito.

## E a segunda frase, que é a razão deste kit existir

> **Testar é sentar a bunda na cadeira, pegar mouse e teclado com as duas mãos,
> olhar para o monitor e usar.** Operar, sentir, perceber, observar — e sair de lá
> com uma opinião.

Não é `curl 200`. Não é "está no ar". Não é "os testes passaram". Isso prova que
um processo respondeu; não prova que alguém consegue usar aquilo, nem que valha a
pena.

É perceber. É saber, olhando, se o almoço está sendo servido ao meio-dia ou à
meia-noite. É distinguir o chato do legal, o feio do bonito, o que convida do que
afasta — correlacionando, sem conta de mais ou de menos, com um mundo inteiro de
contexto em volta.

**Nenhum programa faz isso. Este kit não finge que faz.**
Ele torna **impossível pular** quem faz.

> A assimetria é deliberada: **a máquina pode REPROVAR, só o humano pode APROVAR.**

---

## O que você ganha

| | O quê |
|---|---|
| 🔒 **Travas que bloqueiam** | hooks `PreToolUse`/`Stop`/`SubagentStop` que cancelam a chamada — não avisam, cancelam |
| 🪑 **Bancada humana obrigatória** | nenhuma entrega final sem uma pessoa sentar, usar e escrever o que achou |
| 🧾 **Selos assinados** | "eu validei" não emite selo; **rodar** emite. HMAC + TTL + re-execução em modo estrito |
| 👥 **Executor ≠ fiscal** | garantido por toolset (N4) **e** por ledger: quem escreveu produto não assina o laudo |
| 📓 **Auditoria encadeada** | NDJSON com hash-chain + espelho legível em `AUDITORIA.md`, linha a linha |
| 🕵️ **Forense e rollback** | imagem-anterior de todo arquivo tocado, por sessão. Desfazer sem git |
| 🔁 **Loops com fusível** | contador de reentrada, teto de rodadas, saída honrosa — cede e **escala**, nunca prende |
| 🎛️ **Ligar/desligar auditado** | `/trava-status`, `#trava-off <motivo>` — com prazo, motivo e registro |
| 📚 **Skills, comandos e agentes** | prontos: entrega, bancada, equipe · 6 slash commands · 4 papéis |
| 🧪 **22 provas automáticas** | a bateria que prova que a trava trava, antes de você confiar nela |

---

## Como funciona, em 60 segundos

1. **Estado fora da conversa.** A verdade sobre "a etapa foi concluída?" mora em
   `.trava/` no disco — não no histórico do chat. O modelo não reescreve o
   passado nem convence um arquivo.

2. **Selo = prova assinada de uma verificação que de fato rodou.** Emitir um selo
   executa o comando (`npm test`, `pytest -q`, `./validar.sh`), grava o código de
   saída e o hash da saída, e assina com HMAC. **Declarar não emite selo.**

3. **Gatilho obrigatório.** Um hook `PreToolUse` roda antes de *toda* chamada que
   casa com o matcher. Não é opcional, não é lembrado: é executado.

4. **Veredito obedecido.** O hook responde `permissionDecision: "deny"`. O runtime
   **cancela a chamada**. A ferramenta não roda.

5. **Trava de saída.** `SubagentStop` bloqueia o encerramento sem prova. Não
   existe "entreguei pela metade".

6. **Trava de entrega, em três estágios.**
   mecânico (`deny`) → **bancada humana** (`deny`) → **`ask` ao usuário**.
   O `ask` devolve a decisão ao canal do usuário no runtime, onde o agente não
   alcança. **A prova de humano não está no conteúdo — está no canal.**

7. **Válvula e anti-loop.** Fusível `stop_hook_active`, contador de reentrada,
   TTL e liberação auditada. Sem isso, a trava vira loop infinito — que é o modo
   de falha nº 1.

---

## Os documentos

Leia nesta ordem se você é novo aqui. Se tem pressa: **[09](docs/09-o-que-e-testar.md)** e **[14](docs/14-instalacao.md)**.

| # | Documento | Responde |
|---|---|---|
| 0 | [A tese](docs/00-tese.md) | por que frase não trava. A Escala de Dureza N0→N4 |
| 1 | [O mecanismo: hooks](docs/01-mecanismo-hooks.md) | **referência técnica**: eventos, payload, exit codes, JSON |
| 2 | [Anatomia da trava](docs/02-anatomia-da-trava.md) | os 6 órgãos. Como projetar uma do zero |
| 3 | [Travas de sub-agente](docs/03-travas-de-subagente.md) | os 4 pontos de controle de um sub-agente |
| 4 | [Receitas](docs/04-receitas.md) | 10 travas prontas, copiáveis |
| 5 | [Travas sem hook (N4)](docs/05-travas-sem-hook.md) | toolset, `permissions.deny`, container, credencial ausente |
| 6 | [Portabilidade](docs/06-portabilidade.md) | **usar isto num agente que não tem hooks** |
| 7 | [Antipadrões](docs/07-antipadroes.md) | o que parece trava e não é. Como vira deadlock |
| 8 | [Provar que trava](docs/08-provar-que-trava.md) | as 6 provas obrigatórias, antes de confiar |
| 9 | **[O que é testar](docs/09-o-que-e-testar.md)** | **o coração do kit.** Por que isto não se automatiza, e como conduzir a bancada |
| 10 | [Papéis e equipe](docs/10-papeis-e-equipe.md) | executor, fiscal, operador, auditor — e por que o fiscal nunca é o executor |
| 11 | [Auditoria, forense, rollback](docs/11-auditoria-forense-rollback.md) | ledger encadeado, imagem-anterior, investigar incidente |
| 12 | [Os loops](docs/12-loops.md) | interno, externo, e o loop do raciocínio verificável |
| 13 | [Comandos, skills, agentes](docs/13-comandos-skills-agentes.md) | o que é orientação e o que é trava. Como acrescentar |
| 14 | [Instalação](docs/14-instalacao.md) | o que é extraído, o que o setup faz, como atualizar |
| 15 | [Modelo de ameaças](docs/15-modelo-de-ameacas.md) | **onde isto falha.** Leia antes de confiar |
| — | [Contrato de entrega](payload/CONTRATO-DE-ENTREGA.md) | o texto vinculante, portátil, para agente e humano |

---

## O que é instalado

```
/seu/projeto/                  ← seu Dockerfile, src/, scripts/ continuam aqui
├── trava                      o CLI
├── AUDITORIA.md               histórico legível, linha a linha
├── CONTRATO-DE-ENTREGA.md     o contrato
├── output/  evidencias/       relatórios, laudos, capturas
├── .trava/                    cofre: contrato, selos, ledger, forense, bancada
└── .claude/
    ├── settings.json          ← FUNDIDO, com backup datado
    ├── hooks/                 os executores das travas
    ├── agents/                executor · fiscal · operador · auditor-doc
    ├── commands/              /trava-status /trava-off /trava-bancada …
    └── skills/                entrega · bancada · equipe
```

Detalhes em [14 — Instalação](docs/14-instalacao.md).

## Uso diário

```bash
./trava status        # o que está sendo imposto agora
./trava doutor        # a trava está viva, ou é enfeite?
./trava selo listar   # o que falta provar
./trava bancada abrir # prepara o teste humano
./trava entregar      # a porta única da entrega final
./trava auditoria     # histórico; --verificar checa a cadeia
./trava forense       # o que foi tocado, e por quem
```

De dentro do agente: `/trava-status`, `/trava-bancada`, `/trava-entregar`,
`/trava-auditoria`, `/trava-rollback`, `/trava-off`.

---

## Modelo de ameaça (leia antes de confiar)

| Contra o quê | Protegido? | Por qual camada |
|---|---|---|
| agente que **esquece** a regra | ✅ | hook: o runtime executa, não o modelo lembra |
| sub-agente que **nunca viu** a regra | ✅ | hook vale na sessão inteira, inclusive sidechains |
| agente que **declara** sem ter feito | ✅ | selo re-executa a verificação |
| **"curl 200, então está bom"** | ✅ | bancada humana obrigatória |
| **quem fez julgando o próprio trabalho** | ✅ | toolset restrito + papel derivado do ledger |
| **prova vencida** (validou e continuou codando) | ✅ | fingerprint + TTL + revogação no PostToolUse |
| **laudo humano escrito pelo agente** | ✅ alto | sessão registrada + tempo mínimo + `ask` + TTY |
| **adulteração da auditoria** | ⚠️ detectável | hash-chain: não impede, **acusa** |
| agente **adversário com shell**, que apaga `.trava/` | ⚠️ **não** | só N4: usuário separado, container `:ro`, credencial ausente, CI |

O HMAC é **anti-deriva e anti-atalho**, não anti-adversário-com-root. A trava
inviolável é sempre a estrutural: o agente não consegue porque **não tem** a
ferramenta, a permissão ou a credencial — não porque foi proibido.
Ver [05](docs/05-travas-sem-hook.md) e [15](docs/15-modelo-de-ameacas.md).

---

## O passo que só você pode dar

**Reinicie a sessão do agente depois de instalar.** Hooks são capturados na
inicialização; até lá, **nada está ativo** — e a falha é silenciosa.

Depois, prove:

```bash
bash .trava/bin/testar_travas.sh
#   22 corretos, 0 falhos
#   ✅ TRAVAS VALIDADAS
```

> Uma trava não testada é uma **suposição de segurança** — e é pior que não ter
> trava, porque produz confiança sem proteção.

E lembre da distinção que mais custa caro:

> **"Instalado" não é "protegido".** Os hooks podem estar ativos com o contrato
> vazio, e aí nada é bloqueado. `./trava doutor` diz qual dos dois você tem.
