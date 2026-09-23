# 11 — Auditoria, forense e rollback

> Sem rastro, você não consegue distinguir **"a trava não bloqueou"** de **"a trava
> nem rodou"** — e são bugs completamente diferentes, com correções opostas.

## 1. Três coisas distintas (não confunda)

| | Responde | Onde | Formato |
|---|---|---|---|
| **Auditoria** | *o que a trava decidiu, e por quê* | `.trava/auditoria.jsonl` | NDJSON encadeado |
| **Espelho humano** | *o que houve aqui?* para quem não abre JSONL | `AUDITORIA.md` | tabela markdown |
| **Forense** | *o que este agente mudou, e como desfazer* | `.trava/forense/<sessao>/` | imagem-anterior + metadados |

## 2. A auditoria encadeada

Cada linha carrega o hash da linha anterior:

```jsonc
{"ts":1790121384,"iso":"2026-09-22T23:56:24Z","sessao":"abc","evento":"PreToolUse",
 "decisao":"deny","trava":"autoprotecao","motivo":"tentativa de escrita no cofre",
 "prev":"a91f3c…","hash":"7e22b1…"}
```

`hash = sha256(json canônico do registro sem o campo hash)`, e o `prev` do próximo
é esse `hash`. Editar ou remover **qualquer** linha do meio quebra a cadeia a
partir dali.

```bash
./trava auditoria --verificar
# cadeia íntegra: 142 registro(s)
# ou:
# linha 37: elo quebrado — 'prev' é a91f3c…, esperado 7e22b1…. Alguma linha
#           anterior foi editada ou removida.
```

> **O que isto garante e o que não garante.** Não impede a edição: quem tem shell
> pode reescrever o arquivo inteiro e recalcular a cadeia. O que ele faz é tornar
> a edição **visível e cara** — e distinguir "alguém mexeu" de "sempre foi assim".
> É esse o serviço que uma auditoria presta. Para tornar a edição impossível, é
> preciso levar o ledger para fora da máquina (§7).

### O heartbeat

O gate registra `decisao: "invocado"` **antes** de avaliar qualquer regra. Sem
isso, "o hook rodou e nenhuma regra casou" e "o hook nem rodou" produzem o mesmo
silêncio no log, e o diagnóstico do [08](08-provar-que-trava.md) fica falso.

Corolário prático: **auditoria vazia = o hook nunca rodou**. O problema é
configuração (matcher, caminho, sessão não reiniciada), não lógica.

```bash
./trava doutor     # é exatamente isto que ele checa
```

## 3. O espelho humano — `AUDITORIA.md`

O JSONL é para programa. `AUDITORIA.md` é para a pessoa que vai perguntar "o que
aconteceu aqui?" três semanas depois:

```markdown
| quando (UTC) | evento | decisão | trava/alvo | motivo |
|---|---|---|---|---|
| 2026-09-22T23:41:07Z | PreToolUse | deny | autoprotecao | tentativa de escrita no cofre |
| 2026-09-22T23:43:02Z | bancada | aberta | a interface do produto | roteiro com 7 passo(s) |
| 2026-09-22T23:46:18Z | bancada | fechada | a interface do produto | duração 412s (mínimo 180s) |
| 2026-09-22T23:46:20Z | entrega | bloqueada | | documentação não revisada |
```

Cresce junto com o JSONL, na mesma escrita. Fica na raiz do projeto de propósito:
é o arquivo para mostrar a alguém, para anexar num incidente, para commitar.

> `AUDITORIA.md` **fica no git**. `.trava/chave.secreta`, `selos/`, `contadores/`,
> `forense/` e `bancada/` ficam fora (o `setup.sh` escreve o `.gitignore`).
> Estado e segredo não se versionam; histórico, sim.

## 4. Forense: a imagem-anterior

Antes de **cada** escrita, o gate guarda o conteúdo anterior do arquivo:

```
.trava/forense/<sessao>/
├── 00001.json     metadados: quando, qual ferramenta, qual caminho, qual papel
├── 00001.antes    o conteúdo do arquivo ANTES daquela escrita
├── 00002.json
└── 00002.antes
```

Isso dá duas coisas que log de texto não dá:

1. **Prova do que existia** — não a descrição do que existia.
2. **Rollback real**, independente de git, funcionando inclusive em arquivo que
   nunca foi commitado.

Limites explícitos: arquivos acima de 4 MB não recebem snapshot (o metadado
registra `nota: arquivo grande demais`), e a captura roda no `PreToolUse`, então
só cobre o que passa pelo gate — se alguém escrever com o hook desligado, não há
imagem-anterior.

```bash
./trava forense                      # tudo
./trava forense --sessao abc-123     # de uma sessão
#   00001  2026-09-22T23:41:07Z  Write    [snapshot]  src/app.ts
#   00002  2026-09-22T23:41:30Z  Edit     [snapshot]  src/api.ts
```

## 5. HOW TO: rollback

```bash
./trava rollback --sessao abc-123              # tudo daquela sessão
./trava rollback --sessao abc-123 --ate 00042  # do evento 42 em diante
```

Restaura do mais recente para o mais antigo, para que sobrescritas encadeadas
voltem na ordem certa.

**Exige TTY e confirmação digitada** (`RESTAURAR`). Duas razões:

- rollback é destrutivo na direção oposta: ele apaga o que veio depois;
- é decisão de pessoa. O agente que fez a bagunça não é quem decide desfazê-la.

Antes de confirmar, o comando lista o que será restaurado. Leia a lista.

## 6. HOW TO: investigar um incidente

```bash
# 1. A trava chegou a rodar?
./trava doutor

# 2. A cadeia está íntegra? (se não, alguém mexeu no histórico)
./trava auditoria --verificar

# 3. O que aconteceu, em ordem
./trava auditoria -n 100

# 4. Cheiros a procurar no resultado:
#    deny + autoprotecao ...... houve tentativa de mexer na própria trava
#    cedido ................... uma trava abriu SEM as provas → entrega não verificada
#    imposicao SUSPENSA ....... alguém desligou; veja o motivo e por quanto tempo
#    loop_estourado ........... executor↔fiscal não convergiu
#    CONTRATO_SEM_TRAVAS ...... os hooks rodam e nada bloqueia
#    erro_interno ............. hook quebrado; a trava pode estar cega

# 5. O que mudou no disco
./trava forense --sessao <id>

# 6. Desfazer, se for o caso (no SEU terminal)
./trava rollback --sessao <id>
```

## 7. Os padrões que denunciam um mecanismo morrendo

Revise mensalmente. Uma trava que ninguém audita vira enfeite — e enfeite é pior
que nada, porque produz confiança sem lastro.

| Padrão | O que significa | O que fazer |
|---|---|---|
| muitas `imposicao SUSPENSA` seguidas de encerramento | a válvula virou o caminho | descubra qual trava está errada; não é o usuário que está errado |
| `cedido` recorrente | as exigências não são satisfazíveis | a receita de destravamento está errada ou impossível |
| nenhum `deny` em semanas | as travas não pegam nada | ou está tudo ótimo, ou o contrato está vazio (`./trava status`) |
| `deny` toda hora na mesma trava | calibragem ruim | comece com `ask` e promova só se o humano sempre nega |
| `bancada` sempre com a duração mínima exata | alguém está cronometrando para passar | converse; o mecanismo não resolve isto, gente resolve |
| `bancada` sempre APROVADO de primeira | aprovação de cortesia | veja §5 do [09](09-o-que-e-testar.md) |

## 8. Levar o ledger para fora da máquina

A cadeia local detecta adulteração, mas quem tem shell pode reescrever tudo. Se o
seu contexto exige garantia forte, ancore o ledger fora:

```bash
# a cada entrega, anexe o hash da ponta da cadeia a algo que o agente não controla
HASH=$(tail -1 .trava/auditoria.jsonl | python3 -c 'import json,sys;print(json.load(sys.stdin)["hash"])')
git commit -m "entrega $(date -u +%F) · ledger=$HASH"
git push          # o hash fica no histórico do remoto
```

Ou envie a ponta para um log append-only externo (syslog remoto, bucket com
object-lock, canal de CI). A partir daí, reescrever o ledger local não adianta: a
âncora externa não bate.

Isto é a mesma lógica do [05](05-travas-sem-hook.md): o que precisa resistir a um
agente adversário tem que morar onde ele não alcança.

---

➡️ Próximo: [12 — Os loops](12-loops.md)
