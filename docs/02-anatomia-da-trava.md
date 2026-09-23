# 02 — Anatomia de uma trava: os 6 órgãos

Toda trava real, em qualquer runtime, tem os mesmos seis órgãos. Se faltar um, você sabe
exatamente qual defeito vai aparecer. Use esta seção como **checklist de projeto**.

```
   ┌─── 1. GATILHO ──────── em que ponto obrigatório eu intercepto?
   │
   ├─── 2. ESTADO ───────── onde mora a verdade, fora da narrativa do modelo?
   │
   ├─── 3. VERIFICADOR ──── qual programa decide, e com base em que execução real?
   │
   ├─── 4. VEREDITO ─────── como o "não" é dito numa linguagem que o runtime obedece?
   │
   ├─── 5. RETORNO ──────── o que o agente lê para saber COMO destravar?
   │
   └─── 6. VÁLVULA ──────── como sai daqui sem loop infinito, e quem fica sabendo?
```

---

## Órgão 1 — GATILHO

**Pergunta:** existe um ponto por onde a ação *obrigatoriamente* passa, e que eu controlo?

Se não existe, pare: você não tem onde pôr a trava. Crie o ponto primeiro (ver N2 em
[00-tese.md](00-tese.md) — um wrapper que vira o caminho único).

No Claude Code o gatilho é `evento + matcher`:

| Quero travar | Gatilho |
|---|---|
| execução de comando | `PreToolUse` + matcher `Bash` |
| escrita de arquivo | `PreToolUse` + matcher `Write\|Edit\|NotebookEdit` |
| nascimento de sub-agente | `PreToolUse` + matcher `Task` |
| leitura de segredo | `PreToolUse` + matcher `Read` |
| saída para a internet | `PreToolUse` + matcher `WebFetch\|WebSearch` |
| **conclusão do sub-agente** | `SubagentStop` (sem matcher) |
| **conclusão do turno principal** | `Stop` (sem matcher) |
| dano já consumado | `PostToolUse` + matcher da ferramenta |

**Defeito se faltar:** existe rota alternativa. O agente contorna sem nem perceber que
estava contornando. *Sempre pergunte: "qual é o outro jeito de fazer isso?" e cubra também.*
Exemplo real: travar `Write` e esquecer que `Bash(cat > arquivo)` escreve igual.

---

## Órgão 2 — ESTADO

**Pergunta:** o fato que autoriza a ação está gravado onde o modelo não escreve?

Regra inegociável:

> O estado da trava **nunca** mora no contexto da conversa. Mora em arquivo no disco,
> escrito por um verificador, não por uma afirmação do modelo.

Layout usado neste repositório:

```
<projeto>/.trava/
├── contrato.json          # declaração: o que trava, o que destrava  (você escreve)
├── chave.secreta          # 32 bytes, 0600, gerada na 1ª execução    (lib gera)
├── selos/
│   ├── plano-aprovado.json
│   └── testes-verdes.json # provas assinadas de verificações que rodaram
├── contexto/
│   └── <session>.json     # perfil do sub-agente, gravado no nascimento
├── contadores/
│   └── <session>.json     # reentradas de Stop — o fusível anti-loop
└── auditoria.jsonl        # append-only: toda decisão de toda trava
```

Por que arquivo e não contexto: sobrevive à compactação, é comum a todos os sub-agentes da
sessão, é legível por programa, e é gravado por quem *executou* a verificação.

**Defeito se faltar:** o teste da amnésia falha. Compactou, perdeu a trava.

---

## Órgão 3 — VERIFICADOR

**Pergunta:** o que exatamente roda para decidir, e a decisão vem de uma execução ou de
uma afirmação?

Escada de força do verificador, do mais fraco ao mais forte:

### V1 — Presença de arquivo
```python
ok = Path(".trava/selos/testes-verdes.json").exists()
```
Trava contra **esquecimento e desordem**. Um agente pode criar o arquivo vazio com `touch`.
Aceitável para ordem de etapas, insuficiente para garantia.

### V2 — Selo assinado (HMAC)
O selo carrega `{comando, código de saída, hash da saída, timestamp}` e um HMAC-SHA256
sobre esse corpo, com chave gerada na primeira execução (`0600`).
```python
esperado = hmac.new(chave, json.dumps(corpo, sort_keys=True).encode(), hashlib.sha256).hexdigest()
ok = hmac.compare_digest(esperado, selo["hmac"])
```
Trava contra **fabricação casual**: o agente não consegue escrever um selo válido à mão,
porque não sabe a chave. Não trava contra `cat .trava/chave.secreta` num shell irrestrito.

### V3 — Re-execução pelo gate ← **o padrão-ouro**
O gate **ignora qualquer afirmação** e roda ele mesmo a verificação:
```python
r = subprocess.run("python3 -m pytest -q", shell=True, capture_output=True)
ok = (r.returncode == 0)
```
Trava contra **tudo que não seja um estado do mundo genuinamente verde**. Não existe
falsificar: a verdade é recalculada no instante da decisão.
**Custo:** lentidão. Roda a cada chamada que casa com o matcher.

### V4 — Impossibilidade (N4)
Não há verificador porque não há ação. Ver [05-travas-sem-hook.md](05-travas-sem-hook.md).

### A composição que este repositório usa

```
selo emitido  →  V3 (roda o comando de verdade)  +  V2 (assina o resultado)
gate consulta →  V2 (confere assinatura e TTL)   +  V3 opcional (re-executa se "estrito")
```

Assim o caminho comum é barato (conferir HMAC: microssegundos) e o caminho crítico é
forte (re-execução) — ligado por trava via `"estrito": true` no contrato.
**Verificação cara vira selo uma vez; não roda a cada chamada.**

**Defeito se faltar:** o teste da mentira falha. O agente diz "validei" e a trava cede.

---

## Órgão 4 — VEREDITO

**Pergunta:** o "não" está dito numa linguagem que o runtime é obrigado a obedecer?

Isto é o que separa N3 de N0. O veredito **não é uma frase**, é um valor de retorno:

```python
# Via A — universal
print("motivo", file=sys.stderr); sys.exit(2)

# Via B — precisa
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": motivo}}))
sys.exit(0)
```

Três vereditos possíveis, e escolher bem é metade do projeto:

| Veredito | Quando usar |
|---|---|
| `deny` | a ação está errada **agora**; existe caminho claro para destravar |
| `ask` | a ação pode ser legítima, mas é cara/irreversível → **humano no laço** |
| `allow` | pré-aprovação explícita; pula o sistema de permissões. Use com parcimônia. |

> `ask` é subusado. Para muitos casos ("apagar diretório", "gastar dinheiro", "publicar"),
> a trava certa não é impedir — é **exigir um humano**. É uma trava real: o agente não
> passa sozinho.

**Defeito se faltar:** você escreveu um hook que imprime um alerta bonito e sai com 0.
A ferramenta roda. Você tem log, não trava. **Esse é exatamente o erro que este
repositório existe para eliminar.**

---

## Órgão 5 — RETORNO

**Pergunta:** o agente bloqueado sabe exatamente o que fazer para destravar?

O texto do `reason` é uma **interface de programação para um leitor em linguagem natural**.
Anatomia do bom retorno, em quatro partes:

```
[1] O QUE foi bloqueado e por qual trava (id rastreável)
[2] QUAL condição falhou, concretamente
[3] O COMANDO LITERAL que resolve
[4] O QUE fazer se a condição for impossível de satisfazer
```

Exemplo:

```
BLOQUEADO pela trava 'sem-push-sem-teste'.
Condição: falta o selo 'testes-verdes' (não existe em .trava/selos/).
Para destravar, rode exatamente:
    ./trava selo emitir testes-verdes
Isso executa 'python3 -m pytest -q'. O selo só é emitido se o código de saída for 0.
Se os testes não puderem passar agora, NÃO tente contornar a trava: relate ao usuário
qual teste falha e pare.
```

A última linha é importante: sem ela, um agente diligente tenta caminhos alternativos —
desabilitar o teste, editar o gate, usar outra ferramenta — o que é pior do que parar.
**Diga explicitamente que a saída é reportar, não contornar.**

**Defeito se faltar:** deadlock e queima de tokens. O agente bate na parede em loop,
inventando variações. Trava sem retorno é a segunda maior causa de "agente em loop".

---

## Órgão 6 — VÁLVULA

**Pergunta:** como isso termina, se a condição nunca for satisfeita?

Toda trava precisa de **limite e saída**, senão ela mesma vira o bug. Quatro mecanismos,
use pelo menos dois:

### (a) Fusível `stop_hook_active` — obrigatório em `Stop`/`SubagentStop`
```python
if payload.get("stop_hook_active"):
    sys.exit(0)   # já estamos num turno causado por bloqueio anterior; não empilhar
```
**A maior causa de loop infinito de agente é bloquear Stop sem checar este campo.**

### (b) Contador de reentrada
```python
n = incrementar(f".trava/contadores/{session_id}.json")
if n > contrato["max_reentradas"]:
    liberar(f"Trava cedida após {n} tentativas. ESCALE PARA O USUÁRIO: descreva o que falta.")
```
Depois de N tentativas, a trava **abre e avisa**. Um agente preso não resolve nada;
um usuário informado resolve.

### (c) TTL do selo
`"ttl": 1800` — selo expira. Impede que um selo de duas horas atrás autorize um push sobre
código que mudou desde então. Selo velho é mentira lenta.

### (d) Liberação auditada
Uma saída explícita, deliberada, e que **deixa rastro**:
```bash
./trava selo liberar sem-push-sem-teste --motivo "hotfix P0, incidente #4471"
```
Grava em `auditoria.jsonl` com motivo, timestamp e sessão. Diferente de "desligar a trava":
a trava registra que foi contornada, e por quê.

**Defeito se faltar:** a trava funciona uma vez, produz um loop infinito na segunda, e
alguém remove o hook inteiro. Travas mal-projetadas são deletadas — e aí você tem zero.

---

## Ficha de projeto (copie e preencha)

```
TRAVA: <id-kebab-case>
────────────────────────────────────────────────────────────
Objetivo (1 frase):
Nível de dureza alvo:      N0 / N1 / N2 / N3 / N4

1. GATILHO      evento:            matcher:
                rotas alternativas cobertas:
2. ESTADO       caminho:
                quem escreve:
3. VERIFICADOR  nível: V1/V2/V3/V4
                comando exato:
                critério de sucesso:  exit == 0 ?
4. VEREDITO     deny / ask / allow        via: exit 2 / JSON
5. RETORNO      texto (4 partes) escrito? [ ]
                inclui "não contorne, reporte"? [ ]
6. VÁLVULA      stop_hook_active checado? [ ]   max_reentradas:
                TTL:                             liberação auditada? [ ]

PROVA           bloqueio comprovado (08)? [ ]    passagem comprovada? [ ]
                testado a partir de sub-agente?  [ ]
```

---

Próximo: [03-travas-de-subagente.md](03-travas-de-subagente.md).
