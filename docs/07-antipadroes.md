# 07 — Antipadrões: o que parece trava e não é

Catálogo de falhas reais. Cada uma com o sintoma, a causa e a correção.

---

## A1 — O hook que só avisa

```python
if "git push" in comando and not selo_existe("testes-verdes"):
    print("⚠️  ATENÇÃO: push sem testes!")   # e sai com 0
sys.exit(0)
```

**Sintoma:** você vê o aviso no transcript, e o push acontece.
**Causa:** o veredito nunca foi emitido. Código de saída 0 = "sem objeção".
**Correção:** `sys.exit(2)` ou `permissionDecision: "deny"`. Sem um desses dois, você
escreveu um sistema de logging.

> Este é o antipadrão que dá nome a este repositório. Uma recusa bem escrita que não
> cancela a chamada é exatamente a "frase linda de negação" que não trava nada — e ela
> é *mais perigosa* que não ter trava, porque produz a sensação de estar protegido.

---

## A2 — Bloquear `Stop` sem checar `stop_hook_active`

```python
if not tem_relatorio():
    print(json.dumps({"decision": "block", "reason": "faça o relatório"}))
```

**Sintoma:** o agente nunca para. Consome tokens até o limite. É o "loop de agente".
**Causa:** o hook bloqueia → o agente continua → tenta parar → o hook bloqueia de novo.
Se a condição nunca for satisfeita (ou se o agente não entender como satisfazê-la),
a recursão é infinita.
**Correção — as três, não uma:**

```python
if p.get("stop_hook_active"):        # 1. fusível
    sys.exit(0)
n = incrementar(f"stop_{sessao}")    # 2. contador
if n > 3:
    avisar("trava cedida; revise manualmente"); sys.exit(0)
# 3. reason com receita literal + saída honrosa
```

---

## A3 — Trava sem receita de destravamento

```python
T.negar("Ação não permitida.")
```

**Sintoma:** o agente tenta 12 variações do mesmo comando, cada uma bloqueada, até
desistir ou estourar o contexto.
**Causa:** ele não recebeu informação suficiente para agir. "Não permitida" não é
acionável.
**Correção:** as 4 partes do órgão 5 ([02](02-anatomia-da-trava.md)): o quê, qual condição,
o comando literal, e o que fazer se for impossível. A última parte é a mais esquecida e
a que evita a busca por contorno.

---

## A4 — Travar a ferramenta, esquecer a rota alternativa

```json
{ "quando": { "ferramentas": ["Write", "Edit"] } }
```

**Sintoma:** o arquivo é modificado mesmo assim.
**Causa:** `Bash(cat > arquivo)`, `Bash(sed -i)`, `Bash(tee)`, `Bash(python3 -c "open(...)")`
escrevem sem passar por `Write`.
**Correção:** pergunte sempre *"qual é o outro jeito de conseguir isso?"* e cubra também:

```json
{ "quando": { "ferramentas": ["Write","Edit","NotebookEdit"] } },
{ "quando": { "ferramentas": ["Bash"],
              "regex_alvo": ">\\s*\\S+|sed\\s+-i|tee\\s|dd\\s+of=" } }
```

E aceite o limite: regex sobre string de comando é defesa de superfície. Para o que
realmente não pode acontecer, **use N4** ([05](05-travas-sem-hook.md)) — filesystem
somente-leitura não tem rota alternativa.

---

## A5 — O selo que não prova nada

```json
"testes-verdes": { "comando": "echo ok" }
```
ou
```json
"relatorio": { "comando": "test -f output/relatorio.md" }
```

**Sintoma:** a trava passa sempre; o problema que ela deveria pegar continua acontecendo.
**Causa:** o verificador não verifica. `test -f` passa com `touch`.
**Correção:** toda condição de **existência** precisa de uma condição de **substância**:

```json
"relatorio": {
  "comando": "test -s output/relatorio.md && [ $(wc -c < output/relatorio.md) -ge 300 ] && grep -q '## Pendências' output/relatorio.md"
}
```

---

## A6 — Prova imortal

**Sintoma:** push com teste vermelho, apesar da trava R2 estar ativa.
**Causa:** o selo foi emitido às 14h02, o código mudou às 14h15, o push foi às 14h20.
O selo ainda existia e ainda era válido.
**Correção, em três camadas:**
- `"ttl"` curto para provas voláteis (`testes-verdes`: 1800s; `arvore-limpa`: 300s)
- `pos_acao.selos_volateis` — `PostToolUse` revoga a prova a cada escrita
- `"estrito": true` na trava crítica — re-executa a verificação no instante da decisão

---

## A7 — A trava que o agente edita

**Sintoma:** o agente foi bloqueado, "resolveu o problema", e o hook está diferente.
**Causa:** `.claude/hooks/` é gravável pelas ferramentas do agente.
**Correção:** R10 em [04](04-receitas.md) + `:ro` no bind mount ([05](05-travas-sem-hook.md) §4).
E no prompt do agente, explicitamente: *"editar as travas é violação do contrato; se a
trava parecer errada, diga isso e pare."*

**Detecção:** a auditoria denuncia. Um `PreToolUse` com `decision=deny` em
`Edit(.claude/hooks/...)` é o sinal mais claro de agente fora do contrato — vale um alerta.

---

## A8 — Falha aberta silenciosa

```python
try:
    verificar()
except Exception:
    sys.exit(0)     # "melhor não atrapalhar"
```

**Sintoma:** a trava simplesmente não funciona, e ninguém percebe por semanas.
**Causa:** um `except` que engole erro e libera. Um `import` quebrado, um `contrato.json`
com vírgula sobrando, e a trava some sem ruído.
**Correção:** escolha a política **por trava** e escreva-a no cabeçalho do arquivo:
- **trava de segurança → falha FECHADA** (`negar()` no `except`), como `trava_gate.py`
- **trava de fluxo/conclusão → falha ABERTA** (`exit 0`), como `trava_stop.py` — porque
  ali o risco é prender o agente para sempre

Em ambos os casos, **sempre** registre em `auditoria.jsonl`. "Falhou aberto" precisa
deixar rastro, senão é indistinguível de "passou legitimamente".

---

## A9 — Debug no stdout

```python
print("tool_name:", tool_name)          # ☠️
print(json.dumps({"hookSpecificOutput": {...}}))
```

**Sintoma:** a trava "não funciona", às vezes.
**Causa:** em `PreToolUse`, **o stdout é parseado como o veredito**. Qualquer texto extra
corrompe o JSON e o veredito é perdido.
**Correção:** debug vai para `stderr` ou para arquivo. `lib_trava.auditar()` existe para isso.

---

## A10 — Editar settings e achar que ligou

**Sintoma:** você configurou tudo, testou, e nada acontece.
**Causa:** hooks são capturados **no início da sessão**. Editar `settings.json` com a
sessão aberta não ativa nada — e isso é proposital, para que um agente não recarregue as
próprias travas alteradas no meio do caminho.
**Correção:** reinicie a sessão. Confira em `/hooks`. Depois **prove** com
[08-provar-que-trava.md](08-provar-que-trava.md). Nunca presuma.

---

## A11 — Matcher com caixa errada

```json
{ "matcher": "bash|write" }
```

**Sintoma:** silêncio absoluto. O hook nunca roda.
**Causa:** o matcher é sensível a maiúsculas: `Bash`, `Write`, `Edit`, `Task`,
`NotebookEdit`, `WebFetch`, `Read`, `Glob`, `Grep`.
**Correção:** confira a grafia. E adicione um hook temporário com `"matcher": "*"` que só
faz `auditar()` — se o log não crescer, o problema é configuração, não lógica.

---

## A12 — Travar demais

**Sintoma:** o agente não consegue fazer nada. Tudo bloqueado, tudo exige selo, cada selo
exige outro selo. Você desliga o sistema inteiro na sexta-feira.
**Causa:** travas foram adicionadas por ansiedade, não por incidente.
**Correção:** disciplina de adoção —

1. Uma trava por **falha real que já aconteceu**, não por falha imaginada.
2. Comece com `"veredito": "ask"`; promova para `"deny"` só se o `ask` estiver sempre
   sendo negado pelo humano.
3. Cada trava precisa deixar **aberto o caminho que leva à própria liberação** (R1 libera
   `docs/`, senão o agente não escreve o plano que destrava).
4. Revise `auditoria.jsonl` mensalmente: trava que nunca disparou é ruído; trava que
   dispara toda hora está mal calibrada.

**Uma trava que é removida protege zero.** Calibração é parte do mecanismo, não um detalhe.
