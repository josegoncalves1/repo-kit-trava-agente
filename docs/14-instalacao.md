# 14 — Instalação e distribuição

## 1. O que é extraído, e onde

O kit instala **na raiz do projeto alvo**, convivendo com o que já existe. Ele não
move nada seu, não apaga nada seu, e nunca sobrescreve um contrato existente.

```
/seu/projeto/                      ← Dockerfile, src/, package.json… continuam aqui
├── trava                          ★ o CLI (atalho para .trava/bin/trava)
├── AUDITORIA.md                   ★ histórico legível, criado no 1º evento
├── CONTRATO-DE-ENTREGA.md         ★ o contrato, para agente e humano
├── output/                        ★ relatórios, revisões, laudo de bancada
├── evidencias/                    ★ capturas de tela e vídeo
├── .trava/                        ★ o cofre: estado, provas, forense
│   ├── contrato.json                 a DECLARAÇÃO das travas (você edita)
│   ├── contrato.exemplo.json         o exemplo completo, para consultar
│   ├── bloco-contrato.md             o texto obrigatório no prompt de sub-agente
│   ├── chave.secreta                 HMAC, 0600, gerada no 1º uso — fora do git
│   ├── auditoria.jsonl               ledger encadeado por hash
│   ├── imposicao.json                ligada/suspensa, com motivo e prazo
│   ├── selos/                        provas assinadas
│   ├── contadores/                   fusíveis anti-loop
│   ├── contexto/                     papel atual + quem escreveu produto
│   ├── forense/<sessao>/             imagem-anterior de cada arquivo tocado
│   ├── bancada/                      sessão de teste humano
│   ├── formularios/laudo-bancada.md  o formulário em branco
│   └── bin/{trava,testar_travas.sh}
└── .claude/
    ├── settings.json              ← FUNDIDO (backup datado, nunca substituído)
    ├── hooks/*.py                 ★ os executores das travas
    ├── agents/trava-*.md          ★ executor, fiscal, operador, auditor-doc
    ├── commands/trava-*.md        ★ /trava-status, /trava-off, /trava-bancada…
    └── skills/trava-*/SKILL.md    ★ entrega, bancada, equipe
```

## 2. Instalar

```bash
# no diretório do projeto
curl -fsSL https://raw.githubusercontent.com/josegoncalves1/repo-kit-trava-agente/main/setup.sh | sh
```

> ⚠️ Você está prestes a rodar um script baixado da internet, com as suas
> credenciais, que instala **hooks — código que roda a cada chamada de
> ferramenta**. Leia antes:
> ```bash
> curl -fsSL https://raw.githubusercontent.com/josegoncalves1/repo-kit-trava-agente/main/setup.sh | less
> ```
> Este aviso vale para este kit tanto quanto para qualquer outro.

Variações:

```bash
./setup.sh                    # contrato MÍNIMO, adaptado ao projeto (recomendado)
./setup.sh --completo         # o contrato de exemplo inteiro
./setup.sh --dry-run          # mostra o que faria, sem tocar em nada
./setup.sh --destino /outro   # instala em outro diretório

TRAVA_REPO=fulano/trava-kit TRAVA_REF=v1.0.0 sh setup.sh   # fixar origem e versão
```

Requisito único: **python3** (só biblioteca padrão; nenhuma dependência externa).
`curl`/`wget` e `tar` só são necessários quando se instala pelo pipe.

## 3. O que o setup.sh faz, passo a passo

### 1 — detecta como ESTE projeto verifica
Procura `package.json` (`npm test`), `pyproject.toml`/`tests/` (`pytest`),
`Cargo.toml`, `go.mod`, `Makefile` com alvo `test:` e, por último, scripts
próprios (`validar.sh`, `check.sh`, `scripts/check.sh`).

> Isto existe porque um contrato com `pytest` fixo num projeto Node trava para
> sempre — e a primeira coisa que alguém faz é desligar a trava inteira. Se nada
> for detectado, a trava de teste nasce **desligada**, com aviso. Melhor desligada
> que bloqueando `git push` sem caminho de saída.

### 2 — extrai os artefatos
Copia hooks, agentes, comandos, skills, CLI e formulários. Cria `output/` e
`evidencias/`. Escreve o atalho `./trava` na raiz.

### 3 — gera o contrato (nunca sobrescreve)
Se `.trava/contrato.json` já existe, é **preservado**, e o exemplo completo é
copiado ao lado para comparação manual.

### 4 — registra os hooks em `.claude/settings.json` ← **o passo que a cópia não faz**
Copiar os `.py` não liga nada: eles ficam inertes até que a chave `"hooks"`
registre cada um num evento. **A falha em fazer isso é silenciosa** — nenhum erro,
nenhum aviso, nenhuma trava.

O merge é seguro:
- backup datado (`settings.json.bak-AAAAMMDD-HHMMSS`);
- **funde**, preserva `model`, `permissions.allow` e tudo o mais;
- **idempotente**: comparar comandos por igualdade exata, não substring sobre
  `json.dumps` — as aspas viram `\"` na serialização e a comparação nunca casa.
  Foi assim que a idempotência quebrou na primeira versão deste script;
- aborta se o `settings.json` existente for JSON inválido, em vez de sobrescrever.

### 5 — escreve o `.gitignore`
```
.trava/chave.secreta      .trava/selos/       .trava/contadores/
.trava/forense/           .trava/bancada/     evidencias/
```
Estado e segredo ficam fora do git. **`AUDITORIA.md` e `.trava/auditoria.jsonl`
ficam dentro** — histórico se versiona.

### 6 — prova que as travas travam
Roda `.trava/bin/testar_travas.sh` (22 verificações). Se alguma falhar, o
instalador avisa e aponta o log. Ele também avisa quando o contrato gerado tem
poucas travas:

> **"Instalado" não é "protegido".** Os hooks podem estar ativos e o contrato
> vazio — nesse caso nada é bloqueado no dia a dia. A trava de **entrega** (a
> bancada humana) vem ativa por padrão, e é a que mais importa; o resto é você
> quem calibra.

## 4. O passo que só você pode dar

**Reinicie a sessão do agente.**

Hooks são capturados na inicialização da sessão. Editar `settings.json` com a
sessão aberta não ativa nada — e isso é proposital: evita que um agente com
acesso ao disco recarregue travas que ele mesmo alterou no meio do caminho.

Depois:

```bash
./trava status      # o que está sendo imposto
./trava doutor      # está viva, ou é enfeite?
/trava-status       # o mesmo, de dentro do agente
```

Se `.trava/auditoria.jsonl` não crescer quando você pedir algo ao agente, o hook
**nem rodou** — é configuração (matcher com caixa errada, caminho, sessão não
reiniciada), não lógica. Ver [08](08-provar-que-trava.md).

## 5. Atualizar

```bash
curl -fsSL https://raw.githubusercontent.com/josegoncalves1/repo-kit-trava-agente/main/setup.sh | sh
```

Rodar de novo é seguro: o merge é idempotente e o contrato é preservado. O que é
sobrescrito são os **hooks**, o **CLI** e os **formulários** — se você editou
algum deles, faça um diff antes.

> Prática melhor: não edite os hooks. Toda a variação de comportamento cabe em
> `.trava/contrato.json`, que o setup nunca toca. Hook editado é hook que você
> vai perder no próximo update, e é também o que a autoproteção existe para
> desencorajar.

## 6. Desinstalar

```bash
rm -rf .trava .claude/hooks/trava_*.py .claude/hooks/lib_trava.py \
       .claude/hooks/verificar_*.py .claude/agents/trava-*.md \
       .claude/commands/trava-*.md .claude/skills/trava-* ./trava
# e remova a chave "hooks" do .claude/settings.json (ou restaure um .bak-*)
```

Guarde `AUDITORIA.md`: é o histórico, e ele não se recupera.

## 7. Publicar o seu próprio fork

```bash
git init && git add . && git commit -m "trava-kit"
gh repo create SEU-josegoncalves1/repo-kit-trava-agente --public --source=. --push
```

Depois troque `josegoncalves1/repo-kit-trava-agente` pelo seu caminho em:
- `setup.sh` (variável `REPO`);
- este documento (§2);
- o `README.md`.

O `setup.sh` baixa de `https://codeload.github.com/$REPO/tar.gz/$REF`, então
qualquer branch ou tag funciona como `TRAVA_REF`. Fixe uma **tag** em produção:
`main` muda debaixo de você.

## 8. Instalar em vários projetos

O kit é por projeto, de propósito: cada um tem um jeito diferente de verificar, e
um contrato compartilhado seria errado em todos. Para uma frota:

```bash
for p in ~/projetos/*/; do (cd "$p" && sh ~/trava-kit/setup.sh); done
```

Depois **revise cada `.trava/contrato.json`**. A detecção automática acerta o
comando de teste; ela não sabe o que é entrega naquele projeto específico.

---

➡️ Próximo: [15 — Modelo de ameaças](15-modelo-de-ameacas.md)
