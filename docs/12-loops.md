# 12 — Os loops: interno, externo e o loop do raciocínio

> Confundir o loop interno com o externo é a causa de metade das entregas ruins.
> Gente rodando o loop interno, chamando de entrega, e ficando genuinamente
> surpresa quando o usuário reclama.

## 1. Os dois loops

```
┌───────────────────────────────────────────────────────────────────────┐
│ LOOP INTERNO        rápido · barato · SEU · dezenas de voltas por hora │
│                                                                        │
│   escrever ──► rodar ──► ler o erro ──► corrigir ──► rodar ──► …      │
│                                                                        │
│   provas:    compila · testes passam · lint limpo · tipos batem       │
│   responde:  "o código está certo?"                                   │
│   trava:     ./trava selo emitir <nome>                               │
│   fecha em:  segundos a minutos                                       │
└───────────────────────────────────────────────────────────────────────┘
                                   │
                    o loop interno NUNCA conclui uma entrega
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│ LOOP EXTERNO      lento · caro · DE OUTROS · 1 a 3 voltas por entrega  │
│                                                                        │
│   construir ──► FISCAL revisa ──► BANCADA humana usa ──► veredito     │
│        ▲                                                    │          │
│        └────────────────── REPROVADO ───────────────────────┘          │
│                                                                        │
│   provas:    revisão com lastro · laudo de bancada · doc revisada     │
│   responde:  "isto serve para alguém?"                                │
│   trava:     ./trava entregar                                         │
│   fecha em:  horas a dias                                             │
└───────────────────────────────────────────────────────────────────────┘
```

O loop interno prova que **o código faz o que o código diz**. É indispensável e é
barato. Mas a pergunta da entrega é outra: se aquilo **tem propósito**, se é
**confortável**, se **convida**, se a sensação prometida **está lá**.

Nenhuma quantidade de voltas no loop interno responde a pergunta do externo.

## 2. Como o kit separa os dois mecanicamente

| | Loop interno | Loop externo |
|---|---|---|
| gatilho | `Bash(git push\|commit)` | `Bash(git tag\|npm publish\|deploy…)` |
| hook | `trava_gate.py` | `trava_entrega.py` |
| verificação | selo com `estrito: true` (re-executa) | selos + doc + **bancada humana** |
| veredito | `deny` até o selo existir | `deny` → `deny` → **`ask` ao usuário** |
| quem libera | o próprio comando de teste | uma pessoa |

A separação não é conceitual — são dois hooks diferentes, em dois gatilhos
diferentes, com critérios diferentes. Você não consegue satisfazer um com o outro.

## 3. O loop do raciocínio (chain of thought verificável)

O terceiro loop, o que acontece dentro da cabeça do agente, tem um problema:
**ele não deixa rastro verificável**. O agente raciocina, conclui, e o que chega
no disco é a conclusão — nunca o caminho.

O kit não tenta ler o raciocínio. Ele faz uma coisa mais barata e mais robusta:
**força o raciocínio a virar artefato, e depois confronta o artefato com o mundo.**

```
   afirmação do agente             confronto mecânico
   ───────────────────             ──────────────────
   "rodei os testes"        →      o selo só nasce de rc==0 (emitir_selo)
   "revisei o código"       →      ≥2 referências arquivo:linha que EXISTEM
   "a revisão está atual"   →      mtime da revisão > mtime do código
   "a tela está boa"        →      laudo com 9 respostas distintas e não-genéricas
   "o efeito funciona"      →      delta entre frames do vídeo > 0
   "documentei"             →      docs mais novos que o código, caminhos existem
   "eu não escrevi isso"    →      ledger diz quem escreveu
```

> **O padrão:** para cada afirmação que importa, existe um confronto mecânico que
> a contradiz quando ela é falsa. Não se verifica o raciocínio; verifica-se a
> **consequência** dele no mundo.

Essa é a razão de `verificar_revisao.py` exigir `arquivo:linha` reais. Não é
burocracia de formato: é impossível produzir duas referências válidas sem ter
aberto o código. O artefato carrega a evidência do processo que o gerou.

### O que isso não cobre, e é honesto dizer

Um agente pode abrir o código, citar duas linhas corretas e ainda assim revisar
mal. O confronto mecânico elimina a **fraude fácil** e a **omissão**; não garante
**qualidade de julgamento**. Para isso existe o passo seguinte, que é humano.

## 4. Fusível, contador e escada — como o loop termina

Todo loop precisa de um jeito de acabar, senão ele mesmo vira o bug. São **quatro**
mecanismos, e você precisa de pelo menos dois:

### (a) Fusível `stop_hook_active` — obrigatório
```python
if p.get("stop_hook_active"):
    sys.exit(0)   # já estamos num turno causado por bloqueio anterior
```
**A maior causa de loop infinito de agente é bloquear `Stop` sem checar isto.**

### (b) Contador de reentrada
```python
n = T.incrementar(f"stop_{sessao}")
if n > regra.get("max_reentradas", 3):
    T.avisar("Encerramento liberado após N tentativas SEM as provas. "
             "Revise manualmente — a entrega NÃO foi verificada.")
```
A trava **cede e escala**. Um agente preso não resolve nada; um usuário informado
resolve. E o evento fica no ledger como `cedido` — uma entrega marcada como não
verificada é um resultado ruim, mas é um resultado **conhecido**.

### (c) Teto global do loop executor↔fiscal
```json
"loop": { "max_rodadas": 6 }
```
Sem isto os dois jogam ping-pong até o limite de tokens: o fiscal reprova, o
executor ajusta, o fiscal reprova outra coisa. Ao estourar: `loop_estourado`,
liberação com aviso, decisão humana.

### (d) TTL da prova
Selo expira. Bancada expira por fingerprint. Prova velha é mentira lenta.

## 5. Como fazer o loop externo convergir em 1–2 voltas

O loop externo é caro. Cada volta consome tempo de gente. Práticas que encurtam:

| Prática | Efeito |
|---|---|
| `SessionStart` injeta o estado e as pendências | o agente não descobre a trava no fim |
| mensagem de bloqueio com **comando literal** | ele corrige a causa certa, não chuta |
| rodar as mecânicas **antes** de chamar o humano | ninguém é chamado para tela quebrada |
| operador faz triagem antes da bancada | os tropeços óbvios morrem antes |
| tarefas de usuário, não passos de teste, no roteiro | o laudo pega o que importa |
| `REPROVADO` com achado específico e reproduzível | uma volta resolve, não três |

> **Heurística para a mensagem de bloqueio:** se ela não contém um **fato medido**,
> um **comando executável** e um **caminho de arquivo**, ela ainda não está pronta.
> "Validação falhou. Corrija e tente novamente." garante mais uma volta.

## 6. Interação com a compactação de contexto

Sessões longas compactam, e o contexto evapora. Por isso **o estado do loop não
mora no contexto** — mora no disco, e é relido a cada hook:

- o contador de reentrada está em `.trava/contadores/`;
- o papel está em `.trava/contexto/`;
- a bancada está em `.trava/bancada/`;
- o `UserPromptSubmit` **republica o contrato vivo a cada turno**, lido do disco.

Se a sua trava depende de o modelo lembrar, ela morre na primeira compactação.
Esta não depende: cada hook recomputa tudo do zero, toda vez.

## 7. O antipadrão central

```python
❌ if n >= 3: sys.exit(0)   # "já tentou bastante, libera"
```

Isto converte a trava em **atraso de três turnos**. Um agente que aprende o padrão
passa a gastar três turnos e entregar. A diferença entre isto e o item (b) acima é
uma linha:

```python
✅ if n > maximo:
       T.avisar("liberado SEM as provas — a entrega NÃO foi verificada")
```

Liberar em silêncio é um bug. Liberar **gritando, com registro no ledger e a
entrega marcada como não verificada**, é uma válvula. **Insistência não é prova.**

---

➡️ Próximo: [13 — Comandos, skills e agentes](13-comandos-skills-agentes.md)
