#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar_bancada.py — o verificador do TESTE HUMANO.

═══ A PREMISSA, DITA SEM ENFEITE ═══
Testar é sentar a bunda na cadeira, pegar mouse e teclado com as duas mãos, olhar
para o monitor, usar, operar, sentir, perceber, observar — e extrair uma opinião.
Não é `curl 200`. Não é "up". Não é "os testes passaram".

É perceber. É saber, olhando, se o almoço está sendo servido ao meio-dia ou à
meia-noite. É distinguir o chato do legal, o feio do bonito, o que convida do que
afasta. Não tem conta de mais ou de menos: é notar, correlacionar e concluir.

Nenhum programa faz isso. Este aqui NÃO TENTA.

═══ O QUE ESTE PROGRAMA FAZ, ENTÃO ═══
Ele torna IMPOSSÍVEL entregar sem que uma pessoa tenha feito isso, checando o que
uma máquina checa bem:

  1. A sessão de uso ACONTECEU        — bancada aberta e fechada, com marca de tempo
  2. DUROU tempo de gente             — abaixo do mínimo não é uso, é screenshot
  3. É sobre ESTE código              — fingerprint e frescor; código novo invalida
  4. A opinião é uma OPINIÃO          — recusa "ok/funcionou/200"; exige percepção
  5. Cada pergunta foi RESPONDIDA     — e respondida com coisa diferente das outras
  6. Quem respondeu NÃO foi o executor — papel derivado do ledger, não declarado

O veredito sensorial em si continua sendo de quem sentou na cadeira. É assim que
tem que ser. A trava só garante que ele existe, que é fresco e que é dele.

USO
  verificar_bancada.py <laudo.md> [--min-segundos 180] [--fonte .] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_trava as T  # noqa: E402

FALHAS: list[str] = []


def falha(m: str) -> None:
    FALHAS.append(m)


# ─────────────────────────────────────────── o que NÃO é percepção
#
# Estas frases descrevem o estado de um PROCESSO, não a experiência de uma PESSOA.
# Sozinhas, em qualquer seção, são recusadas.
PROVA_FRACA = re.compile(
    r"^[\s\-*>]*(?:(?:http\s*)?(?:200|201|204|2xx)(?:\s*ok)?|ok(?:ay)?|"
    r"funciona(?:ndo|u)?|sem\s+erros?|nenhum\s+erro|tudo\s+(?:certo|ok|funcionando)|"
    r"passou|success(?:ful)?|healthy|up|online|no\s+ar|bom|boa|legal|"
    r"ficou\s+(?:bom|legal|bacana)|t[aá]\s+bom|perfeito|sem\s+problemas?)\W*$",
    re.I | re.M)

# ─────────────────────────────────────────── as perguntas obrigatórias
#
# São perguntas ABERTAS de propósito. Checkbox não captura percepção: ela oferece
# a resposta pronta e a pessoa marca no automático. Pergunta aberta obriga a
# formular — e formular exige ter olhado.
SECOES = {
    "## O QUE VOCÊ VIU NOS PRIMEIROS 5 SEGUNDOS": (
        120,
        "Antes de entender, antes de explorar: o que saltou aos olhos? Descreva a "
        "tela como quem nunca viu. Se você precisou de 30s para entender o que era, "
        "isso é a resposta."),
    "## O QUE VOCÊ TENTOU FAZER E O QUE ACONTECEU": (
        200,
        "A jornada, passo a passo: 'fiz X → vi Y'. Pelo menos 3 passos. O que você "
        "tentou PRIMEIRO, por instinto — e funcionou?"),
    "## ONDE VOCÊ HESITOU": (
        100,
        "Onde parou para pensar, releu, procurou, errou o clique, desfez, ou não "
        "sabia se tinha dado certo. Se não hesitou em lugar nenhum, diga o que você "
        "tentou quebrar antes de concluir isso."),
    "## O QUE INCOMODOU": (
        100,
        "Mesmo sem saber explicar por quê. Cor que cansa, espaçamento que aperta, "
        "animação que atrasa, texto que grita, botão que some. Incômodo sem "
        "justificativa técnica é dado válido — anote assim mesmo."),
    "## AS CORES E O CONFORTO": (
        100,
        "Declare os pares reais como '#RRGGBB sobre #RRGGBB' (o contraste é medido "
        "em separado). Depois: a paleta cansa a vista em sessão longa? Você "
        "trabalharia nessa tela por 3 horas?"),
    "## OS BOTÕES": (
        120,
        "Um por linha: 'nome → o que faz → funcionou? → faz sentido estar ALI?'. "
        "Um botão que funciona mas não deveria existir é um defeito."),
    "## O PROPÓSITO": (
        120,
        "Em UMA frase: o que a pessoa consegue fazer aqui. Depois: cada parte "
        "entregue serve a essa frase, ou é um monte de código junto, cada um com "
        "um propósito desconexo do outro?"),
    "## A SENSAÇÃO": (
        150,
        "A experiência observada, não a especificação. Peso, velocidade, resposta, "
        "realismo, fluidez. Onde a ilusão quebra. Se o produto promete que a areia "
        "esparrama com a passagem do caça, a pergunta é: esparrama? Ou pisca?"),
    "## VOCÊ USARIA ISSO": (
        80,
        "Três perguntas, resposta direta e o porquê: você usaria? você pagaria? "
        "você mostraria para alguém? 'Correto' e 'bom' são coisas diferentes."),
}


def corpo_secao(texto: str, sec: str) -> str:
    alvo = sec.upper()
    i = texto.upper().find(alvo)
    if i < 0:
        return ""
    return re.split(r"\n##\s", texto[i + len(alvo):])[0]


def normalizar(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("laudo")
    ap.add_argument("--min-segundos", type=int, default=180)
    ap.add_argument("--fonte", default=".")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    laudo = Path(a.laudo)
    if not laudo.exists():
        print(f"BANCADA NÃO REALIZADA: {a.laudo} não existe.\n"
              f"Ninguém sentou na cadeira. Rode: ./trava bancada abrir", file=sys.stderr)
        return 1
    texto = laudo.read_text(encoding="utf-8", errors="replace")
    # Os comentários HTML do formulário são a AJUDA, não a resposta. Sem
    # removê-los, um formulário em branco acusa "copiou a pergunta" em vez
    # de "está vazia" — mensagem errada manda a pessoa para o lugar errado.
    texto = re.sub(r"<!--.*?-->", "", texto, flags=re.S)

    # ── 1. A SESSÃO DE USO ACONTECEU, E DUROU TEMPO DE GENTE ────────────────
    b = T.estado_bancada()
    if not b:
        falha("não há registro de sessão de bancada em .trava/bancada/. "
              "O laudo existe mas ninguém abriu a bancada — a sessão de uso não "
              "foi registrada, então não há como saber que ela aconteceu.")
    else:
        if not b.get("fechada_em"):
            falha("a bancada está ABERTA e nunca foi fechada. Feche com "
                  "'./trava bancada fechar' ao terminar de usar — é o fechamento "
                  "que grava quanto tempo durou.")
        else:
            dur = int(b["fechada_em"]) - int(b["aberta_em"])
            if dur < a.min_segundos:
                falha(f"a sessão de uso durou {dur}s; mínimo {a.min_segundos}s. "
                      f"Abaixo disso não é uso, é conferência de screenshot. "
                      f"Abra a bancada, USE de verdade, depois feche.")
            # A trava anota, mas não reprova por excesso: teste longo é bom sinal.

        # ── 2. É SOBRE ESTE CÓDIGO ──────────────────────────────────────────
        fp_agora = T.fingerprint_produto()
        if b.get("fingerprint") and b["fingerprint"] != fp_agora:
            falha(f"o código de produto MUDOU depois da bancada "
                  f"(bancada: {b['fingerprint'][:20]}…, agora: {fp_agora[:20]}…). "
                  f"Você testou outra coisa. Refaça a bancada sobre o código atual.")

        # ── 3. QUEM TESTOU NÃO PODE SER QUEM CONSTRUIU ──────────────────────
        # Derivado do ledger: quem escreveu produto é executor, e ponto.
        sessao_laudo = b.get("por_sessao") or ""
        if sessao_laudo:
            conflito = T.conflito_de_papel(sessao_laudo)
            if conflito:
                falha(f"conflito de papel na bancada: {conflito} "
                      f"Quem construiu a tela não consegue ver a tela — vê a intenção. "
                      f"A bancada precisa de outra pessoa, ou de outra sessão que não "
                      f"tenha escrito produto.")

    # ── 4. O LAUDO É FRESCO ─────────────────────────────────────────────────
    mudou = T.produto_mudou_desde(int(laudo.stat().st_mtime))
    if mudou:
        falha(f"o código mudou depois do laudo ('{mudou}'). O laudo descreve um "
              f"produto que não existe mais. Teste de novo.")

    # ── 5. CADA PERGUNTA FOI RESPONDIDA, COM SUBSTÂNCIA ─────────────────────
    respostas = {}
    for sec, (minimo, ajuda) in SECOES.items():
        corpo = corpo_secao(texto, sec)
        if not corpo:
            falha(f"falta a seção obrigatória '{sec}'.\n      → {ajuda}")
            continue
        linhas = [l for l in corpo.splitlines() if l.strip() and not l.strip().startswith("#")]
        conteudo = "\n".join(linhas).strip()
        respostas[sec] = conteudo

        if not conteudo:
            falha(f"'{sec}' está vazia.\n      → {ajuda}")
        elif linhas and all(PROVA_FRACA.match(l) for l in linhas):
            falha(f"'{sec}' contém só afirmação genérica ('ok', 'funcionou', '200'). "
                  f"Isso descreve um processo respondendo, não uma pessoa usando."
                  f"\n      → {ajuda}")
        elif len(conteudo) < minimo:
            falha(f"'{sec}' tem {len(conteudo)} caracteres; mínimo {minimo}. "
                  f"Resposta rasa não é percepção.\n      → {ajuda}")
        elif normalizar(ajuda)[:60] in normalizar(conteudo):
            falha(f"'{sec}' parece ter copiado o texto da pergunta em vez de "
                  f"respondê-la.\n      → {ajuda}")

    # ── 6. AS RESPOSTAS SÃO DIFERENTES ENTRE SI ─────────────────────────────
    # Nove respostas idênticas = formulário preenchido no automático, não percepção.
    vistas = {}
    for sec, conteudo in respostas.items():
        chave = normalizar(conteudo)[:200]
        if chave and chave in vistas:
            falha(f"'{sec}' tem o mesmo conteúdo de '{vistas[chave]}'. "
                  f"Perguntas diferentes com a mesma resposta = formulário preenchido "
                  f"no automático.")
        vistas[chave] = sec

    # ── 7. A JORNADA TEM PASSOS DE VERDADE ──────────────────────────────────
    jornada = respostas.get("## O QUE VOCÊ TENTOU FAZER E O QUE ACONTECEU", "")
    passos = re.findall(r"^\s*\d+[.)]\s+.{6,}?(?:→|->|=>)\s*\S.{4,}", jornada, re.M)
    if len(passos) < 3:
        falha(f"a jornada tem {len(passos)} passo(s) no formato "
              f"'1. o que fiz → o que vi'; mínimo 3. Percorra o fluxo como usuário.")

    # ── 8. OS BOTÕES FORAM JULGADOS UM A UM ─────────────────────────────────
    botoes = re.findall(r"^\s*[-*]?\s*(.+?)\s*→\s*(.+?)\s*→\s*(.+?)\s*→\s*(.+)$",
                        respostas.get("## OS BOTÕES", ""), re.M)
    if not botoes or not any(b[0].strip(" -*") for b in botoes):
        falha("'## OS BOTÕES' precisa de pelo menos uma linha no formato "
              "'nome → o que faz → funcionou? → faz sentido estar ali?'.")
    botoes = [b for b in botoes if b[0].strip(" -*") and b[1].strip()]
    for nome, _faz, funcionou, sentido in botoes:
        if not re.search(r"\b(sim|s[ií]|funcionou|testei|cliquei|ok)\b", funcionou, re.I):
            falha(f"botão '{nome.strip()[:40]}': o campo 'funcionou?' não afirma "
                  f"teste real ('{funcionou.strip()[:40]}'). Você clicou nele?")
        if len(sentido.strip()) < 15:
            falha(f"botão '{nome.strip()[:40]}': justifique por que ele existe ALI "
                  f"('{sentido.strip()[:30]}' é raso). Funcionar não é razão para existir.")

    # ── 9. O VEREDITO DE USO É EXPLÍCITO ────────────────────────────────────
    usaria = respostas.get("## VOCÊ USARIA ISSO", "")
    if usaria and not re.search(r"\b(usaria|pagaria|mostraria)\b", usaria, re.I):
        falha("'## VOCÊ USARIA ISSO' precisa responder explicitamente às três "
              "perguntas: usaria? pagaria? mostraria para alguém?")

    # ── 10. VEREDITO FINAL ──────────────────────────────────────────────────
    m = re.search(r"^##\s*VEREDITO\s*:\s*(APROVADO|REPROVADO)\s*$", texto, re.M | re.I)
    if not m:
        falha("falta a linha final '## VEREDITO: APROVADO' ou '## VEREDITO: REPROVADO'.")
    veredito = m.group(1).upper() if m else "AUSENTE"

    rel = {"aprovado": not FALHAS, "veredito": veredito, "falhas": FALHAS,
           "duracao_s": (int(b["fechada_em"]) - int(b["aberta_em"]))
                        if b and b.get("fechada_em") else None,
           "passos_jornada": len(passos), "botoes_julgados": len(botoes)}

    if a.json:
        print(json.dumps(rel, indent=2, ensure_ascii=False))
    elif FALHAS:
        print("BANCADA INVÁLIDA — a entrega não passa:", file=sys.stderr)
        for f in FALHAS:
            print(f"  ✗ {f}", file=sys.stderr)
        print(f"\n  Formulário em branco: .trava/formularios/laudo-bancada.md", file=sys.stderr)
    else:
        print(f"  ✅ bancada válida — VEREDITO: {veredito}")
        print(f"     sessão de uso: {rel['duracao_s']}s · "
              f"{len(passos)} passos de jornada · {len(botoes)} botões julgados")

    T.auditar(evento="bancada", decisao="valida" if not FALHAS else "invalida",
              trava="verificar_bancada",
              motivo=f"veredito={veredito} falhas={len(FALHAS)}")
    return 1 if FALHAS else (0 if veredito == "APROVADO" else 2)


if __name__ == "__main__":
    sys.exit(main())
