#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lib_trava.py — núcleo do TRAVA-KIT.

Estende o núcleo original (selos HMAC, contadores, veredito) com o que o kit
acrescenta:

  * LEDGER ENCADEADO      auditoria append-only com hash-chain (à prova de edição)
  * ESPELHO HUMANO        AUDITORIA.md, linha a linha, legível por gente
  * FORENSE + ROLLBACK    imagem-anterior de todo arquivo tocado, por sessão
  * PAPÉIS                executor / fiscal / operador — derivado de QUEM ESCREVEU
  * IMPOSIÇÃO             liga/desliga auditado, com TTL e exigência de TTY
  * BANCADA               o teste humano: estado, laudo, tempo mínimo de uso

Sem dependências externas. Python 3.8+.

═══ MODELO DE AMEAÇA (não infle isto ao repassar) ═══
O HMAC e o hash-chain protegem contra FABRICAÇÃO CASUAL e contra EDIÇÃO SILENCIOSA
do histórico. Não protegem contra um agente com shell irrestrito que leia
.trava/chave.secreta ou apague .trava/ inteiro. Para isso existe N4:
permissions.deny, toolset restrito, filesystem somente-leitura, credencial ausente.
Ver docs/05-travas-sem-hook.md e docs/14-modelo-de-ameacas.md.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSAO_KIT = "1.0.0"

# ═══════════════════════════════════════════════════════ caminhos e estado


def raiz_projeto() -> Path:
    """Raiz do projeto. CLAUDE_PROJECT_DIR é definido pelo runtime nos hooks.
    Nunca confie no cwd do processo de hook: ele não é garantido."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def dir_estado() -> Path:
    d = raiz_projeto() / ".trava"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sub(nome: str) -> Path:
    d = dir_estado() / nome
    d.mkdir(parents=True, exist_ok=True)
    return d


def dir_selos() -> Path:       return _sub("selos")
def dir_contadores() -> Path:  return _sub("contadores")
def dir_contexto() -> Path:    return _sub("contexto")
def dir_forense() -> Path:     return _sub("forense")
def dir_bancada() -> Path:     return _sub("bancada")
def dir_laudos() -> Path:      return _sub("laudos")


def agora() -> int:
    return int(time.time())


def iso(ts: Optional[int] = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts if ts is not None else agora()))


# ═══════════════════════════════════════════════════════ chave e assinatura


def _caminho_chave() -> Path:
    return dir_estado() / "chave.secreta"


def _chave() -> bytes:
    """Chave HMAC do projeto. Gerada na primeira execução, 0600."""
    p = _caminho_chave()
    if not p.exists():
        p.write_bytes(secrets.token_bytes(32))
        try:
            p.chmod(0o600)
        except OSError:
            pass
    return p.read_bytes()


def _assinar(corpo: Dict[str, Any]) -> str:
    """HMAC-SHA256 sobre a serialização canônica do corpo (sem o campo 'hmac')."""
    limpo = {k: v for k, v in corpo.items() if k != "hmac"}
    bruto = json.dumps(limpo, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hmac.new(_chave(), bruto.encode("utf-8"), hashlib.sha256).hexdigest()


def sha256_texto(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8", "replace")).hexdigest()


# ═══════════════════════════════════════════════════════════════════ SELOS


def emitir_selo(nome: str, comando: str, ttl: int = 1800,
                cwd: Optional[str] = None, timeout: int = 300) -> Tuple[bool, Dict[str, Any]]:
    """EXECUTA `comando` e, se o código de saída for 0, grava um selo assinado.

    Este é o ponto onde "eu validei" deixa de ser afirmação e vira fato: o selo
    só nasce de uma execução real com rc == 0. Declarar não emite selo. Rodar emite.
    """
    inicio = time.time()
    try:
        r = subprocess.run(comando, shell=True, capture_output=True, text=True,
                           cwd=cwd or str(raiz_projeto()), timeout=timeout)
        rc, saida = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        rc, saida = 124, f"TIMEOUT após {timeout}s"
    except Exception as e:  # noqa: BLE001
        rc, saida = 125, f"ERRO AO EXECUTAR: {e!r}"

    corpo: Dict[str, Any] = {
        "nome": nome, "comando": comando, "rc": rc, "ok": rc == 0,
        "digest_saida": sha256_texto(saida), "trecho_saida": saida[-1200:],
        "emitido_em": int(inicio), "duracao_s": round(time.time() - inicio, 3),
        "ttl": int(ttl), "sessao": sessao_atual(),
    }
    corpo["hmac"] = _assinar(corpo)

    if corpo["ok"]:
        (dir_selos() / f"{nome}.json").write_text(
            json.dumps(corpo, indent=2, ensure_ascii=False), encoding="utf-8")
    auditar(evento="selo", decisao="emitido" if corpo["ok"] else "recusado",
            trava=nome, motivo=f"rc={rc} cmd={comando}")
    return corpo["ok"], corpo


def conferir_selo(nome: str, estrito: bool = False) -> Tuple[bool, str]:
    """Confere um selo. Retorna (valido, motivo_legivel).

    V1 existe · V2 HMAC bate e rc==0 · TTL · V3 (estrito) RE-EXECUTA agora.
    """
    p = dir_selos() / f"{nome}.json"
    if not p.exists():
        return False, f"selo '{nome}' não existe (esperado em {p})"
    try:
        corpo = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return False, f"selo '{nome}' ilegível: {e!r}"

    if not hmac.compare_digest(_assinar(corpo), str(corpo.get("hmac", ""))):
        return False, f"selo '{nome}' com assinatura INVÁLIDA (foi editado à mão?)"
    if not corpo.get("ok") or corpo.get("rc") != 0:
        return False, f"selo '{nome}' registra falha (rc={corpo.get('rc')})"

    ttl = int(corpo.get("ttl", 0))
    idade = agora() - int(corpo.get("emitido_em", 0))
    if ttl > 0 and idade > ttl:
        return False, f"selo '{nome}' EXPIROU (idade {idade}s > ttl {ttl}s); reemita"

    if estrito:
        try:
            r = subprocess.run(corpo.get("comando", ""), shell=True, capture_output=True,
                               text=True, cwd=str(raiz_projeto()), timeout=300)
            if r.returncode != 0:
                return False, (f"selo '{nome}' em modo ESTRITO: a verificação foi "
                               f"re-executada agora e FALHOU (rc={r.returncode}). "
                               f"O estado mudou desde a emissão.")
        except Exception as e:  # noqa: BLE001
            return False, f"selo '{nome}' estrito: re-execução falhou: {e!r}"

    return True, f"selo '{nome}' válido (idade {idade}s)"


def revogar_selo(nome: str) -> bool:
    p = dir_selos() / f"{nome}.json"
    if p.exists():
        p.unlink()
        auditar(evento="selo", decisao="revogado", trava=nome, motivo="revogação explícita")
        return True
    return False


# ═══════════════════════════════════════════════ contadores (anti-loop)


def _p_contador(chave: str) -> Path:
    return dir_contadores() / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', chave)[:120]}.json"


def incrementar(chave: str) -> int:
    p = _p_contador(chave)
    n = 0
    if p.exists():
        try:
            n = int(json.loads(p.read_text(encoding="utf-8")).get("n", 0))
        except Exception:  # noqa: BLE001
            n = 0
    n += 1
    p.write_text(json.dumps({"n": n, "em": agora()}), encoding="utf-8")
    return n


def ler_contador(chave: str) -> int:
    p = _p_contador(chave)
    if not p.exists():
        return 0
    try:
        return int(json.loads(p.read_text(encoding="utf-8")).get("n", 0))
    except Exception:  # noqa: BLE001
        return 0


def zerar(chave: str) -> None:
    p = _p_contador(chave)
    if p.exists():
        p.unlink()


# ═══════════════════════════ LEDGER ENCADEADO (auditoria à prova de edição)
#
# Cada linha carrega o hash da linha anterior. Editar ou remover qualquer linha
# do meio quebra a cadeia a partir dali, e `trava auditoria --verificar` aponta
# a linha exata. Não impede a edição — torna a edição VISÍVEL, que é o que uma
# auditoria precisa fazer.


def _p_ledger() -> Path:
    return dir_estado() / "auditoria.jsonl"


def _ultimo_hash() -> str:
    p = _p_ledger()
    if not p.exists() or p.stat().st_size == 0:
        return "0" * 64
    try:
        with p.open("rb") as fh:
            fh.seek(max(0, p.stat().st_size - 8192))
            ultimas = fh.read().decode("utf-8", "replace").strip().splitlines()
        for linha in reversed(ultimas):
            if linha.strip():
                return json.loads(linha).get("hash", "0" * 64)
    except Exception:  # noqa: BLE001
        pass
    return "0" * 64


def auditar(**campos: Any) -> None:
    """Append-only encadeado. Sem isto você não sabe se a trava disparou ou se
    nem rodou — e são bugs completamente diferentes."""
    campos.setdefault("ts", agora())
    campos.setdefault("iso", iso(campos["ts"]))
    campos.setdefault("sessao", sessao_atual())
    campos["prev"] = _ultimo_hash()
    corpo = json.dumps(campos, ensure_ascii=False, sort_keys=True)
    campos["hash"] = hashlib.sha256(corpo.encode("utf-8")).hexdigest()
    try:
        with _p_ledger().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(campos, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass  # auditoria NUNCA pode derrubar a trava
    _espelhar_humano(campos)


def _espelhar_humano(c: Dict[str, Any]) -> None:
    """AUDITORIA.md — o mesmo evento, legível por uma pessoa, linha a linha.
    O JSONL é para programa; este é para quem vai perguntar 'o que houve aqui?'."""
    p = raiz_projeto() / "AUDITORIA.md"
    try:
        novo = not p.exists()
        with p.open("a", encoding="utf-8") as fh:
            if novo:
                fh.write("# AUDITORIA — histórico de eventos da TRAVA\n\n"
                         "Append-only. Espelho legível de `.trava/auditoria.jsonl`.\n"
                         "Verifique a integridade da cadeia com: `./trava auditoria --verificar`\n\n"
                         "| quando (UTC) | evento | decisão | trava/alvo | motivo |\n"
                         "|---|---|---|---|---|\n")
            def esc(v: Any) -> str:
                return str(v).replace("|", "\\|").replace("\n", " ")[:220]
            fh.write(f"| {c.get('iso','')} | {esc(c.get('evento',''))} "
                     f"| {esc(c.get('decisao',''))} "
                     f"| {esc(c.get('trava') or c.get('ferramenta') or c.get('alvo') or '')} "
                     f"| {esc(c.get('motivo',''))} |\n")
    except OSError:
        pass


def verificar_ledger() -> Tuple[bool, str, int]:
    """Recalcula a cadeia inteira. Retorna (integra, mensagem, n_linhas)."""
    p = _p_ledger()
    if not p.exists():
        return True, "ledger vazio", 0
    anterior = "0" * 64
    n = 0
    for n, linha in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        if not linha.strip():
            continue
        try:
            reg = json.loads(linha)
        except Exception as e:  # noqa: BLE001
            return False, f"linha {n}: JSON inválido ({e})", n
        if reg.get("prev") != anterior:
            return False, (f"linha {n}: elo quebrado — 'prev' é {reg.get('prev','')[:12]}…, "
                           f"esperado {anterior[:12]}…. Alguma linha anterior foi "
                           f"editada ou removida."), n
        esperado = hashlib.sha256(
            json.dumps({k: v for k, v in reg.items() if k != "hash"},
                       ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        if esperado != reg.get("hash"):
            return False, f"linha {n}: conteúdo alterado (hash não confere)", n
        anterior = reg["hash"]
    return True, f"cadeia íntegra: {n} registro(s)", n


# ═══════════════════════════════════ FORENSE: imagem-anterior e rollback
#
# Antes de cada escrita, guardamos o conteúdo ANTERIOR do arquivo. Isso dá duas
# coisas que nenhum log de texto dá: prova do que existia, e rollback real.


def registrar_forense(sessao: str, caminho: str, ferramenta: str) -> Optional[str]:
    """Guarda a imagem-anterior do arquivo. Retorna o id do evento forense."""
    alvo = Path(caminho)
    if not alvo.is_absolute():
        alvo = raiz_projeto() / caminho
    d = dir_forense() / re.sub(r"[^A-Za-z0-9_.-]", "_", sessao or "sem-sessao")
    d.mkdir(parents=True, exist_ok=True)
    seq = incrementar(f"forense_{sessao}")
    ident = f"{seq:05d}"
    meta = {"id": ident, "ts": agora(), "iso": iso(), "sessao": sessao,
            "ferramenta": ferramenta, "caminho": str(alvo),
            "existia": alvo.exists(), "papel": papel_atual()}
    if alvo.exists() and alvo.is_file():
        try:
            if alvo.stat().st_size <= 4 * 1024 * 1024:   # 4 MB: não vira depósito
                destino = d / f"{ident}.antes"
                shutil.copy2(alvo, destino)
                meta["antes"] = str(destino)
                meta["sha256_antes"] = hashlib.sha256(alvo.read_bytes()).hexdigest()
            else:
                meta["antes"] = None
                meta["nota"] = "arquivo grande demais para snapshot (>4MB)"
        except OSError as e:
            meta["erro"] = repr(e)
    (d / f"{ident}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                     encoding="utf-8")
    return ident


def listar_forense(sessao: Optional[str] = None) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    raizes = [dir_forense() / sessao] if sessao else sorted(dir_forense().glob("*"))
    for d in raizes:
        if not d.is_dir():
            continue
        for j in sorted(d.glob("*.json")):
            try:
                out.append(json.loads(j.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                pass
    return sorted(out, key=lambda r: r.get("ts", 0))


def rollback(sessao: str, ate_id: Optional[str] = None) -> List[str]:
    """Restaura as imagens-anteriores de uma sessão, do mais recente ao mais
    antigo. Retorna a lista de arquivos restaurados."""
    eventos = [e for e in listar_forense(sessao) if e.get("antes")]
    if ate_id:
        eventos = [e for e in eventos if e["id"] >= ate_id]
    restaurados = []
    for e in sorted(eventos, key=lambda r: r["id"], reverse=True):
        origem, destino = Path(e["antes"]), Path(e["caminho"])
        if origem.exists():
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino)
            restaurados.append(str(destino))
    auditar(evento="forense", decisao="rollback", trava=sessao,
            motivo=f"{len(restaurados)} arquivo(s) restaurado(s)")
    return restaurados


# ═══════════════════════════════════════════════════════════════ SESSÃO


_SESSAO_CACHE: Optional[str] = None


def definir_sessao(s: str) -> None:
    global _SESSAO_CACHE
    _SESSAO_CACHE = s or "sem-sessao"


def sessao_atual() -> str:
    return _SESSAO_CACHE or os.environ.get("CLAUDE_SESSION_ID") or "cli"


# ═══════════════════════════════════════════════════ PAPÉIS (executor ≠ fiscal)
#
# O papel NÃO é uma declaração: é derivado do LEDGER. Quem escreveu arquivo de
# produto é executor daquele trabalho, para sempre, e não pode assinar o laudo
# que o julga. É a regra mais importante do kit depois da bancada.


def registrar_papel(tipo: str, sessao: str, descricao: str = "") -> None:
    (dir_contexto() / "papel_atual.json").write_text(json.dumps(
        {"tipo": tipo, "sessao": sessao, "descricao": descricao, "em": agora()},
        ensure_ascii=False), encoding="utf-8")
    auditar(evento="papel", decisao="registrado", trava=tipo, motivo=descricao[:200])


def papel_atual() -> Optional[str]:
    p = dir_contexto() / "papel_atual.json"
    if not p.exists():
        return None
    try:
        return (json.loads(p.read_text(encoding="utf-8")).get("tipo") or "").strip() or None
    except Exception:  # noqa: BLE001
        return None


def registrar_escrita_de_produto(sessao: str, caminho: str) -> None:
    """Marca que ESTA sessão escreveu produto. Base da separação de papéis."""
    p = dir_contexto() / "executores.json"
    dados = {}
    if p.exists():
        try:
            dados = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            dados = {}
    reg = dados.setdefault(sessao or "sem-sessao", {"arquivos": [], "desde": agora()})
    if caminho not in reg["arquivos"]:
        reg["arquivos"].append(caminho)
    reg["ate"] = agora()
    p.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")


def sessoes_executoras() -> Dict[str, Any]:
    p = dir_contexto() / "executores.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def eh_executor(sessao: str) -> bool:
    return sessao in sessoes_executoras()


def conflito_de_papel(sessao_fiscal: str) -> Optional[str]:
    """Retorna o motivo se o fiscal for (ou tiver sido) executor. None se ok.

    DERIVADO, não declarado: consulta quem de fato escreveu produto.
    """
    execs = sessoes_executoras()
    if sessao_fiscal in execs:
        arqs = execs[sessao_fiscal]["arquivos"][:5]
        return (f"a sessão '{sessao_fiscal}' escreveu arquivos de produto "
                f"({', '.join(arqs)}{'…' if len(execs[sessao_fiscal]['arquivos']) > 5 else ''}) "
                f"e portanto é EXECUTORA. Executor não fiscaliza o próprio trabalho.")
    return None


# ═══════════════════════════════════════════ IMPOSIÇÃO (liga/desliga auditado)
#
# Desligar a trava é legítimo — troubleshooting, incidente, exploração. O que
# não é legítimo é desligar sem deixar rastro, sem motivo e para sempre. Por
# isso: exige motivo, expira sozinho, é registrado, e o AGENTE não consegue.


def _p_imposicao() -> Path:
    return dir_estado() / "imposicao.json"


def estado_imposicao() -> Dict[str, Any]:
    p = _p_imposicao()
    if not p.exists():
        return {"ativa": True, "motivo": "padrão", "expira_em": 0}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"ativa": True, "motivo": "estado ilegível — FALHA FECHADA", "expira_em": 0}
    # Expirou? Volta a impor sozinha. Modo de escape sem prazo é modo permanente.
    if not d.get("ativa") and int(d.get("expira_em", 0)) and agora() > int(d["expira_em"]):
        return {"ativa": True, "motivo": "a suspensão expirou", "expira_em": 0,
                "expirou_de": d.get("motivo", "")}
    return d


def imposicao_ativa() -> bool:
    return bool(estado_imposicao().get("ativa", True))


def definir_imposicao(ativa: bool, motivo: str, minutos: int = 60,
                      por: str = "humano") -> Dict[str, Any]:
    d = {"ativa": bool(ativa), "motivo": motivo, "por": por, "em": agora(),
         "expira_em": 0 if ativa else agora() + max(1, min(minutos, 240)) * 60}
    _p_imposicao().write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    auditar(evento="imposicao", decisao="ativada" if ativa else "SUSPENSA",
            trava="imposicao", motivo=f"{motivo} (por={por}, expira={iso(d['expira_em']) if d['expira_em'] else '-'})")
    return d


# ═══════════════════════════════════════════════════════════════ BANCADA
#
# A bancada é o teste humano: sentar, pegar mouse e teclado, usar, perceber e
# dar uma opinião. O programa NÃO julga a experiência — ele só garante que a
# sessão de uso aconteceu, que durou tempo de gente, e que a opinião é uma
# opinião (não "200 ok").


def _p_bancada() -> Path:
    return dir_bancada() / "sessao_atual.json"


def abrir_bancada(alvo: str, roteiro: List[str], por: str = "humano") -> Dict[str, Any]:
    d = {"alvo": alvo, "roteiro": roteiro, "por": por, "aberta_em": agora(),
         "fechada_em": 0, "fingerprint": fingerprint_produto()}
    _p_bancada().write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    auditar(evento="bancada", decisao="aberta", trava=alvo,
            motivo=f"roteiro com {len(roteiro)} passo(s), por={por}")
    return d


def estado_bancada() -> Optional[Dict[str, Any]]:
    p = _p_bancada()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


# ══════════════════════════════════════════ fingerprint do código de produto
#
# Amarra toda prova a UMA versão do código. Sem isto, "validei ontem" cobre o
# código de hoje — e essa é a fraude mais comum, e a mais inocente.


EXT_PRODUTO = {".py", ".js", ".ts", ".tsx", ".jsx", ".vue", ".svelte", ".go", ".rs",
               ".cs", ".cpp", ".c", ".h", ".java", ".kt", ".rb", ".php", ".swift",
               ".gd", ".shader", ".glsl", ".hlsl", ".css", ".scss", ".html", ".htm"}
IGNORAR = {".trava", ".claude", ".git", "node_modules", "dist", "build", ".next",
           "__pycache__", ".venv", "venv", "vendor", "target", ".pytest_cache"}


def arquivos_de_produto() -> List[Path]:
    raiz = raiz_projeto()
    cfg = carregar_contrato().get("produto", {})
    exts = set(cfg.get("extensoes") or EXT_PRODUTO)
    ignorar = set(cfg.get("ignorar") or []) | IGNORAR
    out = []
    for p in raiz.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        if ignorar & set(p.relative_to(raiz).parts):
            continue
        out.append(p)
    return sorted(out)


def fingerprint_produto() -> str:
    """sha256 estável da árvore de produto. Ordem fixa é obrigatória: sem sort,
    o hash oscila e a trava vira loop infinito."""
    h = hashlib.sha256()
    raiz = raiz_projeto()
    for p in arquivos_de_produto():
        h.update(p.relative_to(raiz).as_posix().encode())
        try:
            h.update(hashlib.sha256(p.read_bytes()).digest())
        except OSError:
            pass
    return "sha256:" + h.hexdigest()[:32]


def produto_mudou_desde(ts: int) -> Optional[str]:
    """Nome do arquivo de produto alterado depois de `ts`, se houver."""
    for p in arquivos_de_produto():
        try:
            if p.stat().st_mtime > ts:
                return str(p.relative_to(raiz_projeto()))
        except OSError:
            pass
    return None


# ═══════════════════════════════════════════════════ entrada e veredito


def ler_payload() -> Dict[str, Any]:
    """Lê o JSON que o runtime escreve no stdin. Nunca levanta."""
    try:
        bruto = sys.stdin.read()
        p = json.loads(bruto) if bruto.strip() else {}
    except Exception:  # noqa: BLE001
        p = {}
    if p.get("session_id"):
        definir_sessao(p["session_id"])
    return p


def _emitir(obj: Dict[str, Any]) -> None:
    """stdout de um hook é parseado como veredito: só JSON sai por aqui.
    Um print() de debug perdido corrompe o veredito — debug vai em auditar()."""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))
    sys.stdout.flush()


def negar(motivo: str) -> None:
    """PreToolUse: cancela a chamada. O motivo vai para o MODELO."""
    _emitir({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                    "permissionDecision": "deny",
                                    "permissionDecisionReason": motivo}})
    sys.exit(0)


def perguntar(motivo: str) -> None:
    """PreToolUse: devolve ao USUÁRIO para confirmação manual.

    Este é o canal de PROVA DE HUMANO do kit: a resposta é dada no canal do
    usuário, no runtime, onde o agente não alcança. Assinatura em arquivo não
    prova nada — um agente escreve 'nome: fulano'. Um `ask` respondido, sim.
    """
    _emitir({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                    "permissionDecision": "ask",
                                    "permissionDecisionReason": motivo}})
    sys.exit(0)


def permitir(motivo: str = "") -> None:
    """PreToolUse: libera PULANDO o sistema de permissões. Use com parcimônia."""
    _emitir({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                    "permissionDecision": "allow",
                                    "permissionDecisionReason": motivo}})
    sys.exit(0)


def seguir() -> None:
    """Não opina: deixa o fluxo normal de permissões decidir. O caminho comum."""
    sys.exit(0)


def bloquear_encerramento(motivo: str) -> None:
    """Stop/SubagentStop: o agente NÃO encerra e recebe `motivo` como instrução.
    `motivo` é o único texto que ele vê. Vazio aqui = agente preso."""
    _emitir({"decision": "block", "reason": motivo})
    sys.exit(0)


def avisar(msg: str) -> None:
    """Mensagem ao usuário, sem bloquear nada."""
    _emitir({"systemMessage": msg})
    sys.exit(0)


def injetar_contexto(evento: str, texto: str) -> None:
    _emitir({"hookSpecificOutput": {"hookEventName": evento, "additionalContext": texto}})
    sys.exit(0)


# ═══════════════════════════════════════════════════════════════ CONTRATO


def carregar_contrato() -> Dict[str, Any]:
    p = dir_estado() / "contrato.json"
    if not p.exists():
        return {"versao": 1, "travas": [], "saida_subagente": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        # FALHA FECHADA: contrato corrompido é motivo para desconfiar, não para liberar.
        auditar(evento="contrato", decisao="erro", motivo=repr(e))
        return {"versao": 1, "travas": [], "saida_subagente": {}, "_erro": repr(e)}


def alvo_da_ferramenta(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Texto representativo da ação, para casar contra regex do contrato.
    É aqui que o gate enxerga 'o que está sendo feito'."""
    ti = tool_input or {}
    if tool_name == "Bash":
        return str(ti.get("command", ""))
    if tool_name in ("Write", "Edit", "MultiEdit", "NotebookEdit", "Read"):
        return str(ti.get("file_path") or ti.get("notebook_path") or ti.get("path") or "")
    if tool_name == "Task":
        return " ".join(str(ti.get(k, "")) for k in ("subagent_type", "description", "prompt"))
    if tool_name in ("WebFetch", "WebSearch"):
        return str(ti.get("url", "")) + " " + str(ti.get("query", ""))
    if tool_name in ("Glob", "Grep"):
        return str(ti.get("pattern", "")) + " " + str(ti.get("path", ""))
    return json.dumps(ti, ensure_ascii=False)


def caminhos_da_ferramenta(tool_name: str, tool_input: Dict[str, Any]) -> List[str]:
    """TODOS os caminhos que a chamada pode tocar — inclusive dentro do comando
    Bash. Filtrar só `file_path` é o furo clássico: `echo x > arquivo` passa."""
    ti = tool_input or {}
    out = []
    for k in ("file_path", "notebook_path", "path"):
        if ti.get(k):
            out.append(str(ti[k]))
    if tool_name == "Bash":
        cmd = str(ti.get("command", ""))
        out += re.findall(r"(?:>|>>|\btee\b|\bsed\s+-i\b\s*\S*)\s*([\w./~-]+)", cmd)
        out += re.findall(r"\b(?:rm|mv|cp|truncate|install|dd\s+of=)\s+(?:-\S+\s+)*([\w./~-]+)", cmd)
    return out
