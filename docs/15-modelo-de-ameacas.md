# 15 — Modelo de ameaças e limites honestos

> Um documento de trava que não diz onde a trava falha é propaganda. Este diz.
> **Não infle nada disto ao repassar o mecanismo.**

## 1. A tabela, sem maquiagem

| # | Ameaça | Frequência real | Coberto? | Por qual camada |
|---|---|---|---|---|
| A1 | agente **esquece** a regra (contexto longo, compactação) | altíssima | ✅ total | hook: o runtime executa, o modelo não precisa lembrar |
| A2 | sub-agente **nunca viu** a regra (nasceu com outro prompt) | altíssima | ✅ total | hook vale na sessão inteira, inclusive sidechains |
| A3 | agente **declara** conclusão sem ter feito | altíssima | ✅ total | selo re-executa; declaração não vira selo |
| A4 | **otimismo**: "curl 200, então está bom" | alta | ✅ total | bancada humana obrigatória na entrega |
| A5 | **cegueira de autor**: quem fez não vê o defeito | alta | ✅ total | fiscal com toolset restrito + papel derivado do ledger |
| A6 | **prova vencida**: validou e continuou codando | alta | ✅ total | fingerprint + TTL + `selos_volateis` no PostToolUse |
| A7 | agente **desiste no meio** e entrega parcial | alta | ✅ total | `SubagentStop` com `decision: block` |
| A8 | **lavagem por sub-agente**: relato vira fato | média | ✅ total | o portão lê o disco, nunca o texto |
| A9 | agente **erra o alvo** (`rm -rf` fora do escopo) | média | ✅ total | `permissions.deny` + gate por regex |
| A10 | **laudo de bancada escrito pelo agente** | média | ✅ alto | sessão registrada + tempo mínimo + heurísticas + `ask` |
| A11 | **atalho de conveniência** ("só desta vez") | média | ✅ alto | imposição com TTL, motivo e registro; exige TTY |
| A12 | **escrita direta no cofre** | baixa | ⚠️ parcial | autoproteção do gate (filtro de string) + `permissions.deny` |
| A13 | **leitura da chave HMAC** | baixa | ⚠️ parcial | filtro de caminho; `Read(./.trava/chave.secreta)` em deny |
| A14 | **adulteração do ledger** | baixa | ⚠️ detectável | hash-chain: não impede, **acusa** |
| A15 | **desinstalar os hooks** | baixa | ❌ local | só CI/branch protection resolve |
| A16 | **prompt injection** vinda de conteúdo lido | baixa | ⚠️ parcial | não levanta o portão (é código), mas convence o agente a tentar |

## 2. A limitação estrutural, dita de uma vez

> **Um agente com `Bash` irrestrito, na conta do usuário, pode em princípio fazer
> qualquer coisa que o usuário faria** — inclusive apagar `.trava/`, reescrever os
> hooks, ler a chave por um caminho que o regex não previu, ou recalcular a cadeia
> de auditoria inteira.

Isso é verdade e não tem como esconder. O HMAC e o hash-chain são
**anti-deriva e anti-atalho**, não anti-adversário-com-shell.

O que as camadas locais realmente entregam:

- **Custo e visibilidade.** Contornar exige ação deliberada, específica e
  registrada. Um agente derivando não contorna por acaso; teria que *tentar*.
- **Ausência de caminho acidental.** Nenhum fluxo normal de trabalho leva ao
  bypass.
- **Rastro.** Um `deny` em `autoprotecao` no ledger é o sinal mais claro que
  existe de agente fora do contrato.

O que elas **não** entregam: impossibilidade. Não confunda filtro de string com
isolamento.

## 3. Como fechar de verdade (quando o contexto exige)

Em ordem de força. Todas são N4 — [05](05-travas-sem-hook.md).

### 3.1 Toolset restrito
A restrição mais barata e mais forte. O fiscal sem `Write` não escreve, com ou
sem hook, com ou sem bug. **Antes de escrever qualquer trava, pergunte se o
agente precisa mesmo daquela ferramenta.**

### 3.2 Usuário do sistema separado
```bash
sudo useradd -m agente
sudo chown -R root:root .claude/hooks .trava/chave.secreta
sudo chmod 755 .claude/hooks && sudo chmod 600 .trava/chave.secreta
# o agente roda como 'agente': não escreve nos hooks, não lê a chave
```
Transforma A12 e A13 de "parcial" em **coberto**. Não é regex — é o kernel.

### 3.3 Container com montagem somente-leitura
```bash
docker run --rm --read-only --tmpfs /tmp --network none \
  -v "$PWD/src:/app/src:rw" \
  -v "$PWD/.claude:/app/.claude:ro" \
  -v "$PWD/.trava:/app/.trava:ro" \
  imagem-do-agente
```
`:ro` resolve a autoproteção **completamente**, inclusive contra `Bash(cat > …)`,
que `permissions.deny` não cobre. `--network none` é a trava de exfiltração
definitiva: nenhum hook precisa inspecionar URL porque não há rota.

> Nota: com `.trava` somente-leitura, o kit não consegue escrever selos nem
> ledger. Monte `.trava/selos` e `.trava/auditoria.jsonl` como volumes graváveis
> separados, ou rode o verificador fora do container.

### 3.4 Credencial ausente
A trava mais portátil que existe, e a que atravessa qualquer runtime e qualquer
fornecedor: **o agente não tem o token**. Ponto. O deploy passa por um broker que
só libera mediante `./trava selo conferir producao --estrito`.

### 3.5 CI e branch protection — contra A15
Desinstalar o hook local não muda nada se o PR não passa:

```yaml
- run: python3 .claude/hooks/verificar_doc.py
- run: test -f output/LAUDO-BANCADA.md
- run: python3 .claude/hooks/verificar_bancada.py output/LAUDO-BANCADA.md
- run: ./trava auditoria --verificar
- run: bash .trava/bin/testar_travas.sh      # a trava ainda trava?
```

Com esses checks **obrigatórios** na branch protegida, nenhuma configuração local
importa para o que sai. Acrescente um check que recusa PRs que alterem
`.claude/hooks/` **e** código de produto no mesmo commit: mudança de trava vira
PR próprio, revisado por gente.

### 3.6 Âncora externa do ledger
Ver [11](11-auditoria-forense-rollback.md) §8. O hash da ponta da cadeia vai para
onde o agente não alcança (mensagem de commit no remoto, log append-only, CI).
Reescrever o ledger local passa a não adiantar.

## 4. O ponto mais macio: o laudo humano (A10)

A bancada é o coração do kit, e é onde mora a fraude mais plausível: **o agente
escreve o laudo como se fosse a pessoa**.

Defesas, da mais fraca para a mais forte:

| Defesa | Força | Contorno |
|---|---|---|
| heurísticas de conteúdo (sem "ok/funcionou", respostas distintas, jornada com passos) | fraca | um modelo bom escreve um laudo convincente |
| tempo mínimo de sessão | média | o agente pode esperar — mas o tempo fica no ledger |
| fingerprint + frescor | média | força a fraude a ser refeita a cada mudança |
| `por_sessao` ≠ sessão executora | forte | exige uma sessão que não escreveu nada |
| **`ask` do runtime** | **a mais forte** | o agente não consegue responder pelo usuário |
| **TTY** em `entregar`/`imposicao off`/`rollback` | **a mais forte** | o `Bash` do agente não tem terminal |

> Conclusão prática: **não confie no conteúdo do laudo como prova de humano.**
> A prova é o canal — o `ask` e o TTY. As heurísticas servem para outra coisa:
> garantir que o laudo de um humano de verdade seja **útil** (respondido, não
> despachado).

E há um limite que nenhum mecanismo resolve: uma pessoa que abre a bancada, cronometra
os 180 segundos e escreve nove respostas plausíveis sem olhar direito. Isso é
problema de cultura, não de código. O que o kit faz é deixar o padrão visível no
`AUDITORIA.md` — bancadas sempre na duração mínima exata, sempre APROVADO de
primeira — para que alguém possa notar e conversar.

## 5. O que o kit explicitamente NÃO faz

- **Não garante que o produto é bom.** Garante que ele foi **observado como o
  usuário o observaria**, por alguém que não o construiu. Produto certo é problema
  de produto.
- **Não substitui** teste de segurança, carga, correção funcional ou conformidade.
- **Não avalia o que não está numa jornada declarada.** O roteiro da bancada é o
  limite da cobertura. Este é o furo mais comum na prática, e é de disciplina
  humana.
- **Não impede regressão** fora do escopo de produto declarado.
- **Não funciona com contrato vazio.** Hooks ativos + contrato sem travas =
  cerimônia completa, efeito zero. `./trava doutor` grita isso; leia.

## 6. Como saber se a sua instalação está viva ou virou teatro

**Sinais de saúde:**
- há reprovações regulares, e elas mudam o código;
- o `AUDITORIA.md` mostra `deny` e `bancada invalida` acontecendo;
- alguém já suspendeu a imposição, com motivo, e ela voltou sozinha;
- o contrato ganhou uma trava nos últimos 60 dias, vinda de uma falha real.

**Sinais de teatro** (todos exigem ação):
- **nunca** reprova → contrato vazio ou travas triviais;
- **sempre** reprova o mesmo e ninguém corrige → mal calibrada;
- `#trava-off` em mais de ~40% das sessões que tocam produto;
- `cedido` recorrente no ledger → as exigências não são satisfazíveis;
- bancadas sempre na duração mínima exata, sempre APROVADO;
- auditoria vazia → **o hook nem está rodando** (`./trava doutor`).

Ponha um relatório mensal disso no CI.

> **Uma trava que ninguém audita vira enfeite — e enfeite é pior que nada,
> porque produz confiança sem lastro.**

## 7. O resumo de uma frase

> Este kit torna **impossível entregar errado por descuido**, e torna **caro e
> visível entregar errado de propósito**. Ele não torna impossível entregar errado
> de propósito — para isso, o mecanismo tem que morar onde o agente não alcança:
> outro usuário, outro container, outra máquina.

---

⬅️ Volta ao [README](../README.md) · [Contrato de entrega](../payload/CONTRATO-DE-ENTREGA.md)
