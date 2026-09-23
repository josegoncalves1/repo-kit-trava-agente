# 13 — Comandos, skills e agentes: o que é orientação e o que é trava

> Um erro comum ao ler este kit: achar que o slash command **é** a trava. Não é.
> Comandos e skills são **superfície**; a trava roda embaixo, mesmo que ninguém
> chame comando nenhum.

## 1. A tabela que resolve a confusão

| Artefato | Onde | Quem executa | Trava? |
|---|---|---|---|
| **hook** | `.claude/hooks/*.py` | o **runtime**, antes da ação | ✅ **sim** |
| `permissions.deny` | `.claude/settings.json` | o **harness**, antes do hook | ✅ **sim** (N4) |
| `tools:` do agente | `.claude/agents/*.md` | o **harness**, ao criar o sub-agente | ✅ **sim** (N4) |
| **CLI** `./trava` | `.trava/bin/trava` | quem digitar | ⚠️ só o que exige TTY |
| **skill** | `.claude/skills/*/SKILL.md` | o **modelo**, por leitura | ❌ orientação |
| **slash command** | `.claude/commands/*.md` | o **modelo**, por leitura | ❌ orientação |
| `CONTRATO-DE-ENTREGA.md` | raiz | o **modelo**, por leitura | ❌ orientação |

As três últimas linhas são **N0** ([00-tese.md](00-tese.md)). E N0 não é inútil —
é a camada de comunicação. Sem ela o agente bate numa parede sem saber o que
fazer e entra em loop de tentativa. Com ela, ele lê "falta o selo X, emita com
`./trava selo emitir X`" e resolve.

> **A trava é N3/N4. A saída é N0.** Use as duas. Só a primeira gasta ciclos à
> toa; só a segunda é esperança.

## 2. Os slash commands

Instalados em `.claude/commands/`. O usuário digita `/nome`.

| Comando | Para quê |
|---|---|
| `/trava-status` | **mostra o que está sendo imposto** — travas, selos, bancada, imposição, integridade |
| `/trava-on` · `/trava-off` | **ativa/desativa a imposição** (o comando orienta; quem muda é o humano) |
| `/trava-bancada` | prepara o teste humano e entrega o roteiro à pessoa |
| `/trava-entregar` | a porta única da entrega final |
| `/trava-auditoria` | histórico linha a linha + verificação da cadeia |
| `/trava-rollback` | lista o rastro forense e orienta o rollback |

### Por que `/trava-off` não desliga nada sozinho

Este é o ponto de projeto mais importante da seção. O arquivo
`.claude/commands/trava-off.md` é um **prompt**, lido pelo modelo. Se ele
simplesmente rodasse `./trava imposicao off`, o agente desligaria a própria trava
— e aí não existe trava nenhuma.

Então o comando faz outra coisa: **ensina o usuário a desligar**, e explica o que
continua valendo. Os dois caminhos reais são:

```
1. no prompt do usuário:    #trava-off <motivo com 10+ caracteres>
2. no terminal do usuário:  ./trava imposicao off --motivo "..." --minutos 60
```

O primeiro é capturado pelo hook `UserPromptSubmit`, que é **o único ponto do
runtime onde chega texto digitado pela pessoa**. Um agente não consegue emitir um
`UserPromptSubmit`. O segundo exige **TTY**, que o `Bash` do agente não tem.

> **A fronteira não está no conteúdo — está no canal.** Qualquer coisa que o
> agente possa escrever, ele escreve. O que ele não pode é *ser o usuário*.

E mesmo suspensa, continuam valendo: a autoproteção do cofre, o registro forense
e a auditoria. A suspensão expira sozinha (padrão 60 min, teto 240) e fica em
`AUDITORIA.md` com o motivo — é assim que se percebe, semanas depois, que a
válvula virou o caminho.

### Anatomia de um comando bem escrito

O frontmatter declara a descrição e restringe as ferramentas; o corpo é o prompt.
Linhas iniciadas por `!` com o comando entre crases são executadas e a saída é
injetada.

```markdown
---
description: uma linha, aparece na lista de comandos
allowed-tools: Bash(./trava status), Bash(./trava doutor)
---

(aqui vai a linha de execução: "!" seguido do comando entre crases)

Depois responda em no máximo 6 linhas:
1. ...
2. Se for zero, diga com todas as letras: os hooks rodam mas nada bloqueia.
```

Três regras aprendidas escrevendo estes:

1. **Restrinja `allowed-tools`** ao que o comando realmente precisa. Um comando de
   leitura com `Bash` irrestrito é uma porta aberta com placa de "só consulta".
2. **Diga o que fazer com o resultado**, não só o que rodar. Sem isso o agente
   despeja a saída bruta e o usuário faz a análise sozinho — que era o serviço.
3. **Proíba a suavização explicitamente.** "Não amenize: um diagnóstico suavizado
   é pior que nenhum, porque produz confiança sem proteção." Sem essa linha, o
   modelo arredonda para o lado otimista.

## 3. As skills

Instaladas em `.claude/skills/<nome>/SKILL.md`. O modelo as carrega quando a
`description` casa com o que está acontecendo — então a **description é o
gatilho**, e escrevê-la mal é o mesmo que não ter a skill.

| Skill | Dispara quando | Contém |
|---|---|---|
| `trava-entrega` | tarefa declarada concluída, "entregar", "publicar", "deploy", antes de `git tag`/`npm publish` | os dois loops, a ordem obrigatória das provas, o que fazer quando cada uma falha |
| `trava-bancada` | validar experiência real, UX/UI, jogo, sensação, conforto visual, "testar de verdade" | o que é testar, como preparar, as 9 perguntas, o que o verificador cobra |
| `trava-equipe` | despachar sub-agentes, organizar frentes, revisão cruzada | os 4 papéis, a coreografia, as 5 regras de despacho |

### Como escrever a `description`

```yaml
# ❌ genérico demais: nunca dispara, ou dispara sempre
description: Ajuda com entregas.

# ✅ enumera os gatilhos reais, nas palavras que a pessoa usa
description: Procedimento completo de entrega final sob travas — os dois loops,
  a ordem obrigatória das provas, e o que fazer quando cada uma falha. Use sempre
  que uma tarefa for declarada concluída, sempre que o usuário pedir para
  "entregar", "finalizar", "publicar" ou "fazer deploy", e antes de qualquer
  git tag, npm publish, docker push ou release.
```

Liste **as palavras que o usuário vai usar** e **os comandos que precedem o
momento**. A skill não é encontrada por semântica pura; é encontrada pela
sobreposição entre a situação e a descrição.

## 4. Os agentes

Instalados em `.claude/agents/`. Aqui o frontmatter **é trava** — `tools:` define
o vocabulário inteiro do sub-agente, e o harness o aplica na criação:

```markdown
---
name: trava-fiscal
tools: Read, Grep, Glob, Bash
model: opus
---
```

Sem `Write` e sem `Edit`: trava N4. O fiscal não é *proibido* de corrigir —
corrigir não existe no vocabulário dele.

Ver [10 — Papéis e equipe](10-papeis-e-equipe.md) para os quatro papéis e a
coreografia completa.

> **Regra:** toda restrição que puder ser expressa como *ausência de ferramenta*
> deve ser expressa assim. O corpo do arquivo (prosa) é N0: explica **por quê**,
> e é isso que evita o sub-agente gastar ciclos tentando o que não pode.

## 5. HOW TO: acrescentar um comando

Crie `.claude/commands/trava-meu.md` com frontmatter (`description`,
`allowed-tools`) e o corpo do prompt, no formato da §2.

Comandos e skills são lidos **por demanda** — não precisa reiniciar.
**Hooks, não**: esses são capturados no início da sessão.

## 6. HOW TO: acrescentar uma trava de verdade

Um comando novo não trava nada. Para bloquear algo, o caminho é o contrato.

**Passo 1 — defina COMO se prova.** Em `.trava/contrato.json` → `verificacoes`.
O comando precisa sair com `rc 0` exatamente quando está tudo bem:

```json
"migracoes-aplicadas": {
  "comando": "./scripts/check-migrations.sh",
  "ttl": 900,
  "descricao": "Migrações aplicadas e iguais ao esperado."
}
```

**Passo 2 — defina O QUE isso destrava.** Em `.trava/contrato.json` → `travas`:

```json
{
  "id": "sem-deploy-sem-migracao",
  "quando": { "ferramentas": ["Bash"], "regex_alvo": "kubectl\\s+apply" },
  "exige_selos": ["migracoes-aplicadas"],
  "estrito": true,
  "veredito": "deny",
  "como_destravar": ["./trava selo emitir migracoes-aplicadas"],
  "mensagem": "Deploy sem migração aplicada derruba o serviço em produção."
}
```

**Passo 3 — PROVE que trava**, sem abrir sessão de agente. Um hook é um programa
que lê JSON no stdin: alimente-o com o mesmo payload que o runtime enviaria.

```bash
printf '%s' '{"hook_event_name":"PreToolUse","session_id":"t","tool_name":"Bash","tool_input":{"command":"kubectl apply -f k8s/"}}' | python3 .claude/hooks/trava_gate.py
```

Espere ver `"permissionDecision": "deny"` com a sua mensagem. Se sair vazio, a
regra não casou — confira o `regex_alvo` e a lista de `ferramentas`.

**Passo 4 — rode a bateria inteira:**

```bash
bash .trava/bin/testar_travas.sh
```

### Disciplina de adoção (vale mais que qualquer receita)

1. **Uma trava por falha que JÁ ACONTECEU**, não por falha imaginada.
2. Comece com `"veredito": "ask"`. Promova para `"deny"` só se o humano estiver
   sempre negando.
3. Toda trava precisa deixar **aberto o caminho que leva à própria liberação**
   (a trava de plano libera `docs/`, senão o agente não escreve o plano que
   destrava).
4. Revise `AUDITORIA.md` mensalmente: trava que nunca dispara é ruído; trava que
   dispara toda hora está mal calibrada.

> **Uma trava que é removida protege zero.** Calibração faz parte do mecanismo,
> não é um detalhe de manutenção.

---

➡️ Próximo: [14 — Instalação e distribuição](14-instalacao.md)
