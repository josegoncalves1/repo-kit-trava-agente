# 08 — Provar que a trava trava

> Uma trava não testada é uma **suposição de segurança** — e é pior do que não ter trava,
> porque produz confiança sem proteção.

O antipadrão A1 ([07](07-antipadroes.md)) — o hook que só avisa — é invisível: tudo parece
certo no código, e a ação acontece do mesmo jeito. Só um teste distingue.

---

## 1. A ideia central: hook é programa, programa se testa

Um hook não tem nada de mágico. É um processo que **lê JSON no stdin e responde**. Então
você pode testá-lo **sem abrir uma sessão de agente**, alimentando-o com o mesmo payload
que o runtime enviaria:

```bash
echo '{"hook_event_name":"PreToolUse","session_id":"t","permission_mode":"default",
       "tool_name":"Bash","tool_input":{"command":"git push origin main"}}' \
  | python3 .claude/hooks/trava_gate.py
```

Ciclo de desenvolvimento em segundos, sem gastar token, sem reiniciar sessão.

Leitura da resposta:

| Saída | Significado |
|---|---|
| stdout vazio, exit 0 | **passou** — a ferramenta vai rodar |
| `{"hookSpecificOutput":{...,"permissionDecision":"deny",...}}` | **bloqueou** |
| `{"hookSpecificOutput":{...,"permissionDecision":"ask",...}}` | devolvido ao humano |
| `{"decision":"block","reason":"..."}` | (Stop/SubagentStop) não encerra |
| exit 2 + texto no stderr | **bloqueou** pela via de código de saída |
| exit 1, ou stack trace | **hook quebrado** — provavelmente não bloqueia nada |

---

## 2. As seis provas obrigatórias

Rode antes de confiar em qualquer trava. Script pronto:
[../payload/.trava/bin/testar_travas.sh](../payload/.trava/bin/testar_travas.sh).

### Prova 1 — do bloqueio
Com a condição **não** satisfeita, a ação é negada?
*Se falhar:* você tem um logger (A1). Falta o `exit 2` / `permissionDecision`.

### Prova 2 — da mentira
Forje o estado à mão e tente passar:
```bash
echo '{"nome":"testes-verdes","rc":0,"ok":true,"hmac":"forjado"}' > .trava/selos/testes-verdes.json
./trava selo conferir testes-verdes   # deve dizer "assinatura INVÁLIDA"
```
*Se falhar:* seu verificador é V1 (presença de arquivo). Suba para V2/V3 ([02](02-anatomia-da-trava.md) órgão 3).

### Prova 3 — da passagem
Com a condição satisfeita, a ação passa?
*Se falhar:* você criou um deadlock. Pior que trava nenhuma — o agente nunca conclui.

### Prova 4 — da verificação real
Um comando que falha **não** pode emitir selo:
```bash
./trava selo emitir relatorio --comando "false"; echo "exit=$?"   # 1
test -f .trava/selos/relatorio.json && echo "BUG: selo criado!"
```

### Prova 5 — do anti-loop
O fusível responde, e o contador cede depois de N?
```bash
echo '{"hook_event_name":"SubagentStop","session_id":"t","stop_hook_active":true}' \
  | python3 .claude/hooks/trava_stop.py     # DEVE sair vazio, exit 0
```
*Se bloquear aqui, você tem loop infinito garantido em produção.* É a prova mais importante.

### Prova 6 — da auditoria
`.trava/auditoria.jsonl` cresceu? Sem rastro, você não consegue distinguir
"não bloqueou" de "nem chegou a rodar" — e são bugs completamente diferentes.

---

## 3. Resultado de referência

Saída real de `.trava/bin/testar_travas.sh` neste repositório:

```
─── 1. TESTE DO BLOQUEIO: a trava trava? ───
  ✅ push sem selo — BLOQUEADO (correto)
  ✅ sub-agente sem contrato — BLOQUEADO (correto)
  ✅ encerrar sem relatório — BLOQUEADO (correto)

─── 2. TESTE DA MENTIRA: selo forjado é rejeitado? ───
  ✅ selo escrito à mão — REJEITADO: selo 'testes-verdes' com assinatura INVÁLIDA
  ✅ push com selo forjado — BLOQUEADO (correto)

─── 3. TESTE DA PASSAGEM: destrava quando deve? ───
  ✅ push com selos válidos — passou (correto)

─── 4. TESTE DA VERIFICAÇÃO REAL ───
  ✅ verificação falhou → selo NÃO emitido (correto)

─── 5. TESTE ANTI-LOOP ───
  ✅ stop_hook_active=true (fusível) — passou (correto)
  ✅ stop tentativa 1 / 2 / 3 — BLOQUEADO (correto)
  ✅ stop tentativa 4 (trava cede e escala) — passou (correto)

─── 6. TESTE DA AUDITORIA ───
  ✅ auditoria com 14 registros

  13 corretos, 0 falhos   ✅ TRAVAS VALIDADAS
```

> **Armadilha encontrada ao escrever este script** (e vale para qualquer teste de trava):
> com `set -o pipefail`, o pipeline `./trava selo conferir | grep -q "..."` herda o **exit 1**
> do `./trava selo conferir` — que sai 1 corretamente, por ser um selo inválido — e mascara o sucesso do
> `grep`. O teste acusa falha onde o mecanismo está certo. Capture a saída numa variável
> antes de testá-la. **Um teste de trava com bug faz você desconfiar de uma trava boa, ou
> confiar numa ruim.**

---

## 4. Teste em sessão real

Os testes acima validam o **programa**. Falta validar a **integração** — se o runtime está
de fato chamando o seu hook.

1. **Reinicie a sessão.** Hooks são capturados na inicialização (A10).
2. Confira em `/hooks` que o comando aparece registrado.
3. Peça ao agente uma ação que **deve** ser bloqueada. Confirme que:
   - a ferramenta não executou,
   - o agente relatou o motivo com a receita de destravamento,
   - `.trava/auditoria.jsonl` registrou a decisão.
4. Peça a ação que **deve** passar, e confirme que passou.
5. **Teste a partir de um sub-agente.** É o caso que nenhuma instrução em prompt cobre:
   dispare um `Task` e faça o sub-agente tentar a ação bloqueada. Se o gate barrar ali, a
   herança está coberta.

Se a auditoria não registrou nada no passo 3, o hook **nem rodou** — o problema é
configuração (matcher com caixa errada, caminho do script, sessão não reiniciada), não
lógica. Diagnóstico rápido: hook temporário com `"matcher": "*"` que só chama `auditar()`.

---

## 5. Checklist de aceitação

```
[ ] Prova 1 — bloqueia sem a condição
[ ] Prova 2 — estado forjado é rejeitado
[ ] Prova 3 — passa com a condição satisfeita
[ ] Prova 4 — verificação que falha não emite selo
[ ] Prova 5 — fusível responde e contador cede
[ ] Prova 6 — auditoria registra
[ ] Integração — testado em sessão real, após reiniciar
[ ] Herança   — testado a partir de um SUB-AGENTE
[ ] Retorno   — a mensagem de bloqueio traz o comando literal que destrava
[ ] Válvula   — existe caminho documentado quando a condição é impossível
```

Dez itens. Enquanto faltar um, a trava é uma hipótese.

---

➡️ Próximo: [09 — O que é testar](09-o-que-e-testar.md) — o coração do kit.
