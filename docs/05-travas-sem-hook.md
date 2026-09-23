# 05 — Travas estruturais (N4): quando não existe nada a verificar

Hooks são a camada N3: um verificador decide. A camada N4 é diferente em natureza —
**não há decisão porque não há ação possível**. Nada para lembrar, nada para checar,
nada para contornar, nada que possa ter bug.

> **Regra de projeto:** toda restrição que puder ser expressa como *ausência de capacidade*
> deve ser expressa assim. Hooks são para o que sobrar — condições que dependem de
> **estado** (ordem, prova, prazo), não de **capacidade**.

Escrever um hook para impedir algo que você podia simplesmente não conceder é trabalho a
mais com garantia a menos.

---

## 1. Toolset do sub-agente — a mais forte e a mais esquecida

Em `.claude/agents/<nome>.md`:

```markdown
---
name: auditor
description: Audita e relata. Não modifica nada.
tools: Read, Grep, Glob
model: sonnet
---
```

Esse sub-agente **não possui** `Write`, `Edit`, `Bash`. Não é proibido de escrever:
escrever não existe no vocabulário dele. Nenhum hook roda, nenhuma verificação falha,
nenhum prompt precisa avisar.

Compare os custos:

| | Hook (N3) | Toolset (N4) |
|---|---|---|
| Linhas de código | ~60 | 1 linha de frontmatter |
| Pode ter bug | sim | não |
| Pode ser contornado por outra ferramenta | **sim** (`Bash(cat >)`) | não existe outra ferramenta |
| Custo por chamada | executa um processo | zero |
| Mensagem de erro útil | você escreve | genérica |

O único ponto em que N3 ganha: N3 explica *por quê* e diz como destravar. Por isso a
combinação ideal é **N4 para a capacidade + N0 no prompt do agente explicando o recorte**
— exatamente o que faz [../payload/.claude/agents/trava-fiscal.md](../payload/.claude/agents/trava-fiscal.md).

---

## 2. `permissions.deny` — o harness recusa antes do seu código

Em `.claude/settings.json`:

```json
{
  "permissions": {
    "deny": [
      "Bash(rm -rf /*)",
      "Bash(git push --force:*)",
      "Bash(curl:*)",
      "Read(./.env)",
      "Read(./**/*.pem)",
      "WebFetch"
    ],
    "ask": [
      "Bash(git push:*)",
      "Bash(npm publish:*)"
    ]
  }
}
```

Avaliado pelo harness **antes** de qualquer hook. Não depende de o seu Python rodar, nem
de o `.trava/` existir, nem de a chave HMAC estar íntegra. Sintaxe: `Ferramenta(padrão)`,
com `:*` como curinga de sufixo para comandos e globs para caminhos.

`ask` merece a mesma atenção que `deny`: mover uma ação para confirmação humana **é** uma
trava real — o agente não passa sozinho — e sem a rigidez de um "nunca".

---

## 3. Ausência de credencial — a trava que atravessa runtimes

A trava mais portátil que existe, e que funciona com **qualquer** agente, de qualquer
fornecedor, hoje e daqui a cinco anos:

```
O agente não tem o token. Ponto.
```

Padrões:

- **Broker de credencial.** O agente chama `./bin/deploy`, que pede o token a um processo
  separado; o broker só libera mediante verificação (`./trava selo conferir producao --estrito`).
  O segredo nunca entra no ambiente do agente.
- **Ambiente segregado.** O agente roda com um usuário do sistema sem chave SSH, sem
  `~/.aws/credentials`, sem `GH_TOKEN`. Ele pode tentar o que quiser.
- **Escopo mínimo do token.** Token de leitura para o agente explorador, token de escrita
  só na pipeline que roda depois da revisão humana.

Nenhum prompt é necessário. Nenhum hook pode ter bug. **Isto sobrevive a um agente
adversário**, que é o que nenhuma outra camada deste documento faz.

---

## 4. Sistema de arquivos e SO

```bash
chmod 444 config/producao.yaml         # o agente não sobrescreve
chattr +i .claude/hooks/trava_gate.py  # imutável mesmo para root (ext4, precisa de root p/ setar)
mount -o remount,ro /dados/referencia  # partição inteira somente-leitura
```

Rodando o agente em container:

```bash
docker run --rm \
  --read-only \
  --tmpfs /tmp \
  --network none \
  -v "$PWD/src:/app/src:rw" \
  -v "$PWD/.claude:/app/.claude:ro" \
  imagem-do-agente
```

`--network none` é a trava de exfiltração definitiva: nenhum hook precisa inspecionar
URLs porque não há rota para lugar nenhum. `:ro` no `.claude` resolve a autoproteção da §R10
de forma completa — inclusive contra `Bash(cat >)`, que `permissions.deny` não cobre.

---

## 5. Git como trava

O `pre-commit` hook do git é universal: funciona para o agente, para você, para o CI, em
qualquer runtime, sem nenhuma relação com IA.

```bash
# .git/hooks/pre-commit
#!/usr/bin/env bash
set -e
./trava selo conferir testes-verdes --estrito || {
  echo "commit bloqueado: testes não passam agora (verificação re-executada)" >&2
  exit 1
}
```

Note a reutilização: **o mesmo verificador** (`./trava selo conferir --estrito`) serve ao hook
do Claude Code (N3) e ao hook do git (N2). Essa é a chave da portabilidade — ver
[06-portabilidade.md](06-portabilidade.md).

Outras travas nativas do git: branch protegida no servidor, required status checks,
required reviewers. São travas server-side — o agente não consegue contorná-las nem com
root na própria máquina.

---

## 6. Onde N4 é ruim

Honestidade, para não vender N4 como resposta universal:

- **Não negocia.** Não existe "a menos que". Um `deny` de `curl` bloqueia também o `curl`
  legítimo que você ia querer às 3h da manhã.
- **Não explica.** O agente recebe uma recusa genérica do harness e frequentemente não
  entende por quê → tenta variações → queima tokens. Compense com N0 no prompt do agente:
  diga o que está bloqueado e por quê, antes de ele descobrir batendo.
- **Não tem validade.** Não expira, não depende de fase. Se a restrição é "nesta fase não",
  N4 é o instrumento errado — use N3, que lê estado.
- **Custo de manutenção.** Listas de `deny` envelhecem e ficam furadas. Revise.

**A divisão de trabalho correta:**

```
N4  o que jamais pode acontecer, em nenhuma fase, por ninguém
N3  o que pode acontecer, na ordem certa, com prova   ← o grosso
N0  a explicação de N4 e N3, para o agente não bater às cegas
```
