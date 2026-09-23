#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar_entrega_ux.py — a trava de ENTREGA FINAL.

PREMISSA HONESTA
   Nenhum programa julga se a areia levantada pelo caça "parece real". Isso é
   julgamento sensorial humano. Este verificador NÃO finge julgar estética.
   Ele faz duas coisas que uma máquina faz bem, e que juntas tornam impossível
   entregar sem avaliação experiencial de verdade:

   (A) MEDE o que é mensurável, na evidência real — contraste WCAG, telas em
       branco, extremos de luminância, alvos de toque, e MOVIMENTO entre frames.
       Prosa não passa por aqui: os números saem da imagem, não do texto.
   (B) EXIGE que a evidência exista, seja fresca e seja específica; e deixa o
       veredito sensorial para um humano, que a trava obriga a ser consultado.

   "curl 200 ok" não satisfaz nada disto.

USO
   verificar_entrega_ux.py <dossie.md> --midia <dir> [--fonte <dir>]
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys
from pathlib import Path

import numpy as np
from PIL import Image

IMG = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VID = {".mp4", ".mov", ".webm", ".mkv", ".gif"}

FALHAS: list[str] = []
def falha(m: str) -> None: FALHAS.append(m)


# ─────────────────────────────────────────────── medidas objetivas


def luminancia(rgb) -> float:
    """Luminância relativa WCAG 2.x."""
    c = np.asarray(rgb, dtype=float) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])


def contraste(a, b) -> float:
    l1, l2 = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def hex_rgb(h: str):
    h = h.lstrip("#")
    if len(h) == 3: h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def analisar_imagem(p: Path) -> dict:
    """Medidas de conforto visual extraídas DA IMAGEM."""
    im = Image.open(p).convert("RGB")
    a = np.asarray(im, dtype=np.uint8)
    lum = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]) / 255.0
    mx = a.max(axis=2).astype(float); mn = a.min(axis=2).astype(float)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0.0)
    return {
        "arquivo": p.name,
        "largura": im.width, "altura": im.height,
        "variancia": float(lum.var()),                    # tela chapada ≈ 0
        "cores_unicas": int(len(np.unique(a.reshape(-1, 3), axis=0))),
        "pct_estourado": float(((lum > 0.97) | (lum < 0.03)).mean() * 100),
        "pct_saturacao_extrema": float((sat > 0.92).mean() * 100),
        "lum_media": float(lum.mean()),
    }


def movimento(video: Path, amostras: int = 12) -> dict:
    """Extrai frames e mede quanto a imagem MUDA. Prova objetiva de que algo
    se move — se o dossiê afirma 'a areia esparrama' e o delta é ~0, é mentira."""
    tmp = Path(subprocess.run(["mktemp", "-d"], capture_output=True, text=True).stdout.strip())
    subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(video),
                    "-vf", f"fps=8,scale=320:-1", "-frames:v", str(amostras),
                    str(tmp / "f%03d.png")], check=False)
    fr = sorted(tmp.glob("f*.png"))
    if len(fr) < 3:
        return {"erro": "não consegui extrair frames suficientes"}
    arr = [np.asarray(Image.open(f).convert("L"), dtype=float) for f in fr]
    n = min(a.shape for a in arr)
    deltas = [float(np.abs(arr[i + 1][:n[0], :n[1]] - arr[i][:n[0], :n[1]]).mean())
              for i in range(len(arr) - 1)]
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout.strip()
    return {"frames": len(fr), "delta_medio": round(sum(deltas) / len(deltas), 3),
            "delta_max": round(max(deltas), 3), "duracao_s": dur}


# ─────────────────────────────────────────────── seções experienciais


SECOES = {
  "## CORES": ("### PARES MEDIDOS",
    "Liste os pares reais como 'texto #RRGGBB sobre fundo #RRGGBB' — o script mede o "
    "contraste WCAG de cada um. Diga também se a paleta cansa a vista em sessão longa."),
  "## BOTÕES": ("### CADA BOTÃO",
    "Um por linha: 'nome → o que faz → funcionou? → faz sentido estar ali?'. "
    "Um botão que funciona mas não deveria existir é um defeito."),
  "## PROPÓSITO": ("### O QUE ISTO É",
    "Em uma frase, o que a pessoa consegue fazer aqui. Depois: cada parte entregue "
    "serve a essa frase, ou é código solto com propósito desconexo?"),
  "## SENSAÇÃO": ("### O QUE SE SENTE",
    "A experiência observada, não a especificação. Peso, velocidade, resposta, "
    "realismo. Onde quebra a ilusão."),
  "## VEREDITO HUMANO": ("### ASSINATURA",
    "Só uma pessoa preenche. Ver seção de assinatura."),
}
PROVA_FRACA = re.compile(
    r"^[\s\-*>]*(?:(?:http\s*)?(?:200|201|204)(?:\s*ok)?|ok|funciona(?:ndo|u)?|"
    r"sem\s+erros?|tudo\s+certo|passou|success(?:ful)?|healthy|up|bom|ficou\s+bom)\W*$",
    re.I | re.M)


def corpo_secao(texto: str, sec: str) -> str:
    i = texto.upper().find(sec)
    if i < 0: return ""
    return re.split(r"\n##\s", texto[i + len(sec):])[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dossie")
    ap.add_argument("--midia", default="evidencias")
    ap.add_argument("--fonte", default=".")
    ap.add_argument("--min-contraste", type=float, default=4.5)
    ap.add_argument("--exige-movimento", action="store_true",
                    help="entrega com animação/jogo: exige vídeo com movimento medido")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--assinatura-opcional", action="store_true",
                    help="use quando a prova de humano vier do ASK do runtime, não do texto")
    a = ap.parse_args()

    d = Path(a.dossie)
    if not d.exists():
        print(f"ENTREGA BLOQUEADA: {a.dossie} não existe. Nenhuma avaliação de UX foi feita.",
              file=sys.stderr); sys.exit(1)
    texto = d.read_text(encoding="utf-8", errors="replace")

    # ── 1. EVIDÊNCIA VISUAL: existe, é fresca, não é degenerada
    md = Path(a.midia)
    imgs = [p for p in md.rglob("*") if p.suffix.lower() in IMG] if md.exists() else []
    vids = [p for p in md.rglob("*") if p.suffix.lower() in VID] if md.exists() else []
    if not imgs:
        falha(f"nenhuma captura de tela em '{a.midia}/'. Avaliação de UX sem ver a tela "
              f"não é avaliação — é opinião sobre código.")

    medidas = []
    for p in imgs:
        m = analisar_imagem(p); medidas.append(m)
        if m["variancia"] < 0.0015 or m["cores_unicas"] < 24:
            falha(f"{p.name}: tela praticamente chapada (variância {m['variancia']:.5f}, "
                  f"{m['cores_unicas']} cores). Captura em branco/erro não é evidência.")
        if m["largura"] < 640 or m["altura"] < 400:
            falha(f"{p.name}: {m['largura']}x{m['altura']} — pequena demais para avaliar UI.")
        if m["pct_estourado"] > 55:
            falha(f"{p.name}: {m['pct_estourado']:.0f}% dos pixels em preto/branco puro — "
                  f"desconforto visual; justifique ou corrija.")
        if m["pct_saturacao_extrema"] > 35:
            falha(f"{p.name}: {m['pct_saturacao_extrema']:.0f}% da tela em saturação extrema "
                  f"— cansa a vista em sessão longa.")

    # frescor: a evidência precisa ser mais nova que o código
    raiz = Path(a.fonte).resolve()
    fontes = [p for p in raiz.rglob("*")
              if p.is_file() and p.suffix in {".py",".js",".ts",".tsx",".jsx",".go",".rs",
                                              ".cs",".cpp",".gd",".shader",".glsl",".css",".html"}
              and not {".trava",".claude",".git"} & set(p.parts)]
    if fontes and imgs:
        novo = max(fontes, key=lambda p: p.stat().st_mtime)
        if novo.stat().st_mtime > max(p.stat().st_mtime for p in imgs):
            falha(f"o código mudou depois das capturas ('{novo.name}'). As evidências não "
                  f"mostram o que está sendo entregue. Capture de novo.")

    # ── 2. MOVIMENTO medido (jogos, animação, "a areia esparramando")
    mov = None
    if a.exige_movimento:
        if not vids:
            falha(f"nenhum vídeo em '{a.midia}/'. Sensação de movimento não se avalia em "
                  f"print: grave a cena e anexe.")
        else:
            mov = movimento(vids[0])
            if "erro" in mov:
                falha(f"vídeo ilegível: {mov['erro']}")
            elif mov["delta_medio"] < 1.0:
                falha(f"o vídeo está praticamente parado (delta médio {mov['delta_medio']}). "
                      f"O dossiê fala de movimento que a gravação não mostra.")

    # ── 3. SEÇÕES EXPERIENCIAIS
    secoes = dict(SECOES)
    if a.assinatura_opcional:
        secoes.pop("## VEREDITO HUMANO", None)
    for sec, (sub, ajuda) in secoes.items():
        corpo = corpo_secao(texto, sec)
        if not corpo:
            falha(f"falta a seção obrigatória '{sec}'. {ajuda}"); continue
        if sub.upper() not in corpo.upper():
            falha(f"'{sec}' precisa da subseção '{sub}'. {ajuda}"); continue
        linhas = [l for l in corpo.splitlines() if l.strip() and not l.strip().startswith("#")]
        if linhas and all(PROVA_FRACA.match(l) for l in linhas):
            falha(f"'{sec}' contém só afirmação genérica ('ok', 'funcionou', '200'). "
                  f"{ajuda}")
        elif len("\n".join(linhas).strip()) < 120:
            falha(f"'{sec}' tem conteúdo raso ({len(''.join(linhas))} chars). {ajuda}")

    # ── 4. CONTRASTE: medido dos hex declarados, não da prosa
    pares = re.findall(r"#([0-9a-f]{3,6})\s*(?:sobre|on|/)\s*#([0-9a-f]{3,6})",
                       corpo_secao(texto, "## CORES"), re.I)
    contrastes = []
    if not pares:
        falha("'## CORES' não declara nenhum par '#RRGGBB sobre #RRGGBB'. Sem os valores "
              "reais não há como MEDIR contraste — e 'as cores estão boas' não é medida.")
    for fg, bg in pares:
        r = contraste(hex_rgb(fg), hex_rgb(bg))
        contrastes.append({"texto": f"#{fg}", "fundo": f"#{bg}", "razao": round(r, 2)})
        if r < a.min_contraste:
            falha(f"contraste #{fg} sobre #{bg} = {r:.2f}:1, abaixo do mínimo "
                  f"{a.min_contraste}:1 (WCAG AA). Ilegível para parte dos usuários.")

    # ── 5. BOTÕES: cada um com função E justificativa de existir
    bcorpo = corpo_secao(texto, "## BOTÕES")
    botoes = re.findall(r"^\s*[-*]?\s*(.+?)\s*→\s*(.+?)\s*→\s*(.+?)\s*→\s*(.+)$", bcorpo, re.M)
    if len(botoes) < 1:
        falha("'## BOTÕES' precisa de pelo menos uma linha no formato "
              "'nome → o que faz → funcionou? → faz sentido estar ali?'.")
    for nome, _faz, funcionou, sentido in botoes:
        if not re.search(r"\b(sim|s[ií]|ok|funcionou|testado)\b", funcionou, re.I):
            falha(f"botão '{nome.strip()}': campo 'funcionou?' não afirma teste real "
                  f"('{funcionou.strip()}').")
        if len(sentido.strip()) < 15:
            falha(f"botão '{nome.strip()}': justifique por que ele existe ali "
                  f"('{sentido.strip()}' é raso). Funcionar não é razão para existir.")

    # ── 6. ASSINATURA HUMANA — a parte irredutível
    # NOTA: assinatura em arquivo NÃO prova humano — um agente escreve 'nome: fulano'.
    # Quando o gate usa permissionDecision:"ask", a prova de humano é o runtime
    # perguntando ao usuário, fora do alcance do agente. Aí esta checagem é dispensada.
    vh = "" if a.assinatura_opcional else corpo_secao(texto, "## VEREDITO HUMANO")
    assinado = None if a.assinatura_opcional else re.search(r"###\s*ASSINATURA\s*\n+\s*(?:-\s*)?nome:\s*(\S.{2,})\n+\s*"
                         r"(?:-\s*)?avaliei[- ]pessoalmente:\s*(sim|n[ãa]o)", vh, re.I)
    if a.assinatura_opcional:
        pass
    elif not assinado:
        falha("falta a assinatura humana em '## VEREDITO HUMANO / ### ASSINATURA':\n"
              "        nome: <pessoa que olhou a tela>\n"
              "        avaliei-pessoalmente: sim\n"
              "      Nenhum agente pode preencher isto por uma pessoa. Se você é um agente "
              "e chegou aqui, PARE e peça ao usuário que avalie e assine.")
    elif assinado.group(2).lower().startswith("n"):
        falha("a assinatura diz que ninguém avaliou pessoalmente. Entrega final exige "
              "avaliação humana da experiência.")

    rel = {"aprovado": not FALHAS, "imagens": medidas, "contrastes": contrastes,
           "movimento": mov, "falhas": FALHAS}
    if a.json:
        print(json.dumps(rel, indent=2, ensure_ascii=False))
    else:
        for m in medidas:
            print(f"  imagem {m['arquivo']}: {m['largura']}x{m['altura']}, "
                  f"var={m['variancia']:.4f}, estourado={m['pct_estourado']:.0f}%, "
                  f"sat.extrema={m['pct_saturacao_extrema']:.0f}%")
        for c in contrastes:
            ok = "OK " if c["razao"] >= a.min_contraste else "BAIXO"
            print(f"  contraste {c['texto']} sobre {c['fundo']}: {c['razao']}:1  [{ok}]")
        if mov: print(f"  movimento: {mov}")
        if FALHAS:
            print("\nENTREGA BLOQUEADA:", file=sys.stderr)
            for f in FALHAS: print(f"  ✗ {f}", file=sys.stderr)
        else:
            print("\n  ✅ dossiê de UX válido e assinado por humano.")
    sys.exit(1 if FALHAS else 0)


if __name__ == "__main__":
    main()
