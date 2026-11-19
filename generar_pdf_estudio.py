# -*- coding: utf-8 -*-
"""
generar_pdf_estudio.py
======================
Pipeline editorial que produce `Guia_Estudio_Audiovisual_Walking_Bowmasters.pdf`
a partir de GUIA_ARQUITECTURA_Y_EXPOSICION.md y de los 34 archivos .java reales.

Stack:
  * HTML5 + CSS Paged Media  -> PDF con Chromium headless (Playwright + Microsoft Edge)
  * matplotlib + numpy       -> 4 graficos vectoriales SVG (balistica, IA, composicion, audio)
  * Mermaid (en el navegador)-> diagramas UML / paquetes / estados en SVG nativo
  * Pillow                   -> storyboards (parallax, hitboxes, mapa de UI) a 2x
  * qrcode + pypdf           -> codigos QR, hipervinculos, post-proceso y validacion
  * wave                     -> .wav sintetizados con los MISMOS algoritmos de GestorSonido.java

Uso:
    python generar_pdf_estudio.py
Requisitos:
    pip install matplotlib numpy pillow qrcode playwright pypdf pypdfium2
    (usa el Microsoft Edge instalado; alternativa: `playwright install chromium`)
"""
from __future__ import annotations

import html
import math
import re
import struct
import sys
import urllib.request
import wave
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import qrcode
import qrcode.image.svg

# ---------------------------------------------------------------------------
# Rutas y constantes del proyecto
# ---------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent
GUIA_MD = RAIZ / "GUIA_ARQUITECTURA_Y_EXPOSICION.md"
SALIDA_PDF = RAIZ / "Guia_Estudio_Audiovisual_Walking_Bowmasters.pdf"
REC = RAIZ / "estudio_audiovisual"
D_GRAF, D_AUDIO, D_DIAG, D_SB, D_QR, D_VENDOR = (REC / n for n in
                                                  ("graficos", "audio", "diagramas", "storyboards", "qr", "vendor"))

REPO_GIT = "https://github.com/JOHN-RAVEN-CROWNSON-2008/ProyectoLogicaDeProgramacion-II.git"
REPO_WEB = REPO_GIT[:-4]
RAMA = "main"
MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"

# Constantes reales (util/ConstantesJuego.java, armas/*.java, modos/ModoDueloBatallones.java)
ANCHO_VIRTUAL, ALTO_VIRTUAL, Y_SUELO, GRAVEDAD_BASE = 1280, 720, 582, 540.0
ANCHO_MUNDO_DUELO = 1860
V_MIN = 175.0  # Arma.calcularVelocidadInicial
ARMAS = {  # nombre: (velocidadBase, velocidadExtra, factorGravedad, clase)
    "RifleAsalto": (460.0, 640.0, 0.45),
    "LanzaGranadas": (300.0, 690.0, 1.00),
    "Revolver": (410.0, 620.0, 0.55),
    "EspadaKatana": (310.0, 570.0, 0.90),
}
# Paleta categorica validada (dataviz reference palette, modo claro)
C_AZUL, C_NARANJA, C_AQUA, C_AMARILLO, C_MAGENTA, C_VERDE, C_VIOLETA, C_ROJO = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
COLOR_ARMA = {"RifleAsalto": C_AZUL, "LanzaGranadas": C_NARANJA, "Revolver": C_AQUA, "EspadaKatana": C_AMARILLO}
TXT1, TXT2, TXT3, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"


def log(msg: str) -> None:
    print(f"  · {msg}", flush=True)


def v0(arma: str, potencia: float) -> float:
    vb, ve, _ = ARMAS[arma]
    p = min(1.0, max(0.05, potencia))
    return V_MIN + p * ((vb + ve) - V_MIN)


# ---------------------------------------------------------------------------
# 0. Analisis del codigo fuente real
# ---------------------------------------------------------------------------
PAQUETES_PROPIOS = ("armas", "audio", "efectos", "entidades", "escenario",
                    "interfaces", "inventario", "modos", "util")


def analizar_codigo():
    archivos = sorted(RAIZ.glob("**/*.java"))
    archivos = [a for a in archivos if "estudio_audiovisual" not in a.parts]
    info = []
    deps = defaultdict(set)
    for a in archivos:
        rel = a.relative_to(RAIZ).as_posix()
        pk = a.parent.name if a.parent != RAIZ else "(raiz)"
        texto = a.read_text(encoding="utf-8", errors="replace")
        lineas = texto.count("\n") + 1
        m = re.search(r"\b(public\s+)?(abstract\s+|final\s+)*(class|interface|enum)\s+(\w+)", texto)
        tipo = (("abstract " if m and m.group(2) and "abstract" in m.group(2) else "") + m.group(3)) if m else "?"
        info.append({"rel": rel, "paquete": pk, "lineas": lineas, "tipo": tipo})
        for imp in re.findall(r"^import\s+(\w+)\.", texto, re.M):
            if imp in PAQUETES_PROPIOS and imp != pk:
                deps[pk].add(imp)
    # deteccion de ciclos (componentes fuertemente conexas, Tarjan)
    nodos = sorted(set(deps) | {d for v in deps.values() for d in v})
    idx, low, pila, enpila, comps, c = {}, {}, [], set(), [], [0]

    def strong(v):
        idx[v] = low[v] = c[0]; c[0] += 1; pila.append(v); enpila.add(v)
        for w in deps.get(v, ()):
            if w not in idx:
                strong(w); low[v] = min(low[v], low[w])
            elif w in enpila:
                low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp = []
            while True:
                w = pila.pop(); enpila.discard(w); comp.append(w)
                if w == v:
                    break
            comps.append(comp)
    for n in nodos:
        if n not in idx:
            strong(n)
    ciclos = [sorted(cmp) for cmp in comps if len(cmp) > 1]
    return info, deps, ciclos


def extraer(rel: str, patron: str, max_lineas: int | None = None, incluir_anotacion=True):
    """Extrae un bloque REAL de codigo (metodo/clase) por llaves balanceadas."""
    lineas = (RAIZ / rel).read_text(encoding="utf-8").split("\n")
    rx = re.compile(patron)
    for i, ln in enumerate(lineas):
        if rx.search(ln):
            ini = i
            if incluir_anotacion and i > 0 and lineas[i - 1].strip().startswith("@"):
                ini = i - 1
            if ln.rstrip().endswith(";"):
                fin = i
            else:
                prof, fin, abierto = 0, i, False
                for j in range(i, len(lineas)):
                    prof += lineas[j].count("{") - lineas[j].count("}")
                    if "{" in lineas[j]:
                        abierto = True
                    if abierto and prof <= 0:
                        fin = j
                        break
            bloque = lineas[ini:fin + 1]
            if max_lineas and len(bloque) > max_lineas:
                bloque = bloque[:max_lineas] + ["        // ... (continua en el archivo)"]
                fin = ini + max_lineas - 1
            sangria = min((len(l) - len(l.lstrip()) for l in bloque if l.strip()), default=0)
            codigo = "\n".join(l[sangria:] for l in bloque)
            return {"rel": rel, "l1": ini + 1, "l2": fin + 1, "codigo": codigo}
    raise ValueError(f"Patron no encontrado en {rel}: {patron}")


# ---------------------------------------------------------------------------
# 1. Audio: port exacto de GestorSonido.java (incluye java.util.Random)
# ---------------------------------------------------------------------------
class JavaRandom:
    MULT, ADD, MASK = 0x5DEECE66D, 0xB, (1 << 48) - 1

    def __init__(self, seed: int):
        self.seed = (seed ^ self.MULT) & self.MASK

    def _next(self, bits: int) -> int:
        self.seed = (self.seed * self.MULT + self.ADD) & self.MASK
        return self.seed >> (48 - bits)

    def next_double(self) -> float:
        return ((self._next(26) << 27) + self._next(27)) * (1.0 / (1 << 53))


SAMPLE_RATE = 44100.0


def _a_short(val: float) -> int:
    return int(max(-32767.0, min(32767.0, val)))  # (short) trunca hacia cero


def sintetizar_barrido(f_ini, f_fin, dur, vol, metalico, seed):
    n = max(1, int(SAMPLE_RATE * dur))
    rng = JavaRandom(seed)
    fase = fase2 = 0.0
    out, env_arr = [], []
    for i in range(n):
        t = i / n
        freq = f_ini + (f_fin - f_ini) * t
        env = math.sin(math.pi * min(1.0, t * 8.0)) * (1.0 - t)
        fase += 2.0 * math.pi * freq / SAMPLE_RATE
        val = math.sin(fase)
        if metalico:
            fase2 += 2.0 * math.pi * (freq * 2.41) / SAMPLE_RATE
            val = 0.55 * val + 0.30 * math.sin(fase2) + 0.15 * (rng.next_double() * 2.0 - 1.0)
        out.append(_a_short(val * env * vol * 32767.0))
        env_arr.append(env * vol)
    return out, env_arr


def sintetizar_disparo(dur, f_ini, f_fin, vol, peso_ruido, seed):
    n = max(1, int(SAMPLE_RATE * dur))
    rng = JavaRandom(seed)
    fase = filtro = 0.0
    out, env_arr = [], []
    for i in range(n):
        t = i / n
        env = (1.0 - t) ** 1.9
        freq = f_ini * (max(0.05, f_fin / f_ini) ** t)
        fase += 2.0 * math.pi * freq / SAMPLE_RATE
        tono = math.sin(fase)
        ruido = rng.next_double() * 2.0 - 1.0
        filtro = filtro * 0.45 + ruido * 0.55
        mezcla = tono * (1.0 - peso_ruido) + filtro * peso_ruido
        out.append(_a_short(mezcla * env * vol * 32767.0))
        env_arr.append(env * vol)
    return out, env_arr


def sintetizar_arpegio(notas, dur_nota, vol):
    m = max(1, int(SAMPLE_RATE * dur_nota))
    out, env_arr = [], []
    for freq in notas:
        for i in range(m):
            t = i / m
            env = math.sin(math.pi * min(1.0, t * 5.0)) * (1.0 - t * 0.75)
            val = math.sin(2.0 * math.pi * freq * (i / SAMPLE_RATE))
            out.append(_a_short(val * env * vol * 32767.0))
            env_arr.append(env * vol)
    return out, env_arr


EFECTOS = [  # clave, metodo publico, sintetizador, parametros (identicos a inicializarEfectos)
    ("hover", "reproducirHoverMenu()", "sintetizarBarrido", (680, 920, 0.040, 0.14, False, 100)),
    ("click", "reproducirClickMenu()", "sintetizarBarrido", (520, 1080, 0.065, 0.22, False, 101)),
    ("disparo_rifle", "reproducirDisparoRifle()", "sintetizarDisparo", (0.11, 220, 75, 0.34, 0.65, 102)),
    ("disparo_revolver", "reproducirDisparoRevolver()", "sintetizarDisparo", (0.18, 175, 52, 0.42, 0.58, 103)),
    ("lanzagranadas", "reproducirLanzagranadas()", "sintetizarDisparo", (0.17, 130, 48, 0.40, 0.22, 104)),
    ("explosion", "reproducirExplosion()", "sintetizarDisparo", (0.46, 95, 28, 0.55, 0.80, 105)),
    ("katana", "reproducirCorteKatana()", "sintetizarBarrido", (1350, 2900, 0.15, 0.28, True, 106)),
    ("impacto", "reproducirImpacto()", "sintetizarDisparo", (0.085, 190, 68, 0.26, 0.45, 107)),
    ("suministro", "reproducirSuministro()", "sintetizarArpegio", ((523.25, 659.25, 783.99), 0.065, 0.24)),
    ("victoria", "reproducirVictoria()", "sintetizarArpegio", ((523.25, 659.25, 783.99, 1046.50), 0.11, 0.28)),
    ("derrota", "reproducirDerrota()", "sintetizarArpegio", ((392.00, 329.63, 261.63, 196.00), 0.13, 0.28)),
]
SINTE = {"sintetizarBarrido": sintetizar_barrido, "sintetizarDisparo": sintetizar_disparo,
         "sintetizarArpegio": sintetizar_arpegio}


def generar_audio():
    señales = {}
    for clave, _, fn, params in EFECTOS:
        muestras, env = SINTE[fn](*params)
        ruta = D_AUDIO / f"{clave}.wav"
        with wave.open(str(ruta), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(SAMPLE_RATE))
            w.writeframes(struct.pack(f"<{len(muestras)}h", *muestras))
        señales[clave] = (np.array(muestras, dtype=np.int16), np.array(env))
        # demo: tres repeticiones con 0.6 s de silencio para escuchar mejor
    demo = []
    for clave, *_ in EFECTOS:
        demo += list(señales[clave][0]) + [0] * int(SAMPLE_RATE * 0.6)
    with wave.open(str(D_AUDIO / "00_todos_los_efectos_en_orden.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(SAMPLE_RATE))
        w.writeframes(struct.pack(f"<{len(demo)}h", *demo))
    log(f"{len(EFECTOS)} efectos .wav + pista demo -> {D_AUDIO.relative_to(RAIZ)}")
    return señales


# ---------------------------------------------------------------------------
# 2. Graficos matplotlib (SVG vectorial)
# ---------------------------------------------------------------------------
def estilo_mpl():
    plt.rcParams.update({
        "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9.5,
        "axes.edgecolor": TXT3, "axes.labelcolor": TXT2, "axes.titleweight": "bold",
        "axes.titlesize": 11, "axes.titlecolor": TXT1, "axes.titlelocation": "left",
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": TXT2, "ytick.color": TXT2, "legend.frameon": False,
        "svg.fonttype": "none", "figure.dpi": 110, "lines.linewidth": 2.0,
        "lines.solid_capstyle": "round",
    })


def trayectoria(arma, potencia, ang_deg, viento=0.0, x0=242.0, h0=56.0, dt=1 / 60, pasos=900,
                obstaculos=False):
    """Integracion identica a Proyectil.actualizarConViento (coordenadas: altura sobre Y_SUELO)."""
    a = math.radians(ang_deg)
    vel = v0(arma, potencia)
    vx, vy = vel * math.cos(a), -vel * math.sin(a)
    g = GRAVEDAD_BASE * ARMAS[arma][2]
    x, y = x0, Y_SUELO - h0
    xs, ys = [x], [Y_SUELO - y]
    for _ in range(pasos):
        vx += viento * dt
        vy += g * dt
        x += vx * dt
        y += vy * dt
        if obstaculos and any(ox <= x <= ox + w and Y_SUELO - h <= y <= Y_SUELO for ox, w, h in OBSTACULOS):
            xs.append(x); ys.append(Y_SUELO - y); break
        if y >= Y_SUELO:
            # interpolar el punto de contacto con el suelo
            xs.append(x); ys.append(0.0); break
        xs.append(x); ys.append(Y_SUELO - y)
    return np.array(xs), np.array(ys)


OBSTACULOS = [(780, 185, 118), (1175, 130, 74)]  # AUTOBUS y COCHE (x, ancho, alto)


def grafico_balistica():
    fig, axs = plt.subplots(3, 1, figsize=(7.4, 10.2), gridspec_kw={"height_ratios": [1.05, 0.8, 1.15]})
    # A) 100% a 45 grados
    ax = axs[0]
    for arma in ARMAS:
        xs, ys = trayectoria(arma, 1.0, 45, pasos=2400)
        ax.plot(xs, ys, color=COLOR_ARMA[arma],
                label=f"{arma} · factor {ARMAS[arma][2]:.2f} · cae a {xs[-1] - 242:,.0f} px".replace(",", "."))
        ax.plot([xs[-1]], [0], "o", color=COLOR_ARMA[arma], ms=7, mec="white", mew=1.5, clip_on=False)
    ax.axvspan(0, ANCHO_MUNDO_DUELO, color="#f1efe8", zorder=0)
    ax.text(ANCHO_MUNDO_DUELO / 2, ax.get_ylim()[1] * 0.92 if ax.get_ylim()[1] else 900,
            "ANCHO_MUNDO_DUELO = 1860 px", ha="center", fontsize=8, color=TXT3)
    ax.set_title("A · Tecla X al 100 % (potencia 1.00) · 45° · sin viento")
    ax.set_ylabel("altura sobre Y_SUELO (px)"); ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", fontsize=8)
    # B) 5% a 45 grados
    ax = axs[1]
    for arma in ARMAS:
        xs, ys = trayectoria(arma, 0.05, 45)
        ax.plot(xs, ys, color=COLOR_ARMA[arma], label=f"{arma} · {xs[-1] - 242:.0f} px")
        ax.plot([xs[-1]], [0], "o", color=COLOR_ARMA[arma], ms=7, mec="white", mew=1.5, clip_on=False)
    ax.set_title("B · Tecla X al 5 % (potencia 0.05) · 45° · el tiro corto 'de lob'")
    ax.set_ylabel("altura (px)"); ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", fontsize=8, ncols=2, title="alcance horizontal", title_fontsize=8)
    # C) viento en el mundo de duelo
    ax = axs[2]
    for (ox, w, h), nom in zip(OBSTACULOS, ("AUTOBUS", "COCHE")):
        ax.add_patch(plt.Rectangle((ox, 0), w, h, color="#c9c6bc", zorder=1))
        ax.text(ox + w / 2, h + 10, nom, ha="center", fontsize=7.5, color=TXT2)
    for bx, nom in ((210, "batallonJugador\nx = 210"), (1620, "batallonEnemigo\nx = 1620")):
        ax.add_patch(plt.Rectangle((bx - 78, 0), 156, 95, fill=False, ec=TXT2, ls="--", lw=1))
        ax.text(bx, 112, nom, ha="center", fontsize=7.5, color=TXT2,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    estilos = {-125: (C_VIOLETA, "viento −125 px/s² (en contra)"), 0: (TXT3, "sin viento"),
               125: (C_ROJO, "viento +125 px/s² (a favor)")}
    for viento, (col, lab) in estilos.items():
        xs, ys = trayectoria("LanzaGranadas", 1.0, 45, viento=viento, pasos=2400)
        ax.plot(xs, ys, color=col, label=lab, ls="-" if viento else (0, (4, 3)))
        ax.plot([xs[-1]], [ys[-1]], "o", color=col, ms=7, mec="white", mew=1.5)
    ax.set_xlim(0, ANCHO_MUNDO_DUELO + 400); ax.set_ylim(0, 640)
    ax.set_title("C · LanzaGranadas al 100 % en ModoDueloBatallones · efecto del viento ±125")
    ax.set_xlabel("x en el mundo (px)"); ax.set_ylabel("altura (px)")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout(h_pad=1.6)
    ruta = D_GRAF / "g1_balistica.svg"
    fig.savefig(ruta); fig.savefig(D_GRAF / "g1_balistica.png", dpi=300); plt.close(fig)
    log("Grafico 1 (balistica) listo")


def _simular_vector(x0, y0, ang, pot, vbase, factor, viento, dt, pasos, objetivo=None, granada=None):
    """Simulacion vectorizada (numpy) de muchos proyectiles; devuelve x de impacto y si golpeo."""
    vmax = vbase
    vel = V_MIN + np.clip(pot, 0.05, 1.0) * (vmax - V_MIN)
    vx, vy = vel * np.cos(ang), -vel * np.sin(ang)
    g = GRAVEDAD_BASE * factor
    x = np.full_like(vel, x0, dtype=float); y = np.full_like(vel, y0, dtype=float)
    vivo = np.ones_like(vel, dtype=bool)
    impacto_x = np.full_like(vel, np.nan); golpe = np.zeros_like(vel, dtype=bool)
    for _ in range(pasos):
        vx = vx + viento * dt; vy = vy + g * dt
        x = np.where(vivo, x + vx * dt, x); y = np.where(vivo, y + vy * dt, y)
        if objetivo is not None:
            tx = objetivo
            dentro = vivo & (np.abs(x - tx) <= 78) & (y >= Y_SUELO - 95) & (y <= Y_SUELO)
            golpe |= dentro; impacto_x = np.where(dentro, x, impacto_x); vivo &= ~dentro
        choca = np.zeros_like(vivo)
        for ox, w, h in OBSTACULOS:
            choca |= (x >= ox) & (x <= ox + w) & (y >= Y_SUELO - h) & (y <= Y_SUELO)
        choca |= y >= Y_SUELO
        nuevo = vivo & choca
        impacto_x = np.where(nuevo, x, impacto_x)
        if objetivo is not None and granada is not None:
            aoe = nuevo & granada & (np.hypot(objetivo - x, (Y_SUELO - 45) - y) <= 145 + 45)
            golpe |= aoe
        vivo &= ~choca
        if not vivo.any():
            break
    impacto_x = np.where(np.isnan(impacto_x), x, impacto_x)
    return impacto_x, golpe


def grafico_ia(turnos=8, n=3000, semilla=7):
    turno = np.arange(1, turnos + 1)
    err = np.maximum(0.015, 0.14 - (turno - 1) * 0.025)
    rng = np.random.default_rng(semilla)
    armas_ia = ["RifleAsalto", "LanzaGranadas", "Revolver"]  # Inventario.getArma(0..2)
    x0, y0 = 1620 - 32, Y_SUELO - 56
    angs = np.radians(np.arange(122, 153, 3))
    pots = np.array([0.45 + 0.04 * k for k in range(14)])
    A, P = np.meshgrid(angs, pots, indexing="ij"); A, P = A.ravel(), P.ravel()
    vientos = np.linspace(-125, 125, 51)
    mejor = {}
    for wi, arma in enumerate(armas_ia):
        vb, ve, fac = ARMAS[arma]
        for vi, vt in enumerate(vientos):
            ix, _ = _simular_vector(x0, y0, A, P, vb + ve, fac, vt, 0.02, 220)
            k = int(np.argmin(np.abs(ix - 210)))
            mejor[(wi, vi)] = (A[k], P[k])
    prob, mediana = [], []
    for t, e in zip(turno, err):
        wsel = rng.integers(0, 3, n); vsel = rng.integers(0, len(vientos), n)
        base = np.array([mejor[(w, v)] for w, v in zip(wsel, vsel)])
        ang = base[:, 0] + rng.uniform(-1, 1, n) * e * 0.7
        pot = np.clip(base[:, 1] + rng.uniform(-1, 1, n) * e, 0.25, 1.0)
        hits = np.zeros(n, bool); miss = np.zeros(n)
        for wi, arma in enumerate(armas_ia):
            m = wsel == wi
            vb, ve, fac = ARMAS[arma]
            ix, gol = _simular_vector(x0, y0, ang[m], pot[m], vb + ve, fac, vientos[vsel[m]], 1 / 60, 600,
                                      objetivo=210, granada=np.full(m.sum(), arma == "LanzaGranadas"))
            hits[m] = gol; miss[m] = np.abs(ix - 210)
        prob.append(hits.mean() * 100); mediana.append(np.median(miss))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.6, 3.5))
    a1.step(turno, err, where="mid", color=C_AZUL)
    a1.plot(turno, err, "o", color=C_AZUL, ms=7, mec="white", mew=1.5)
    a1.axhline(0.015, color=TXT3, ls=(0, (3, 3)), lw=1)
    a1.text(turnos, 0.019, "piso 0.015", ha="right", fontsize=8, color=TXT2)
    for t, e in zip(turno[:6], err[:6]):
        a1.annotate(f"{e:.3f}", (t, e), xytext=(6, 4), textcoords="offset points", fontsize=7.5, color=TXT2)
    a1.set_title("errorMaximo por turnoIA")
    a1.set_xlabel("turnoIA"); a1.set_ylabel("errorMaximo (rad / potencia)")
    a1.set_xticks(turno); a1.set_ylim(0, 0.16)
    a2.bar(turno, prob, color=C_NARANJA, width=0.62)
    for t, p in zip(turno, prob):
        a2.text(t, p + 1.5, f"{p:.0f}%", ha="center", fontsize=7.5, color=TXT2)
    a2.set_title("Prob. de impacto (Monte Carlo)")
    a2.set_xlabel("turnoIA"); a2.set_ylabel(f"% de {n} disparos simulados"); a2.set_xticks(turno)
    a2.set_ylim(0, max(prob) * 1.18 + 5)
    fig.tight_layout(w_pad=2.5)
    fig.savefig(D_GRAF / "g2_ia.svg"); fig.savefig(D_GRAF / "g2_ia.png", dpi=300); plt.close(fig)
    log("Grafico 2 (IA) listo: prob. impacto " + ", ".join(f"T{t}={p:.0f}%" for t, p in zip(turno, prob)))
    return list(zip(turno.tolist(), err.tolist(), prob, mediana))


def grafico_composicion():
    vida_max, total = 320, 4
    hp = np.arange(vida_max, -1, -1)
    vivos = np.array([0 if v <= 0 else math.ceil(v / vida_max * total) for v in hp])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.4, 4.6), gridspec_kw={"height_ratios": [1.2, 1]}, sharex=True)
    a1.step(hp, vivos, where="post", color=C_AZUL)
    for pct in (0.75, 0.5, 0.25, 0.0):
        x = vida_max * pct
        a1.axvline(x, color=TXT3, ls=(0, (3, 3)), lw=1)
        a1.text(x, 4.25, f"{int(pct * 100)}% · {int(x)} HP", ha="center", fontsize=8, color=TXT2)
    a1.set_ylim(-0.2, 4.6); a1.set_yticks(range(5)); a1.set_ylabel("getMiembrosVivos()")
    a1.set_title("Batallon (vidaGlobal = 320): vivosObjetivo = ceil(vida / vidaMaxima × 4)")
    a1.invert_xaxis()
    nombres = ["miembros[0] · sombrero", "miembros[1] · casco", "miembros[2]", "miembros[3] · casco"]
    umbral = [0, 80, 160, 240]  # vivo mientras vida > umbral (batallonJugador: cae primero el indice 3)
    cols = [C_AZUL, C_AQUA, C_AMARILLO, C_NARANJA]
    for i, (nom, u) in enumerate(zip(nombres, umbral)):
        a2.barh(i, vida_max - u, left=u, color=cols[i], height=0.55)
        a2.text(vida_max - 4, i, nom, va="center", ha="left", fontsize=8, color="white", fontweight="bold")
        a2.text(u - 3, i, f"cae con vida ≤ {u}" if u else "cae con vida = 0", va="center", ha="left",
                fontsize=7.5, color=TXT2)
    a2.set_yticks([]); a2.set_xlabel("vida del Batallon (HP) → el daño avanza hacia la derecha")
    a2.set_title("Ciclo de vida de cada MiembroEscuadron (batallonJugador, esJugador = true)")
    a2.grid(axis="y", visible=False)
    fig.tight_layout(h_pad=1.2)
    fig.savefig(D_GRAF / "g3_composicion.svg"); fig.savefig(D_GRAF / "g3_composicion.png", dpi=300); plt.close(fig)
    log("Grafico 3 (composicion) listo")


def grafico_audio(señales):
    sel = [("hover", C_AZUL), ("disparo_rifle", C_NARANJA), ("explosion", C_ROJO), ("katana", C_VIOLETA)]
    params = {c: (fn, p) for c, _, fn, p in EFECTOS}
    fig, axs = plt.subplots(2, 2, figsize=(7.6, 5.0))
    for ax, (clave, col) in zip(axs.ravel(), sel):
        s, env = señales[clave]
        s = s.astype(float) / 32767.0
        n = len(s); t = np.arange(n) / SAMPLE_RATE * 1000
        bins = max(1, n // 700)
        m = n // bins * bins
        mn, mx = s[:m].reshape(-1, bins).min(1), s[:m].reshape(-1, bins).max(1)
        tb = t[:m].reshape(-1, bins).mean(1)
        ax.fill_between(tb, mn, mx, color=col, alpha=0.55, lw=0)
        ax.plot(t, env, color=TXT1, lw=1.2, label="envolvente × volumen")
        ax.plot(t, -np.array(env), color=TXT1, lw=1.2)
        fn, p = params[clave]
        ax.set_title(f'"{clave}" · {fn}', fontsize=9.5)
        ax.text(0.98, 0.04, f"{n} muestras · {n / SAMPLE_RATE * 1000:.0f} ms", transform=ax.transAxes,
                ha="right", fontsize=7.5, color=TXT2)
        lim = max(abs(mn).max(), mx.max()) * 1.15
        ax.set_ylim(-lim, lim); ax.set_xlabel("ms"); ax.set_ylabel("amplitud")
    axs[0, 0].legend(loc="upper right", fontsize=7.5)
    fig.tight_layout(h_pad=1.2, w_pad=1.5)
    fig.savefig(D_GRAF / "g4_audio_pcm.svg"); fig.savefig(D_GRAF / "g4_audio_pcm.png", dpi=300); plt.close(fig)
    log("Grafico 4 (audio PCM) listo")


# ---------------------------------------------------------------------------
# 3. Storyboards Pillow (recreaciones Graphics2D a 2x)
# ---------------------------------------------------------------------------
FONT_DIR = Path("C:/Windows/Fonts")


def fuente(tam, negrita=False, mono=False):
    nombres = (["consolab.ttf", "consola.ttf"] if mono else
               (["segoeuib.ttf", "arialbd.ttf"] if negrita else ["segoeui.ttf", "arial.ttf"]))
    for nm in nombres:
        p = FONT_DIR / nm
        if p.exists():
            return ImageFont.truetype(str(p), tam)
    return ImageFont.load_default()


class Lienzo:
    """Dibuja en coordenadas virtuales y multiplica por K (supermuestreo 2x)."""

    def __init__(self, ancho, alto, k=2, fondo="#f7f6f2"):
        self.k = k
        self.img = Image.new("RGB", (int(ancho * k), int(alto * k)), fondo)
        self.d = ImageDraw.Draw(self.img, "RGBA")

    def _p(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def rect(self, x, y, w, h, fill=None, outline=None, width=1, r=0, dash=False):
        box = [x * self.k, y * self.k, (x + w) * self.k, (y + h) * self.k]
        if dash:
            self.linea_disc([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], outline, width)
            if fill:
                self.d.rectangle(box, fill=fill)
            return
        if r:
            self.d.rounded_rectangle(box, r * self.k, fill=fill, outline=outline, width=int(width * self.k))
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=int(width * self.k))

    def elipse(self, cx, cy, rx, ry, fill=None, outline=None, width=1):
        self.d.ellipse([(cx - rx) * self.k, (cy - ry) * self.k, (cx + rx) * self.k, (cy + ry) * self.k],
                       fill=fill, outline=outline, width=int(width * self.k))

    def poli(self, pts, fill=None, outline=None):
        self.d.polygon(self._p(pts), fill=fill, outline=outline)

    def linea(self, pts, color, width=1):
        self.d.line(self._p(pts), fill=color, width=int(width * self.k), joint="curve")

    def linea_disc(self, pts, color, width=1, seg=8):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            L = math.hypot(x2 - x1, y2 - y1)
            n = max(1, int(L / seg))
            for i in range(0, n, 2):
                a, b = i / n, min(1, (i + 1) / n)
                self.linea([(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a), (x1 + (x2 - x1) * b, y1 + (y2 - y1) * b)],
                           color, width)

    def flecha(self, x1, y1, x2, y2, color, width=2, cabeza=10):
        self.linea([(x1, y1), (x2, y2)], color, width)
        ang = math.atan2(y2 - y1, x2 - x1)
        p1 = (x2 - cabeza * math.cos(ang - 0.4), y2 - cabeza * math.sin(ang - 0.4))
        p2 = (x2 - cabeza * math.cos(ang + 0.4), y2 - cabeza * math.sin(ang + 0.4))
        self.poli([(x2, y2), p1, p2], fill=color)

    def texto(self, x, y, s, tam=16, color="#111", negrita=False, mono=False, anchor="la"):
        self.d.text((x * self.k, y * self.k), s, font=fuente(int(tam * self.k), negrita, mono), fill=color,
                    anchor=anchor)

    def badge(self, x, y, n, color="#e34948"):
        self.elipse(x, y, 13, 13, fill=color)
        self.texto(x, y + 1, str(n), 15, "white", True, anchor="mm")

    def guardar(self, ruta):
        self.img.save(ruta, optimize=True)


def _escena(L: Lienzo, ox, oy, cam, shake=(0, 0)):
    """Recreacion simplificada de EscenarioApocaliptico.dibujarFondo con capas parallax."""
    # cielo degradado
    for i in range(0, 582, 6):
        t = i / 582
        c = (int(52 + 150 * t), int(38 + 80 * t), int(60 + 30 * t))
        L.rect(ox, oy + i, 1280, 6, fill=c)
    # sol (0.05)
    sx = 880 - cam * 0.05
    L.elipse(ox + sx, oy + 150, 58, 58, fill=(255, 196, 120))
    # edificios lejanos (0.18)
    off = -(cam * 0.18)
    for i in range(12):
        bx = off + i * 150 - 40
        h = 170 + (i * 53) % 120
        if -160 < bx < 1290:
            L.rect(ox + max(0, bx), oy + 582 - 70 - h, min(110, 1280 - max(0, bx)) if bx < 1280 else 0, h,
                   fill=(58, 52, 66))
            for wy in range(int(582 - 70 - h + 16), 582 - 90, 28):
                for wx in range(int(bx + 14), int(bx + 100), 26):
                    if 0 <= wx < 1270 and (wx + wy) % 3:
                        L.rect(ox + wx, oy + wy, 10, 12, fill=(92, 80, 70))
    # arboles / vallas (0.45)
    off = -(cam * 0.45)
    for i in range(16):
        tx = off + i * 120 + 30
        if 0 < tx < 1270:
            L.rect(ox + tx - 4, oy + 582 - 120, 8, 120, fill=(46, 40, 34))
            L.elipse(ox + tx, oy + 582 - 128, 34, 30, fill=(48, 66, 44))
    for i in range(40):
        vx = off + i * 46
        if 0 < vx < 1276:
            L.rect(ox + vx, oy + 582 - 46, 5, 46, fill=(98, 86, 70))
    L.rect(ox, oy + 582 - 34, 1280, 5, fill=(98, 86, 70))
    # suelo
    L.rect(ox, oy + 582, 1280, 138, fill=(64, 60, 56))
    L.rect(ox, oy + 582, 1280, 6, fill=(110, 100, 86))
    # mundo (1.0) con camara y shake
    sx_, sy_ = shake
    for (wx, w, h), col in zip(OBSTACULOS, ((176, 120, 52), (120, 120, 132))):
        x = wx - cam + sx_
        if x < 1280 and x + w > 0:
            L.rect(ox + max(0, x), oy + 582 - h + sy_, min(w, 1280 - x) - max(0, -x), h, fill=col, r=6)
    for bx, col in ((210, (70, 120, 200)), (1620, (190, 70, 60))):
        for k_ in range(4):
            x = bx - 52 + k_ * 34 - cam + sx_
            if 6 < x < 1274:
                L.rect(ox + x - 9, oy + 582 - 60 + sy_, 18, 46, fill=col, r=4)
                L.elipse(ox + x, oy + 582 - 70 + sy_, 10, 10, fill=(225, 190, 160))


def storyboard_parallax():
    L = Lienzo(1900, 1720, k=2)
    L.texto(60, 30, "Storyboard 1 · Capas Parallax + cámara camaraX + Screen Shake", 30, "#111", True)
    L.texto(60, 72, "Recreación esquemática de EscenarioApocaliptico.dibujarFondo(g, camaraX, ANCHO_MUNDO_DUELO)",
            17, "#555")
    frames = [(110, 0, (0, 0), "camaraX = 0  (TURNO_JUGADOR: cámara sobre batallonJugador)"),
              (930, 580, (12, -8), "camaraX = 580  (máx. = 1860 − 1280) · PROYECTIL_EN_VUELO + shake")]
    for oy, cam, sh, lab in frames:
        _escena(L, 60, oy, cam, sh)
        L.rect(60, oy, 1280, 720, outline="#111", width=3)
        L.rect(60, oy - 34, 760, 30, fill="#111", r=6)
        L.texto(72, oy - 30, lab, 17, "white", True)
    # shake marco
    L.rect(60 + 12, 930 - 8, 1280, 720, outline="#e34948", width=3, dash=True)
    # columna de anotaciones
    capas = [("Sol", "camaraX × 0.05", 0.05, (255, 196, 120)), ("Edificios en ruinas", "camaraX × 0.18", 0.18, (58, 52, 66)),
             ("Árboles y vallas", "camaraX × 0.45", 0.45, (48, 66, 44)), ("Mundo (batallones, bus)", "camaraX × 1.00", 1.0,
                                                                            (176, 120, 52))]
    x0 = 1380
    L.texto(x0, 130, "Desplazamiento por capa", 22, "#111", True)
    L.texto(x0, 162, "cuando la cámara avanza 580 px:", 17, "#555")
    for i, (n, f, k_, col) in enumerate(capas):
        y = 215 + i * 118
        L.rect(x0, y, 26, 26, fill=col, r=5)
        L.texto(x0 + 40, y - 2, n, 19, "#111", True)
        L.texto(x0 + 40, y + 26, f, 17, "#2a78d6", mono=True)
        w = 440 * k_
        L.rect(x0 + 40, y + 56, 440, 14, fill="#e4e3df", r=7)
        L.rect(x0 + 40, y + 56, max(14, w), 14, fill="#2a78d6", r=7)
        L.texto(x0 + 40 + 440, y + 26, f"{580 * k_:.0f} px", 17, "#111", True, anchor="ra")
    y = 720
    L.texto(x0, y, "Por qué parece 3D", 22, "#111", True)
    for j, s in enumerate(["Lo lejano se mueve menos que lo", "cercano: el cerebro interpreta", "esa diferencia como profundidad."]):
        L.texto(x0, y + 34 + j * 26, s, 17, "#333")
    y = 900
    L.texto(x0, y, "Cámara con Lerp", 22, "#111", True)
    L.texto(x0, y + 36, "camaraX += (camaraObjetivoX", 16, "#6250d6", mono=True)
    L.texto(x0, y + 60, "          - camaraX)", 16, "#6250d6", mono=True)
    L.texto(x0, y + 84, "        * min(1.0, dt * 6.5);", 16, "#6250d6", mono=True)
    L.texto(x0, y + 120, "Recorre ~10 % de la distancia", 17, "#333")
    L.texto(x0, y + 146, "restante por fotograma (dt≈0.016).", 17, "#333")
    y = 1130
    L.texto(x0, y, "Screen Shake (marco rojo)", 22, "#e34948", True)
    for j, s in enumerate(["g2.translate(sx, sy) aleatorio", "± intensidadShake (16 px tras", "explosión) que decae 38 px/s.",
                           "El HUD se dibuja después, sin", "traslación: siempre queda fijo."]):
        L.texto(x0, y + 36 + j * 26, s, 17, "#333")
    L.guardar(D_SB / "sb1_parallax.png")
    log("Storyboard 1 (parallax) listo")


def _zombie(L, cx, base, Z):
    """Zombie esquematico de 88 px de alto escalado por Z."""
    gris, ropa = (122, 150, 110), (82, 76, 96)
    L.rect(cx - 9 * Z, base - 40 * Z, 7 * Z, 40 * Z, fill=(60, 55, 70))
    L.rect(cx + 2 * Z, base - 40 * Z, 7 * Z, 40 * Z, fill=(60, 55, 70))
    L.rect(cx - 13 * Z, base - 70 * Z, 26 * Z, 32 * Z, fill=ropa, r=4 * Z)
    L.linea([(cx + 10 * Z, base - 64 * Z), (cx + 30 * Z, base - 58 * Z)], gris, 6 * Z)
    L.linea([(cx - 10 * Z, base - 64 * Z), (cx + 22 * Z, base - 52 * Z)], gris, 6 * Z)
    L.elipse(cx + 1 * Z, base - 78 * Z, 10 * Z, 10 * Z, fill=gris)
    L.elipse(cx + 5 * Z, base - 80 * Z, 2 * Z, 2 * Z, fill=(255, 60, 40))


def storyboard_hitboxes():
    L = Lienzo(1900, 1080, k=2, fondo="#ffffff")
    L.texto(50, 28, "Storyboard 2 · Anatomía de Hitboxes, Headshot y AoE", 30, "#111", True)
    # --- Panel A Modo 1
    L.rect(40, 90, 860, 950, fill="#f7f6f2", r=14)
    L.texto(70, 112, "A · ModoSupervivenciaHordas (zoom ×6)", 22, "#111", True)
    Z, cx, base = 6, 400, 930
    zh, zw = 88 * Z, 38 * 0.65 * Z
    L.rect(40, base, 860, 6, fill="#8a8984")
    _zombie(L, cx, base, Z)
    top = base - zh
    L.rect(cx - zw, top, 2 * zw, zh * 0.32, fill=(237, 161, 0, 70))
    L.rect(cx - zw, top, 2 * zw, zh, outline="#2a78d6", width=3, dash=True)
    L.linea_disc([(cx - zw - 60, base - zh * 0.68), (cx + zw + 60, base - zh * 0.68)], "#eb6834", 3)
    # cotas
    L.flecha(cx - zw - 30, base, cx - zw - 30, top + 4, "#2a78d6", 2)
    L.texto(cx - zw - 40, (base + top) / 2, "zh = getAlturaVisual()\n= 88 × escala", 17, "#2a78d6", anchor="rm")
    L.flecha(cx - zw, top - 24, cx + zw, top - 24, "#2a78d6", 2)
    L.texto(cx, top - 30, "2·zw  (zw = getAnchoVisual() × 0.65)", 16, "#2a78d6", anchor="md")
    L.texto(cx + zw + 66, base - zh * 0.68 - 4, "zy − zh × 0.68", 17, "#eb6834", True, mono=True, anchor="ld")
    L.texto(cx + zw + 20, top + 30, "HEADSHOT: 32 % superior", 18, "#b07700", True)
    L.texto(cx + zw + 20, top + 56, "daño × getMultiplicadorCritico()", 16, "#b07700", mono=True)
    # proyectiles
    L.elipse(cx - 40, top + 40, 9, 9, fill="#e34948")
    L.texto(cx - 40, top + 58, "¡CRÍTICO!", 16, "#e34948", True, anchor="ma")
    L.elipse(cx - 12, base - 200, 9, 9, fill="#6250d6")
    L.texto(cx + zw + 20, base - 210, "impacto normal (mult = 1.0)", 16, "#6250d6")
    L.texto(70, 980, "Math.abs(p.getX() - zx) <= zw && p.getY() >= zy - zh && p.getY() <= zy", 15, "#111",
            mono=True)
    L.texto(70, 1004, "zy = y del pie del zombie (Y crece hacia abajo en Swing)", 15, "#555")
    # --- Panel B Modo 2
    L.rect(930, 90, 930, 950, fill="#f7f6f2", r=14)
    L.texto(960, 112, "B · ModoDueloBatallones (zoom ×1.25)", 22, "#111", True)
    Z2, bx, base2 = 1.25, 1250, 770
    L.texto(960, 160, "factor = limitar(1 − dist / (radioExplosion + 70) × 0.45, 0.4, 1.0)", 15, "#111", mono=True)
    L.texto(960, 186, "dist = hypot(b.x − p.x, (b.y − 45) − p.y)  →  daño en área (AoE)", 15, "#111", mono=True)
    L.texto(960, 216, "Orden de colisión: ObstaculoTerreno → Y_SUELO → Batallon rival", 16, "#555")
    L.rect(930, base2, 930, 6, fill="#8a8984")
    # explosion AoE
    ex, ey = bx + 190, base2 - 6
    for r_, a in ((190, 40), (145, 70)):
        L.elipse(ex, ey, r_ * Z2, r_ * Z2, fill=(235, 104, 52, a), outline=(235, 104, 52, 200), width=2)
    L.elipse(ex, ey, 10, 10, fill="#e34948")
    L.linea([(ex, ey), (ex + 145 * Z2 * 0.7071, ey - 145 * Z2 * 0.7071)], "#c2410c", 2)
    L.texto(ex + 145 * Z2 * 0.7071 - 8, ey - 145 * Z2 * 0.7071 - 6, "radioExplosion = 145.0", 17, "#c2410c", True,
            mono=True, anchor="rd")
    L.texto(ex, ey - 190 * Z2 - 10, "alcance efectivo contra Batallon: 145 + 45 = 190", 16, "#c2410c", anchor="md")
    # batallon
    for k_ in range(4):
        x = bx + (-52 + k_ * 34) * Z2
        col = (70, 120, 200) if k_ < 3 else (150, 150, 150)
        if k_ < 3:
            L.rect(x - 9 * Z2, base2 - 60 * Z2, 18 * Z2, 46 * Z2, fill=col, r=6)
            L.elipse(x, base2 - 70 * Z2, 10 * Z2, 10 * Z2, fill=(225, 190, 160))
        else:
            L.rect(x - 23 * Z2, base2 - 18 * Z2, 46 * Z2, 16 * Z2, fill=col, r=6)
            L.texto(x, base2 - 30 * Z2, "caído", 14, "#555", anchor="md")
    L.rect(bx - 78 * Z2, base2 - 95 * Z2, 156 * Z2, 95 * Z2, outline="#2a78d6", width=3, dash=True)
    L.texto(bx, base2 + 40, "caja unificada: |Δx| ≤ 78 y entre y − 95 e y", 16, "#2a78d6", True,
            anchor="md")
    L.texto(960, 1000, "La GRANADA daña por área aunque explote en el suelo junto al Batallon.", 16, "#555")
    L.guardar(D_SB / "sb2_hitboxes.png")
    log("Storyboard 2 (hitboxes) listo")


def storyboard_ui():
    L = Lienzo(1900, 1720, k=2, fondo="#ffffff")
    L.texto(50, 28, "Storyboard 3 · Mapa de navegación de la interfaz (coordenadas reales 1280×720)", 30, "#111", True)
    ox = 50
    # --- Frame A: menu
    oy = 110
    L.rect(ox, oy, 1280, 720, fill=(30, 26, 32))
    L.texto(ox + 640, oy + 125, "THE WALKING BOWMASTERS", 46, (255, 196, 90), True, anchor="ms")
    L.texto(ox + 640, oy + 166, "Edición POO Modular", 20, (210, 200, 190), anchor="ms")
    tit = ["[1] MODO 1 · SUPERVIVENCIA DE HORDAS", "[2] MODO 2 · DUELO 1v1 DE BATALLONES", "[3] MODO 3 · ARMERÍA Y CAMPO DE TIRO"]
    for i, (y, t) in enumerate(zip((248, 336, 424), tit)):
        hov = i == 1
        L.rect(ox + 380 + (6 if hov else 0), oy + y, 520, 74, fill=(70, 56, 40) if hov else (48, 42, 48),
               outline=(255, 196, 90) if hov else (90, 84, 90), width=3 if hov else 1, r=10)
        L.texto(ox + 408 + (6 if hov else 0), oy + y + 22, ("> " if hov else "") + t, 18, "white", True)
        if hov:
            L.texto(ox + 380 + 520 - 84, oy + y + 22, "ENTRAR >", 15, (255, 196, 90), True)
    # cursor mano
    cx, cy = ox + 830, oy + 392
    L.poli([(cx, cy), (cx, cy + 34), (cx + 9, cy + 26), (cx + 16, cy + 40), (cx + 22, cy + 37), (cx + 15, cy + 24),
            (cx + 26, cy + 24)], fill="white", outline="black")
    L.rect(ox + 1065, oy + 22, 185, 38, fill=(48, 42, 48), outline=(120, 120, 120), r=8)
    L.texto(ox + 1078, oy + 32, "SONIDO [M]: ACTIVADO", 14, "white", True)
    L.texto(ox + 230, oy + 562, "CONTROLES Y NAVEGACION MEJORADA:", 16, (255, 196, 90), True)
    L.texto(ox + 230, oy + 590, "• Menú con cursor · Flechas + ENTER · teclas 1, 2, 3", 15, (220, 215, 210))
    L.rect(ox, oy, 1280, 720, outline="#111", width=3)
    for n, (bx_, by_) in enumerate([(380 + 6, 336), (880, 446), (1065, 22)], start=1):
        L.badge(ox + bx_ - 6, oy + by_ - 6, n)
    # --- Frame B: HUD en juego
    oy = 900
    _escena(L, ox, oy, 0)
    L.rect(ox, oy, 1280, 58, fill=(20, 18, 22, 235))
    navs = [("MENÚ", 16, 104, False), ("F1 HORDAS", 130, 152, False), ("F2 DUELO 1v1", 290, 156, True),
            ("F3 ARMERÍA", 454, 152, False)]
    for t, x, w, act in navs:
        L.rect(ox + x, oy + 11, w, 36, fill=(235, 104, 52) if act else (52, 48, 56), r=8)
        L.texto(ox + x + w / 2, oy + 29, t, 15, "white", True, anchor="mm")
    L.texto(ox + 624, oy + 22, "TECLA [X]:", 13, (230, 230, 230), True)
    L.texto(ox + 600, oy + 40, "", 12, "white")
    for t, x, w, act in (("5%", 690, 74, False), ("100%", 770, 84, True)):
        L.rect(ox + x, oy + 11, w, 36, fill=(42, 120, 214) if act else (52, 48, 56), r=8)
        L.texto(ox + x + w / 2, oy + 29, t, 16, "white", True, anchor="mm")
    L.rect(ox + 872, oy + 11, 116, 36, fill=(52, 48, 56), r=8)
    L.texto(ox + 930, oy + 29, "SONIDO ON", 14, "white", True, anchor="mm")
    L.texto(ox + 1090, oy + 22, "Botin: 160", 17, (255, 210, 110), True)
    L.rect(ox, oy + 622, 1280, 98, fill=(20, 18, 22, 235))
    armas = [("[1] Rifle de Asalto M4", "Ammo: 48"), ("[2] Lanzagranadas M79", "Ammo: 9"),
             ("[3] Revolver Python .357", "Ammo: 20"), ("[4] Katana de Michonne", "Infinita")]
    for i, (n, m) in enumerate(armas):
        bx_ = 24 + i * 200
        sel = i == 1
        L.rect(ox + bx_, oy + 634, 188, 72, fill=(62, 54, 46) if sel else (40, 36, 42),
               outline=(235, 104, 52) if sel else (90, 84, 90), width=2, r=10)
        L.texto(ox + bx_ + 10, oy + 640, n, 13, "white", True)
        L.texto(ox + bx_ + 84, oy + 680, m, 13, (210, 200, 190))
    for i, t in enumerate(["[Q] Curar", "[E] Municion", "[R] Racion"]):
        sx_ = 845 + i * 140
        L.rect(ox + sx_, oy + 634, 130, 72, fill=(40, 36, 42), outline=(90, 84, 90), width=2, r=10)
        L.texto(ox + sx_ + 12, oy + 645, t, 14, "white", True)
        L.texto(ox + sx_ + 14, oy + 675, "x3", 15, (255, 210, 110), True)
    # guia de carga X
    L.rect(ox + 230, oy + 420, 150, 22, fill=(20, 18, 22, 220), r=6)
    L.rect(ox + 232, oy + 432, 146 * 0.62, 8, fill=(235, 161, 0), r=4)
    L.texto(ox + 242, oy + 421, "TECLA X: 62%", 11, "white", True)
    L.rect(ox, oy, 1280, 720, outline="#111", width=3)
    for n, (bx_, by_) in enumerate([(130, 11), (690, 11), (1090, 22), (24, 634), (845, 634), (230, 420)], start=4):
        L.badge(ox + bx_ - 4, oy + by_ - 4, n)
    # leyenda
    lx = 1360
    items = [
        ("A · MENU_PRINCIPAL", None),
        ("1", "Tarjeta con hover: detectarHoverMenu(x, y) → borde dorado + ‘ENTRAR >’ + sonido hover"),
        ("2", "Cursor HAND_CURSOR sobre botones; CROSSHAIR_CURSOR al jugar"),
        ("3", "btnMenuSonido / tecla [M] → GestorSonido.alternarSonido()"),
        ("B · HUD EN JUEGO", None),
        ("4", "Barra superior persistente: navMenu, navModo1-3 · atajos F1/F2/F3 · manejarClicBarraSuperior"),
        ("5", "Selector [X: 5% | 100%] (navPot5 / navPot100) · tecla [C] alterna"),
        ("6", "Botín de inventarioCompartido.getRecursosAcumulados()"),
        ("7", "Tarjetas de armas [1-4] (188×72, bx = 24 + i·200)"),
        ("8", "Suministros [Q/E/R] (130×72, sx = 845 + i·140)"),
        ("9", "Mantener [X]: tras 0.18 s carga 5 % → 100 % en 1.05 s"),
    ]
    y = 130
    for n, t in items:
        if t is None:
            L.texto(lx, y, n, 21, "#111", True); y += 40
            if n.startswith("B"):
                pass
            continue
        L.badge(lx + 13, y + 12, n)
        palabras, linea_, lineas_ = t.split(), "", []
        for p in palabras:
            if len(linea_ + " " + p) > 40:
                lineas_.append(linea_); linea_ = p
            else:
                linea_ = (linea_ + " " + p).strip()
        lineas_.append(linea_)
        for j, s in enumerate(lineas_):
            L.texto(lx + 36, y + j * 23, s, 16, "#333")
        y += 23 * len(lineas_) + 26
        if n == "3":
            y = max(y, 900)
    L.guardar(D_SB / "sb3_ui.png")
    log("Storyboard 3 (UI) listo")


# ---------------------------------------------------------------------------
# 4. Codigos QR
# ---------------------------------------------------------------------------
def gh(rel: str, l1: int | None = None, l2: int | None = None) -> str:
    url = f"{REPO_WEB}/blob/{RAMA}/{rel}"
    if l1:
        url += f"#L{l1}" + (f"-L{l2}" if l2 and l2 != l1 else "")
    return url


QRS = {
    "repo": REPO_WEB,
    "arma": gh("armas/Arma.java"),
    "batallon": gh("entidades/Batallon.java"),
    "duelo": gh("modos/ModoDueloBatallones.java"),
    "sonido": gh("audio/GestorSonido.java"),
    "audio_dir": f"{REPO_WEB}/tree/{RAMA}/estudio_audiovisual/audio",
}


def generar_qr():
    for nombre, url in QRS.items():
        q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=1)
        q.add_data(url); q.make(fit=True)
        q.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(str(D_QR / f"qr_{nombre}.svg"))
    log(f"{len(QRS)} codigos QR (SVG)")


# ---------------------------------------------------------------------------
# 5. Diagramas Mermaid
# ---------------------------------------------------------------------------
VISTAS_UML = [
    ("1.1.a Interfaces y jerarquía de combatientes",
     ["Renderizable", "Atacable", "EntidadJuego", "Proyectil", "Combatiente", "Superviviente", "Zombie",
      "ZombieCaminante", "ZombieCorredor", "ZombieBlindado", "SaqueadorRival", "Batallon", "MiembroEscuadron"]),
    ("1.1.b Armas, inventario y suministros",
     ["Arma", "RifleAsalto", "LanzaGranadas", "Revolver", "EspadaKatana", "Inventario", "Suministro", "Combatiente"]),
    ("1.1.c Modos de juego, motor y audio",
     ["ModoJuego", "BaseModoJuego", "ModoSupervivenciaHordas", "ModoDueloBatallones", "ModoArmeriaCampoTiro",
      "WalkingBowmastersPOO", "GestorSonido", "Inventario"]),
]


def vista_uml(completo: str, clases: list) -> str:
    """Subdiagrama de clases: bloques completos de las clases elegidas + relaciones internas."""
    bloques = dict(re.findall(r"^    class (\w+) \{\n(.*?)^    \}", completo, re.S | re.M))
    lineas = ["classDiagram", "    direction TB"]
    for c in clases:
        lineas.append(f"    class {c} {{\n{bloques[c]}    }}")
    for rel in re.findall(r"^    (\w+ .*(?:<\|--|<\|\.\.|\*--|o--|-->|\.\.>).*)$", completo, re.M):
        toks = re.findall(r"\b[A-Z]\w+\b", rel.split(":")[0])
        if len(toks) >= 2 and toks[0] in clases and toks[-1] in clases:
            lineas.append("    " + rel)
    return "\n".join(lineas)


def mermaid_desde_md():
    md = GUIA_MD.read_text(encoding="utf-8")
    bloques = re.findall(r"```mermaid\n(.*?)```", md, re.S)
    clase = bloques[0].replace("Map~String, byte[]~", "Map~String,byte[]~")
    return clase


DIAG_OBJETOS = r"""flowchart LR
  Motor["<b>app : WalkingBowmastersPOO</b><br/>estado = JUGANDO_MODO_2"]
  Modo["<b>modoDuelo : ModoDueloBatallones</b><br/>fase = PROYECTIL_EN_VUELO<br/>vientoActual = -48.5 · camaraX = 310.0<br/>turnoIA = 1 · botinProcesadoEnTurno = false"]
  subgraph CJ["Composición Fuerte ◆ (vive y muere con batallonJugador)"]
    direction TB
    BJ["<b>batallonJugador : Batallon</b><br/>x = 210.0 · y = 582.0<br/>vida = 240 / 320 (75 %)<br/>armadura = 8 · esJugador = true"]
    M0["miembros[0] : MiembroEscuadron<br/>offsetX = -52 · sombrero<br/>vivo = true"]
    M1["miembros[1] : MiembroEscuadron<br/>offsetX = -18 · casco<br/>vivo = true"]
    M2["miembros[2] : MiembroEscuadron<br/>offsetX = 16<br/>vivo = true"]
    M3["miembros[3] : MiembroEscuadron<br/>offsetX = 50 · casco<br/>vivo = false · progresoCaida = 1.0"]
  end
  subgraph AG["Agregación Débil ◇ (objetos independientes)"]
    direction TB
    Inv["<b>inventarioCompartido : Inventario</b><br/>recursosAcumulados = 160<br/>bajasTotales = 1"]
    LG["armas[1] : LanzaGranadas<br/>'Lanzagranadas M79' · danoBase = 74<br/>municion = 9 / 24"]
    Bot["suministros[0] : Suministro<br/>tipo = BOTIQUIN · cantidad = 3"]
    Mun["suministros[1] : Suministro<br/>tipo = CAJA_MUNICION · cantidad = 3"]
  end
  subgraph MU["Entidades activas en escena"]
    direction TB
    BE["<b>batallonEnemigo : Batallon</b><br/>x = 1620.0 · vida = 320 / 320<br/>esJugador = false"]
    PR["<b>proyectiles[0] : Proyectil</b><br/>tipo = GRANADA · faccionJugador = true<br/>x = 785.4 · y = 264.2<br/>vx = 512.0 · vy = -190.5<br/>radioExplosion = 145.0"]
    OB["obstaculos[0] : ObstaculoTerreno<br/>tipo = AUTOBUS · x = 780 · y = 464<br/>185 × 118"]
  end
  Motor -->|modoActivo| Modo
  Motor -->|"crea ◇"| Inv
  Modo --> BJ
  Modo --> BE
  Modo --> PR
  Modo --> OB
  BJ ==>|"◆ *--"| M0
  BJ ==>|"◆ *--"| M1
  BJ ==>|"◆ *--"| M2
  BJ ==>|"◆ *--"| M3
  BJ -.->|"inventario ◇"| Inv
  BJ -.->|"armaActual ◇"| LG
  Inv -.->|"◇ o--"| LG
  Inv -.->|"◇ o--"| Bot
  Inv -.->|"◇ o--"| Mun
  classDef comp fill:#e8f0fb,stroke:#2a78d6,stroke-width:2px,color:#0b0b0b
  classDef agr fill:#fdf0e9,stroke:#eb6834,stroke-width:2px,color:#0b0b0b
  classDef mot fill:#1f1d24,stroke:#1f1d24,color:#ffffff
  classDef caido fill:#eeeeee,stroke:#8a8984,stroke-dasharray:4 3,color:#52514e
  class BJ,M0,M1,M2 comp
  class M3 caido
  class Inv,LG,Bot,Mun agr
  class Motor,Modo mot
"""

DIAG_ESTADOS = r"""stateDiagram-v2
  direction LR
  [*] --> MENU_PRINCIPAL
  MENU_PRINCIPAL --> JUGANDO_MODO_1 : clic / 1 / F1
  MENU_PRINCIPAL --> JUGANDO_MODO_2 : clic / 2 / F2
  MENU_PRINCIPAL --> JUGANDO_MODO_3 : clic / 3 / F3
  JUGANDO_MODO_1 --> MENU_PRINCIPAL : ESC / MENÚ
  JUGANDO_MODO_2 --> MENU_PRINCIPAL : ESC / MENÚ
  JUGANDO_MODO_3 --> MENU_PRINCIPAL : ESC / MENÚ
  JUGANDO_MODO_1 --> JUGANDO_MODO_2 : F2
  JUGANDO_MODO_2 --> JUGANDO_MODO_3 : F3
  JUGANDO_MODO_3 --> JUGANDO_MODO_1 : F1
"""

DIAG_TURNOS = r"""stateDiagram-v2
  direction LR
  [*] --> TURNO_JUGADOR : iniciarModo()
  TURNO_JUGADOR --> PROYECTIL_EN_VUELO : soltar ratón / tecla X
  PROYECTIL_EN_VUELO --> PAUSA_IMPACTO : proyectiles.isEmpty()
  PAUSA_IMPACTO --> TURNO_IA : 1.05 s (tras turno jugador)
  PAUSA_IMPACTO --> TURNO_JUGADOR : 1.05 s (tras turno IA)
  TURNO_IA --> PROYECTIL_EN_VUELO : 1.0 s → ejecutarDisparoIA()
  PAUSA_IMPACTO --> FIN_DUELO : un batallón con vida 0
  FIN_DUELO --> TURNO_JUGADOR : ENTER (NUEVO DUELO)
"""


def diag_paquetes(deps, ciclos, info):
    cuenta = defaultdict(int)
    for f in info:
        cuenta[f["paquete"]] += 1
    en_ciclo = {p for c in ciclos for p in c}
    ids = {p: ("raiz" if p == "(raiz)" else p) for p in set(deps) | {d for v in deps.values() for d in v}}
    lineas = ["flowchart TB"]
    for p, i in sorted(ids.items()):
        nombre = "WalkingBowmastersPOO<br/>(paquete por defecto)" if p == "(raiz)" else f"{p}/"
        lineas.append(f'  {i}["<b>{nombre}</b><br/>{cuenta[p]} archivo(s)"]')
    aristas, rojas = [], []
    for a in sorted(deps):
        for b in sorted(deps[a]):
            ciclo = a in en_ciclo and b in en_ciclo and any(a in c and b in c for c in ciclos)
            if ciclo:
                rojas.append(len(aristas))
            aristas.append(f"  {ids[a]} --> {ids[b]}")
    lineas += aristas
    if rojas:
        lineas.append(f"  linkStyle {','.join(map(str, rojas))} stroke:#e34948,stroke-width:3px")
    lineas.append("  classDef ciclo fill:#fdecec,stroke:#e34948,stroke-width:2px,color:#0b0b0b")
    lineas.append("  classDef base fill:#f4f3ef,stroke:#8a8984,color:#0b0b0b")
    lineas.append("  classDef raiz fill:#1f1d24,stroke:#1f1d24,color:#ffffff")
    lineas.append(f"  class {','.join(ids[p] for p in sorted(ids) if p in en_ciclo) or 'raiz'} ciclo")
    otros = [ids[p] for p in sorted(ids) if p not in en_ciclo and p != "(raiz)"]
    if otros:
        lineas.append(f"  class {','.join(otros)} base")
    lineas.append("  class raiz raiz")
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# 6. Resaltado de sintaxis Java (HTML)
# ---------------------------------------------------------------------------
KW = set("""abstract boolean break byte case catch char class continue default do double else enum extends final
finally float for if implements import instanceof int interface long new package private protected public return
short static super switch this throw throws try void volatile while true false null""".split())
TOK = re.compile(r'(?P<com>//[^\n]*|/\*.*?\*/)|(?P<str>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])\')|(?P<ann>@\w+)'
                 r'|(?P<num>\b\d+(?:\.\d+)?[dDfFL]?\b)|(?P<id>\b[A-Za-z_]\w*\b)', re.S)


def resaltar(codigo: str) -> str:
    out, pos = [], 0
    for m in TOK.finditer(codigo):
        out.append(html.escape(codigo[pos:m.start()]))
        t = m.group(0); e = html.escape(t)
        if m.lastgroup == "com":
            out.append(f'<span class="c">{e}</span>')
        elif m.lastgroup == "str":
            out.append(f'<span class="s">{e}</span>')
        elif m.lastgroup == "ann":
            out.append(f'<span class="a">{e}</span>')
        elif m.lastgroup == "num":
            out.append(f'<span class="n">{e}</span>')
        elif t in KW:
            out.append(f'<span class="k">{e}</span>')
        elif t[0].isupper():
            out.append(f'<span class="t">{e}</span>')
        else:
            out.append(e)
        pos = m.end()
    out.append(html.escape(codigo[pos:]))
    return "".join(out)


def bloque_codigo(ex: dict, titulo: str = "", nota: str = "") -> str:
    lineas = ex["codigo"].split("\n")
    nums = "\n".join(str(ex["l1"] + i) for i in range(len(lineas)))
    url = gh(ex["rel"], ex["l1"], ex["l2"])
    return f"""<figure class="code">
  <figcaption><span class="file">{html.escape(ex['rel'])}</span><span class="lines">líneas {ex['l1']}–{ex['l2']}</span>
  <a href="{url}">ver en GitHub ↗</a></figcaption>
  {f'<div class="code-title">{titulo}</div>' if titulo else ''}
  <div class="code-body"><pre class="ln">{nums}</pre><pre class="src">{resaltar(ex['codigo'])}</pre></div>
  {f'<div class="code-note">{nota}</div>' if nota else ''}
</figure>"""


def java_inline(codigo: str, titulo: str = "") -> str:
    return f"""<figure class="code">{f'<figcaption><span class="file">{titulo}</span></figcaption>' if titulo else ''}
<div class="code-body"><pre class="src">{resaltar(codigo)}</pre></div></figure>"""


def mermaid(codigo: str, nombre: str, clase: str = "") -> str:
    return f'<div class="mermaid-box {clase}" data-nombre="{nombre}"><pre class="mermaid-src">{html.escape(codigo)}</pre></div>'


def img(ruta: Path, alt: str, pie: str, clase: str = "") -> str:
    rel = ruta.relative_to(REC).as_posix()
    return f'<figure class="fig {clase}"><img src="{rel}" alt="{html.escape(alt)}"><figcaption>{pie}</figcaption></figure>'


def qr(nombre: str, etiqueta: str) -> str:
    return (f'<a class="qr" href="{QRS[nombre]}"><img src="qr/qr_{nombre}.svg" alt="QR {etiqueta}">'
            f'<span>{etiqueta}</span></a>')


# ---------------------------------------------------------------------------
# 7. Contenido del dossier (HTML)
# ---------------------------------------------------------------------------
CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
:root{
  --ink:#0b0b0b; --ink2:#3d3c39; --muted:#6f6e69; --line:#e4e3df; --paper:#ffffff; --soft:#f6f5f1;
  --night:#1c1a21; --night2:#2a2730; --blue:#2a78d6; --orange:#eb6834; --aqua:#1baf7a; --yellow:#eda100;
  --red:#e34948; --violet:#6250d6; --green:#008300;
  --sans:'Inter','Segoe UI',system-ui,sans-serif; --mono:'JetBrains Mono','Consolas',monospace;
}
@page{ size:A4; margin:19mm 15mm 17mm 15mm; }
@page uml{ size:A4 landscape; margin:14mm 12mm 14mm 12mm; }
html{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }
body{ font-family:var(--sans); color:var(--ink); background:var(--paper); font-size:9.6pt; line-height:1.52; margin:0; }
h1,h2,h3,h4{ font-weight:800; letter-spacing:-0.01em; line-height:1.2; break-after:avoid; }
h1{ font-size:24pt; margin:0 0 4mm; }
h2{ font-size:14.5pt; margin:7mm 0 2.5mm; padding-bottom:1.5mm; border-bottom:2px solid var(--ink); }
h3{ font-size:11.2pt; margin:5mm 0 2mm; color:var(--ink); }
h4{ font-size:9.8pt; margin:3mm 0 1.5mm; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
p{ margin:0 0 2.4mm; } a{ color:var(--blue); text-decoration:none; }
code{ font-family:var(--mono); font-size:8.4pt; background:#f0efea; padding:.2mm 1.1mm; border-radius:1mm; color:#2b2a33; }
.chapter{ break-before:page; }
.chapter-head{ background:var(--night); color:#fff; border-radius:4mm; padding:9mm 9mm 8mm; margin-bottom:6mm; position:relative; overflow:hidden; }
.chapter-head .num{ font-size:9pt; font-weight:700; letter-spacing:.18em; color:var(--yellow); text-transform:uppercase; }
.chapter-head h1{ color:#fff; margin:2mm 0 2mm; }
.chapter-head p{ color:#cfcbd6; margin:0; max-width:150mm; }
.chapter-head::after{ content:""; position:absolute; right:-18mm; top:-18mm; width:70mm; height:70mm; border-radius:50%;
  background:radial-gradient(circle, rgba(235,104,52,.55), rgba(235,104,52,0) 70%); }
table{ width:100%; border-collapse:collapse; margin:2mm 0 4mm; font-size:8.6pt; break-inside:auto; }
th{ text-align:left; background:var(--night2); color:#fff; font-weight:600; padding:1.8mm 2.2mm; }
td{ padding:1.7mm 2.2mm; border-bottom:1px solid var(--line); vertical-align:top; }
tr{ break-inside:avoid; } tbody tr:nth-child(even) td{ background:#faf9f6; }
.card{ border:1px solid var(--line); border-left:4px solid var(--blue); border-radius:2.5mm; padding:3.5mm 4.5mm; margin:3mm 0;
  background:var(--soft); break-inside:avoid; }
.card.orange{ border-left-color:var(--orange);} .card.aqua{ border-left-color:var(--aqua);} .card.yellow{ border-left-color:var(--yellow);}
.card.red{ border-left-color:var(--red);} .card.violet{ border-left-color:var(--violet);} .card.dark{ background:var(--night); color:#eee; border-color:var(--night); border-left-color:var(--yellow);}
.card h3,.card h4{ margin-top:0; }
.card.dark h3{ color:#fff; } .card.dark code{ background:#34303b; color:#ffd88a; }
.grid2{ display:grid; grid-template-columns:1fr 1fr; gap:4mm; } .grid3{ display:grid; grid-template-columns:repeat(3,1fr); gap:3.5mm; }
.grid2>*, .grid3>*{ break-inside:avoid; }
.pill{ display:inline-block; font-size:7.6pt; font-weight:700; padding:.4mm 2mm; border-radius:10mm; background:var(--night2); color:#fff; margin-right:1mm; }
.pill.blue{background:var(--blue);} .pill.orange{background:var(--orange);} .pill.aqua{background:var(--aqua);} .pill.red{background:var(--red);}
figure{ margin:3mm 0 4mm; break-inside:avoid; }
.fig img{ width:100%; display:block; border-radius:2mm; border:1px solid var(--line); }
.fig figcaption{ font-size:8pt; color:var(--muted); margin-top:1.5mm; }
.fig.chart img{ border:none; }
.code{ border-radius:2.5mm; overflow:hidden; background:#1e1c24; border:1px solid #2e2b36; }
.code figcaption{ display:flex; gap:3mm; align-items:center; background:#2a2731; padding:1.6mm 3mm; font-size:7.6pt; color:#b8b3c4; }
.code figcaption .file{ font-family:var(--mono); color:#ffd88a; font-weight:600; }
.code figcaption a{ margin-left:auto; color:#8fc3ff; }
.code-title{ color:#fff; font-size:8.2pt; font-weight:600; padding:1.6mm 3mm 0; }
.code-body{ display:flex; }
.code pre{ margin:0; font-family:var(--mono); font-size:7.5pt; line-height:1.5; padding:2.2mm 3mm; white-space:pre-wrap; }
.code pre.ln{ color:#5f5a6b; text-align:right; padding-right:2mm; border-right:1px solid #34303b; user-select:none; white-space:pre; }
.code pre.src{ color:#e7e3ee; flex:1; }
.code .k{ color:#ff8fb0; font-weight:600;} .code .t{ color:#7fd3ff;} .code .s{ color:#b5e48c;} .code .n{ color:#ffc56b;}
.code .c{ color:#8a8499; font-style:italic;} .code .a{ color:#c5a3ff;}
.code-note{ background:#2a2731; color:#d9d4e3; font-size:7.8pt; padding:1.8mm 3mm; border-top:1px solid #3a3644; }
.mermaid-box{ break-inside:avoid; text-align:center; margin:3mm 0; }
.mermaid-box svg{ max-width:100% !important; height:auto; }
.mermaid-box.tall svg{ max-height:205mm; width:auto; }
.mermaid-box.uml svg{ max-height:166mm; width:auto; }
.mermaid-box.estado svg{ width:100% !important; max-height:70mm; }
.mermaid-src{ display:none; }
.uml-page{ page:uml; break-before:page; }
.uml-page h2{ margin-top:0; }
.legend{ display:flex; gap:5mm; flex-wrap:wrap; font-size:8pt; color:var(--ink2); margin:1mm 0 2mm; }
.legend b{ font-family:var(--mono); color:var(--ink); }
.qr{ display:inline-flex; flex-direction:column; align-items:center; gap:1mm; font-size:7.4pt; color:var(--ink2); text-align:center; }
.qr img{ width:24mm; height:24mm; background:#fff; padding:1.5mm; border-radius:2mm; border:1px solid var(--line); }
.qr-row{ display:flex; gap:6mm; flex-wrap:wrap; margin:3mm 0; break-inside:avoid; }
.kpi{ background:var(--soft); border-radius:2.5mm; padding:3mm 4mm; border:1px solid var(--line); }
.kpi .v{ font-size:16pt; font-weight:800; } .kpi .l{ font-size:7.8pt; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }
.steps{ counter-reset:paso; display:grid; gap:2.6mm; }
.step{ display:grid; grid-template-columns:11mm 1fr; gap:3mm; align-items:start; break-inside:avoid; }
.step::before{ counter-increment:paso; content:counter(paso); width:11mm; height:11mm; border-radius:50%; background:var(--night);
  color:var(--yellow); font-weight:800; display:flex; align-items:center; justify-content:center; font-size:12pt; }
.step .body{ background:var(--soft); border:1px solid var(--line); border-radius:2.5mm; padding:2.5mm 3.5mm; }
.arrow-down{ text-align:center; color:var(--muted); font-size:12pt; line-height:1; margin:-1mm 0; }
.sb td:first-child{ width:34%; } .sb td:nth-child(2){ width:24%; } .sb td{ font-size:8.3pt; }
.sb .t{ font-family:var(--mono); font-size:7.6pt; color:var(--orange); font-weight:600; display:block; }
.say{ font-style:italic; color:#2b2a33; }
.q{ break-inside:avoid; border:1px solid var(--line); border-radius:2.5mm; margin:0 0 3mm; overflow:hidden; }
.q .qh{ background:var(--night); color:#fff; padding:2mm 3.5mm; font-weight:700; font-size:9.2pt; }
.q .qh span{ color:var(--yellow); margin-right:2mm; }
.q .qa{ padding:2.5mm 3.5mm; } .q .src{ font-size:7.8pt; color:var(--muted); margin-top:1.5mm; }
.check{ list-style:none; padding:0; margin:0; } .check li{ padding:1.6mm 0 1.6mm 8mm; position:relative; border-bottom:1px dashed var(--line); break-inside:avoid; }
.check li::before{ content:""; position:absolute; left:0; top:2mm; width:4mm; height:4mm; border:1.6px solid var(--ink); border-radius:1mm; }
.toc a{ color:var(--ink); display:flex; justify-content:space-between; padding:1.5mm 0; border-bottom:1px dotted #cfcdc6; }
.toc .sub{ padding-left:6mm; color:var(--ink2); font-size:9pt; }
blockquote{ margin:3mm 0; padding:3mm 4.5mm; border-left:4px solid var(--yellow); background:#fff8e6; border-radius:0 2.5mm 2.5mm 0; font-style:italic; break-inside:avoid; }
.audio-table td:first-child{ font-family:var(--mono); font-weight:600; }
.small{ font-size:8pt; color:var(--muted); }
.warn{ border-left-color:var(--red); background:#fff3f2; }
/* portada */
.cover{ height:258mm; background:var(--night); color:#fff; border-radius:5mm; padding:14mm 13mm; position:relative; overflow:hidden;
  display:flex; flex-direction:column; break-after:page; }
.cover::before{ content:""; position:absolute; inset:auto -40mm -60mm auto; width:200mm; height:200mm; border-radius:50%;
  background:radial-gradient(circle at 40% 40%, rgba(235,104,52,.75), rgba(227,73,72,.25) 45%, rgba(28,26,33,0) 70%); }
.cover::after{ content:""; position:absolute; left:0; right:0; bottom:0; height:62mm;
  background:repeating-linear-gradient(90deg, rgba(255,255,255,.05) 0 9mm, transparent 9mm 15mm); clip-path:polygon(0 60%,8% 45%,14% 52%,22% 30%,30% 42%,38% 20%,46% 38%,55% 25%,63% 46%,72% 28%,80% 44%,90% 32%,100% 50%,100% 100%,0 100%); }
.cover .kicker{ font-weight:700; letter-spacing:.2em; text-transform:uppercase; font-size:8.5pt; color:var(--yellow); }
.cover h1{ font-size:36pt; line-height:1.02; margin:6mm 0 3mm; color:#fff; letter-spacing:-0.02em; }
.cover h1 em{ font-style:normal; color:var(--orange); }
.cover .sub{ font-size:12pt; color:#d8d3df; max-width:140mm; }
.cover .spec{ position:relative; z-index:2; margin-top:auto; display:grid; grid-template-columns:1fr 34mm; gap:7mm; align-items:end; }
.cover table{ font-size:8.2pt; margin:0; } .cover th{ background:rgba(255,255,255,.08); }
.cover td{ border-bottom:1px solid rgba(255,255,255,.12); color:#efeaf5; background:transparent !important; padding:1.3mm 2mm; }
.cover .qr img{ width:32mm; height:32mm; } .cover .qr span{ color:#d8d3df; }
.cover .tags{ margin:5mm 0 0; display:flex; gap:2mm; flex-wrap:wrap; position:relative; z-index:2; }
"""


def construir_html(info, deps, ciclos, datos_ia):
    n_java = len(info)
    paquetes = sorted({f["paquete"] for f in info} - {"(raiz)"})
    total_lineas = sum(f["lineas"] for f in info)
    clase_uml = mermaid_desde_md()
    vistas_html = "".join(
        f'<section class="uml-page"><h2>{t}</h2>{mermaid(vista_uml(clase_uml, cl), "uml_vista_" + str(i), "uml")}</section>'
        for i, (t, cl) in enumerate(VISTAS_UML, 1))

    # ---------- extractos reales ----------
    X = {
        "action": extraer("WalkingBowmastersPOO.java", r"public void actionPerformed\("),
        "paint": extraer("WalkingBowmastersPOO.java", r"protected void paintComponent\(", max_lineas=34),
        "mapear": extraer("WalkingBowmastersPOO.java", r"Point2D.Double mapearAMundoVirtual\("),
        "ctor_app": extraer("WalkingBowmastersPOO.java", r"public WalkingBowmastersPOO\(\)", max_lineas=22),
        "vel": extraer("armas/Arma.java", r"public double calcularVelocidadInicial\("),
        "atacar_abs": extraer("armas/Arma.java", r"public List<Proyectil> atacar\(.*boolean faccionJugador"),
        "rifle": extraer("armas/RifleAsalto.java", r"public List<Proyectil> atacar\("),
        "granada": extraer("armas/LanzaGranadas.java", r"public List<Proyectil> atacar\("),
        "viento": extraer("entidades/Proyectil.java", r"public void actualizarConViento\("),
        "ia": extraer("modos/ModoDueloBatallones.java", r"private void ejecutarDisparoIA\("),
        "sim": extraer("modos/ModoDueloBatallones.java", r"private double simularTrayectoria\("),
        "dano": extraer("entidades/Combatiente.java", r"public int calcularDano\(int base\)", ),
        "dano3": extraer("entidades/Combatiente.java", r"public int calcularDano\(int base, double multiplicadorCritico, boolean"),
        "dano2": extraer("entidades/Combatiente.java", r"public int calcularDano\(int base, double multiplicadorCritico\)"),
        "miembro": extraer("entidades/Batallon.java", r"class MiembroEscuadron"),
        "bat_ctor": extraer("entidades/Batallon.java", r"public Batallon\("),
        "bat_vida": extraer("entidades/Batallon.java", r"private void actualizarMiembrosSegunVida\("),
        "bat_dest": extraer("entidades/Batallon.java", r"public void destruirBatallon\("),
        "consumir": extraer("inventario/Suministro.java", r"public boolean consumirUno\("),
        "usar": extraer("inventario/Inventario.java", r"public boolean usarSuministro\("),
        "robar": extraer("inventario/Inventario.java", r"public String robarSuministroAleatorio\("),
        "renderizable": extraer("interfaces/Renderizable.java", r"public interface Renderizable"),
        "modojuego": extraer("interfaces/ModoJuego.java", r"public interface ModoJuego"),
        "reproducir": extraer("audio/GestorSonido.java", r"private static void reproducir\("),
        "pool": extraer("audio/GestorSonido.java", r"ExecutorService POOL"),
        "sonido_arma": extraer("modos/BaseModoJuego.java", r"protected void reproducirSonidoArma\("),
        "disparar": extraer("entidades/Superviviente.java", r"public List<Proyectil> disparar\("),
        "efectos": extraer("modos/BaseModoJuego.java", r"protected void actualizarEfectos\(", max_lineas=26),
    }

    # ---------- tabla de armas ----------
    filas_armas = []
    for arma, (vb, ve, fac) in ARMAS.items():
        v5, v100 = v0(arma, 0.05), v0(arma, 1.0)
        g = GRAVEDAD_BASE * fac
        filas_armas.append(f"<tr><td><b>{arma}</b></td><td>{fac:.2f}</td><td>{g:.0f}</td><td>{vb:.0f} + {ve:.0f}</td>"
                           f"<td>{v5:.1f}</td><td>{v100:.0f}</td><td>{v100 ** 2 / g:,.0f}</td></tr>".replace(",", "."))
    # ---------- tabla de audio ----------
    filas_audio = []
    for clave, metodo, fn, p in EFECTOS:
        if fn == "sintetizarArpegio":
            notas, dn, vol = p
            dur = dn * len(notas); desc = f"notas {', '.join(f'{x:g}' for x in notas)} Hz · {dn * 1000:.0f} ms/nota"
        elif fn == "sintetizarBarrido":
            fi, ff, dur, vol, met, seed = p; desc = f"{fi}→{ff} Hz{' · metálico (×2.41 + ruido)' if met else ''}"
        else:
            dur, fi, ff, vol, pr, seed = p; desc = f"{fi}→{ff} Hz · ruido {pr:.0%}"
        filas_audio.append(f'<tr><td>{clave}</td><td><code>{metodo}</code></td><td>{fn}</td><td>{desc}</td>'
                           f'<td>{dur * 1000:.0f} ms</td><td>{vol:.2f}</td>'
                           f'<td><a href="audio/{clave}.wav">▶ {clave}.wav</a></td></tr>')
    # ---------- tabla paquetes ----------
    por_pk = defaultdict(list)
    for f in info:
        por_pk[f["paquete"]].append(f)
    filas_pk = []
    for pk in ["(raiz)"] + paquetes:
        fs = por_pk[pk]
        nombres = ", ".join(f'<a href="{gh(x["rel"])}">{Path(x["rel"]).stem}</a>' for x in fs)
        filas_pk.append(f"<tr><td><b>{pk}</b></td><td>{len(fs)}</td><td>{sum(x['lineas'] for x in fs)}</td><td>{nombres}</td></tr>")
    ia_filas = "".join(f"<tr><td>{t}</td><td>{e:.3f}</td><td>±{math.degrees(e * 0.7):.2f}°</td><td>±{e * 100:.1f} %</td>"
                       f"<td>{p:.0f} %</td><td>{m:.0f} px</td></tr>" for t, e, p, m in datos_ia)
    ciclo_txt = (" ↔ ".join(ciclos[0]) if ciclos else "ninguno")

    toc = [("cap1", "Capítulo 1 — Mapa visual de la arquitectura", ["Diagrama de clases UML", "Diagrama de objetos en runtime", "Dependencias entre paquetes"]),
           ("cap2", "Capítulo 2 — Radiografía del motor", ["Librerías y APIs", "Game loop a 60 FPS", "Máquinas de estado", "Pipeline de renderizado 2D"]),
           ("cap3", "Capítulo 3 — Laboratorio de balística, IA y audio PCM", ["Curvas balísticas", "Hitboxes y AoE", "IA estocástica", "Motor de audio"]),
           ("cap4", "Capítulo 4 — Los 6 pilares POO con evidencia", ["Abstracción", "Encapsulamiento", "Herencia", "Polimorfismo", "Composición fuerte", "Agregación débil"]),
           ("cap5", "Capítulo 5 — Kit audiovisual de exposición", ["Guion nivel 1", "Storyboard de la demo en vivo", "Banco de 10 preguntas", "Checklist de ensayo"])]
    toc_html = "".join(f'<a href="#{i}"><b>{t}</b></a>' + "".join(f'<div class="sub">· {s}</div>' for s in subs)
                       for i, t, subs in toc)

    H = []
    # =================== PORTADA ===================
    H.append(f"""
<section class="cover">
  <div class="kicker">Dossier de estudio avanzado · Lógica de Programación II</div>
  <h1>The Walking<br><em>Bowmasters</em></h1>
  <div class="sub">Guía de estudio audiovisual para expositores — Edición POO Modular. Cada línea de código,
  cada parábola, cada sonido sintetizado y cada pregunta difícil, explicados para sustentar con total seguridad.</div>
  <div class="tags"><span class="pill orange">Java SE · Swing / AWT</span><span class="pill blue">{n_java} archivos .java</span>
  <span class="pill aqua">{len(paquetes)} paquetes + clase principal</span><span class="pill red">{total_lineas:,} líneas</span></div>
  <div class="spec">
    <table>
      <tr><th colspan="2">Ficha técnica del proyecto</th></tr>
      <tr><td>Clase principal</td><td><code>WalkingBowmastersPOO extends JPanel implements ActionListener</code></td></tr>
      <tr><td>Resolución lógica</td><td>1280 × 720 (<code>ANCHO_VIRTUAL</code> × <code>ALTO_VIRTUAL</code>) escalado a cualquier ventana</td></tr>
      <tr><td>Bucle de juego</td><td><code>new Timer(16, this)</code> ≈ 60 FPS · <code>dt ≤ 0.05 s</code></td></tr>
      <tr><td>Física</td><td><code>GRAVEDAD_BASE = 540.0</code> px/s² · viento ±125 px/s² · <code>Y_SUELO = 582</code></td></tr>
      <tr><td>Audio</td><td>PCM 44 100 Hz · 16-bit · mono · 11 efectos · <code>MAX_VOCES = 10</code></td></tr>
      <tr><td>Modos</td><td>Hordas (Modo 1) · Duelo 1v1 (Modo 2) · Armería (Modo 3)</td></tr>
      <tr><td>Recursos externos</td><td>Ninguno: gráficos y sonidos 100 % procedurales</td></tr>
    </table>
    {qr('repo', 'Repositorio en GitHub')}
  </div>
</section>
<section>
  <h2 style="margin-top:0">Cómo usar este dossier</h2>
  <div class="grid2">
    <div class="card"><h4>Para estudiar</h4><p>Lee un capítulo por sesión. Cada afirmación técnica trae el <b>archivo, la clase y el
    número de línea</b> real (enlaces “ver en GitHub ↗”). Los bloques de código no están reescritos: se extraen automáticamente
    del código fuente cada vez que se ejecuta <code>generar_pdf_estudio.py</code>.</p></div>
    <div class="card orange"><h4>Para ensayar</h4><p>El Capítulo 5 contiene el guion de 3 minutos, el storyboard de la demo
    (pantalla · sonido · qué decir) y 10 preguntas difíciles con respuesta modelo. Los <b>11 sonidos .wav</b> en
    <code>estudio_audiovisual/audio/</code> son idénticos muestra a muestra a los que sintetiza <code>GestorSonido</code>.</p></div>
  </div>
  <h2>Contenido</h2>
  <div class="toc">{toc_html}</div>
  <div class="qr-row">{qr('arma', 'armas/Arma.java')}{qr('batallon', 'entidades/Batallon.java')}{qr('duelo', 'modos/ModoDueloBatallones.java')}{qr('sonido', 'audio/GestorSonido.java')}{qr('audio_dir', 'Carpeta de audios .wav')}</div>
  <p class="small">Fuente obligatoria: <code>GUIA_ARQUITECTURA_Y_EXPOSICION.md</code> + {n_java} archivos <code>.java</code> del proyecto.
  Los QR apuntan a la rama <code>{RAMA}</code> de <a href="{REPO_WEB}">{REPO_WEB.replace('https://', '')}</a>.</p>
</section>
""")
    # =================== CAPITULO 1 ===================
    H.append(f"""
<section class="chapter" id="cap1">
  <div class="chapter-head"><div class="num">Capítulo 1</div><h1>Mapa visual de la arquitectura</h1>
  <p>Tres fotografías del mismo sistema: la estructura estática (clases), una instantánea en memoria (objetos) y el
  acoplamiento entre carpetas (paquetes). Todos los diagramas son vectoriales: amplía sin perder nitidez.</p></div>
  <h2>1.0 Cómo leer las flechas UML</h2>
  <table><tr><th>Notación</th><th>Nombre</th><th>Significado en este proyecto</th><th>Ejemplo real</th></tr>
  <tr><td><code>A &lt;|-- B</code></td><td>Herencia (<code>extends</code>)</td><td>B <i>es un</i> A y reutiliza su código</td><td><code>Combatiente &lt;|-- Batallon</code></td></tr>
  <tr><td><code>I &lt;|.. C</code></td><td>Realización (<code>implements</code>)</td><td>C cumple el contrato de la interfaz I</td><td><code>Atacable &lt;|.. Combatiente</code></td></tr>
  <tr><td><code>A "1" *-- "4" B</code></td><td>Composición fuerte ◆</td><td>B nace y muere dentro de A; nadie más lo ve</td><td><code>Batallon *-- MiembroEscuadron</code></td></tr>
  <tr><td><code>A o-- B</code></td><td>Agregación débil ◇</td><td>A usa a B, pero B existe por su cuenta y se comparte</td><td><code>Combatiente o-- Inventario</code></td></tr>
  <tr><td><code>A --&gt; B</code> / <code>A ..&gt; B</code></td><td>Asociación / dependencia</td><td>A guarda una referencia / solo invoca a B</td><td><code>WalkingBowmastersPOO ..&gt; GestorSonido</code></td></tr>
  </table>
  <div class="card"><h4>Idea clave para la exposición</h4><p>Lee el diagrama de arriba hacia abajo: <b>3 interfaces</b>
  (<code>Renderizable</code>, <code>Atacable</code>, <code>ModoJuego</code>) → <b>5 clases abstractas</b> (<code>EntidadJuego</code>,
  <code>Combatiente</code>, <code>Zombie</code>, <code>Arma</code>, <code>BaseModoJuego</code>) → clases concretas. El motor
  (<code>WalkingBowmastersPOO</code>) sólo conoce los tipos abstractos: eso es lo que permite añadir un arma o un modo nuevo sin tocarlo.</p></div>
</section>
<section class="uml-page">
  <h2>1.1 Diagrama de clases UML completo</h2>
  <div class="legend"><span><b>&lt;|--</b> hereda</span><span><b>&lt;|..</b> implementa</span><span><b>*--</b> composición fuerte</span>
  <span><b>o--</b> agregación</span><span><b>--&gt;</b> asociación</span><span><b>..&gt;</b> dependencia</span>
  <span><b>+</b> public · <b>-</b> private · <b>#</b> protected · <b>*</b> abstracto</span></div>
  {mermaid(clase_uml, 'uml_clases', 'uml')}
  <p class="small">Vista general vectorial (amplía el PDF para leer cada miembro). Las tres páginas siguientes dividen el mismo diagrama en vistas legibles a tamaño real.</p>
</section>
{vistas_html}
<section style="break-before:page">
  <h2 style="margin-top:0">1.2 Diagrama de objetos en tiempo de ejecución — Modo 2 (Duelo 1v1)</h2>
  <p>Instantánea de la memoria durante <code>PROYECTIL_EN_VUELO</code>: <code>batallonJugador</code> ya recibió un impacto
  (240/320 HP = 75 %), por eso <code>miembros[3]</code> está caído, y una granada del <code>LanzaGranadas</code> vuela sobre el
  autobús. Azul = composición ◆, naranja = agregación ◇.</p>
  {mermaid(DIAG_OBJETOS, 'uml_objetos', 'tall')}
</section>
<section style="break-before:page">
  <h2 style="margin-top:0">1.3 Dependencias entre paquetes (análisis automático de <code>import</code>)</h2>
  <p>El script lee cada sentencia <code>import</code> de los {n_java} archivos y dibuja el grafo real. Las aristas rojas pertenecen a un
  ciclo detectado con el algoritmo de Tarjan.</p>
  {mermaid(diag_paquetes(deps, ciclos, info), 'paquetes', 'tall')}
  <div class="card {'red warn' if ciclos else 'aqua'}"><h4>{'Hallazgo honesto: existe un ciclo' if ciclos else 'Sin ciclos'}</h4>
  {'<p>Paquetes en ciclo: <b>' + ciclo_txt + '</b>. Causa: <code>armas.Arma.atacar(...)</code> crea objetos <code>entidades.Proyectil</code>, mientras que <code>entidades.Combatiente</code> guarda un <code>armas.Arma armaActual</code> (y <code>inventario.Inventario</code> agrupa armas). Java lo compila sin problema porque resuelve todos los tipos en la misma compilación, pero <b>no es un grafo acíclico</b>. Si el profesor pregunta, la respuesta está en la pregunta 8 del banco (Capítulo 5): se rompería moviendo <code>Proyectil</code> y <code>TipoProyectil</code> a un paquete propio (p. ej. <code>balistica/</code>) del que dependan tanto <code>armas</code> como <code>entidades</code>.</p>' if ciclos else '<p>El grafo es acíclico.</p>'}
  <p>Lo que sí está limpio: <code>util</code>, <code>interfaces</code> y <code>audio</code> no dependen de nadie (hojas); <code>modos</code> es la única capa que orquesta a todas; y ningún paquete depende de <code>modos</code> salvo la clase principal.</p></div>
  <table><tr><th>Paquete</th><th>Archivos</th><th>Líneas</th><th>Clases (enlace a GitHub)</th></tr>{''.join(filas_pk)}</table>
</section>
""")
    # =================== CAPITULO 2 ===================
    H.append(f"""
<section class="chapter" id="cap2">
  <div class="chapter-head"><div class="num">Capítulo 2</div><h1>Radiografía del motor</h1>
  <p>Librerías, latido de 60 FPS, máquinas de estado y el pipeline de dibujo 2D: cómo un <code>JPanel</code> se convierte en un juego.</p></div>
  <h2>2.1 Librerías y APIs utilizadas</h2>
  <table><tr><th style="width:22%">Paquete Java</th><th style="width:30%">Clases clave</th><th>Rol en el proyecto</th></tr>
  <tr><td><code>javax.swing.*</code></td><td>JFrame, JPanel, Timer, SwingUtilities</td><td>Ventana, lienzo con <i>double buffering</i>, creación de la GUI en el EDT (<code>invokeLater</code>) y latido <code>new Timer(16, this)</code>.</td></tr>
  <tr><td><code>java.awt.*</code></td><td>Graphics2D, RenderingHints, GradientPaint, BasicStroke, AlphaComposite, Polygon, Font, Cursor</td><td>Dibujo vectorial procedural de personajes, armas y fondos; degradados; transparencias; <code>HAND_CURSOR</code> / <code>CROSSHAIR_CURSOR</code>.</td></tr>
  <tr><td><code>java.awt.event.*</code></td><td>ActionListener, MouseAdapter, KeyAdapter</td><td>Arrastre estilo Bowmasters, <code>mouseMoved</code> (hover), atajos <code>1-4</code>, <code>Q/E/R</code>, <code>X</code>, <code>C</code>, <code>A/D</code>, <code>F1-F3</code>, <code>ESC</code>, <code>M</code>.</td></tr>
  <tr><td><code>java.awt.geom.*</code></td><td>Point2D.Double, Ellipse2D, RoundRectangle2D, Arc2D</td><td>Coordenadas virtuales en <code>double</code>, proyectiles, ondas expansivas y arcos de la Katana.</td></tr>
  <tr><td><code>java.util.*</code></td><td>List, ArrayList, Iterator, Map, HashMap, Random</td><td>Colecciones dinámicas; <code>Iterator.remove()</code> seguro al recorrer; caché de audio; oleadas y viento aleatorios.</td></tr>
  <tr><td><code>javax.sound.sampled.*</code></td><td>AudioFormat, AudioSystem, DataLine.Info, SourceDataLine</td><td>Síntesis y reproducción PCM 16-bit a 44 100 Hz en memoria, sin archivos.</td></tr>
  <tr><td><code>java.util.concurrent.*</code></td><td>ExecutorService, ThreadFactory, AtomicInteger</td><td>Pool de hilos <i>daemon</i> para hasta 10 voces simultáneas sin bloquear el render.</td></tr>
  </table>
  <h2>2.2 Infografía: el game loop de 60 FPS</h2>
  <div class="steps">
   <div class="step"><div class="body"><b>Latido.</b> El constructor crea <code>Timer loop = new Timer(16, this)</code>: cada ~16 ms Swing
   invoca <code>actionPerformed(ActionEvent e)</code> en el <i>Event Dispatch Thread</i> (1000/16 ≈ 62.5 → ~60 FPS reales).</div></div>
   <div class="step"><div class="body"><b>Entrada.</b> Entre ticks, <code>MouseAdapter</code> y <code>KeyAdapter</code> guardan el estado
   (cursor, arrastre, tecla <code>X</code> cargando…). El clic se convierte a coordenadas virtuales con <code>mapearAMundoVirtual(e)</code>.</div></div>
   <div class="step"><div class="body"><b>Delta-time.</b> <code>dt = Math.min(0.05, (ahora - ultimoNano) / 1e9)</code>. Todas las
   velocidades están en píxeles/segundo, así el juego corre igual en un PC rápido o lento; el tope de 50 ms evita que tras un
   tirón una bala “salte” a través de un zombie (<i>tunneling</i>).</div></div>
   <div class="step"><div class="body"><b>Actualización.</b> <code>escenario.actualizar(dt)</code> (cenizas) y
   <code>modoActivo.actualizarLogica(dt)</code>: IA, física, colisiones, partículas — <b>polimorfismo</b>: el motor no sabe qué modo es.</div></div>
   <div class="step"><div class="body"><b>Render.</b> <code>repaint()</code> agenda <code>paintComponent(Graphics g)</code>: escala virtual,
   shake, escena del modo, HUD. Swing vuelca el búfer oculto de una sola vez (sin parpadeo).</div></div>
  </div>
  {bloque_codigo(X['action'], 'El tick completo del motor', 'Medir el tiempo real con System.nanoTime() y acotarlo a 0.05 s es la base de una física estable.')}
  <h2>2.3 Máquinas de estado</h2>
  <h4>EstadoPantalla (WalkingBowmastersPOO)</h4>{mermaid(DIAG_ESTADOS, 'estados_pantalla', 'estado')}
  <h4>FaseTurno (ModoDueloBatallones)</h4>{mermaid(DIAG_TURNOS, 'fase_turno', 'estado')}
  <p>La barra superior persistente (<code>manejarClicBarraSuperior</code>) permite saltar de cualquier modo a cualquier otro;
  el <code>Inventario</code> compartido viaja con el jugador. En el duelo, <code>PAUSA_IMPACTO</code> dura <b>1.05 s</b> para ver
  caer al <code>MiembroEscuadron</code> y <code>TURNO_IA</code> espera <b>1.0 s</b> antes de <code>ejecutarDisparoIA()</code>.</p>
  <h2>2.4 Pipeline de renderizado 2D</h2>
  <div class="grid3">
    <div class="card"><h4>① Double buffering</h4><p><code>setDoubleBuffered(true)</code>: cada fotograma se pinta en memoria y se
    vuelca completo. <code>g.create()</code> + <code>KEY_ANTIALIASING</code> suavizan bordes y texto.</p></div>
    <div class="card orange"><h4>② Escala virtual</h4><p><code>escala = min(w/1280, h/720)</code>, se centra con
    <code>translate(offX, offY)</code> y <code>scale(escala, escala)</code>. El clic usa la inversa: <code>(e.getX() − offX) / escala</code>.</p></div>
    <div class="card aqua"><h4>③ Cámara + shake</h4><p>Mundo de 1860 px dibujado con <code>gw.translate(-camaraX, 0)</code>;
    Lerp a <code>dt × 6.5</code>; temblor aleatorio <code>± intensidadShake</code>. El HUD va después, fijo.</p></div>
  </div>
  {bloque_codigo(X['mapear'], 'Transformación inversa: de píxeles de ventana a mundo virtual 1280×720')}
  {bloque_codigo(X['paint'], 'paintComponent: escalado, centrado y screen shake (primeras líneas)')}
  {img(D_SB / 'sb1_parallax.png', 'Storyboard parallax', 'Storyboard 1 — Recreación con Pillow de las capas parallax (0.05 / 0.18 / 0.45 / 1.0), la cámara en sus dos extremos y el marco de screen shake.')}
</section>
""")
    # =================== CAPITULO 3 ===================
    H.append(f"""
<section class="chapter" id="cap3">
  <div class="chapter-head"><div class="num">Capítulo 3</div><h1>Laboratorio de balística, IA y audio PCM</h1>
  <p>Simulaciones numéricas ejecutadas con las mismas ecuaciones y constantes del código Java. Nada de lo que ves aquí es ilustrativo:
  son los números que produce el juego.</p></div>
  <h2>3.1 Cinemática parabólica con viento</h2>
  <div class="grid2">
   <div>
    <p><b>Velocidad inicial</b> (<code>Arma.calcularVelocidadInicial</code>), con la potencia limitada a [0.05, 1.00] y
    <code>vMin = 175</code>:</p>
    <p style="font-size:11pt;text-align:center"><i>v</i><sub>0</sub> = 175 + <i>p</i> · ((velocidadBase + velocidadExtra) − 175)</p>
    <p>Componentes: <code>vx = v0·cos(θ)</code>, <code>vy = −v0·sin(θ)</code> (negativo porque en Swing la Y crece hacia abajo).
    Cada fotograma <code>Proyectil.actualizarConViento(dt, viento)</code> integra con Euler semi-implícito:</p>
   </div>
   <div>{bloque_codigo(X['viento'])}</div>
  </div>
  <table><tr><th>Arma</th><th>factorGravedad</th><th>g efectiva (px/s²)</th><th>base + extra</th><th>v0 al 5 %</th><th>v0 al 100 %</th><th>Alcance ideal 45° (v²/g)</th></tr>
  {''.join(filas_armas)}</table>
  {img(D_GRAF / 'g1_balistica.svg', 'Curvas balísticas', 'Gráfico 1 — Integración a 60 Hz de las 4 armas (A: 100 %, B: 5 %) y del LanzaGranadas con viento ±125 px/s² sobre el mapa real del duelo (autobús, coche y cajas de impacto de los batallones).', 'chart')}
  <div class="card yellow"><h4>Cómo explicarlo en 20 segundos</h4><p>“El rifle tiene gravedad 0.45 y sale a 1100 px/s: casi una línea
  recta que sale de la pantalla. La granada tiene gravedad completa: al 100 % cae justo en la zona enemiga, y el viento de ±125 la mueve
  cientos de píxeles. Por eso en el duelo el viento decide la partida. La tecla X al 5 % es un ‘lob’ corto de menos de 100 px.”</p></div>
  {bloque_codigo(X['vel'])}
  <h2>3.2 Hitboxes, headshot y daño en área</h2>
  {img(D_SB / 'sb2_hitboxes.png', 'Hitboxes', 'Storyboard 2 — A: caja del Zombie y franja de headshot (32 % superior, por encima de zy − zh·0.68). B: caja unificada del Batallon (±78 × 95) y anillos de la explosión AoE.')}
  <p>En <code>ModoSupervivenciaHordas</code> el daño final se calcula con la <b>sobrecarga</b> de tres parámetros:
  <code>z.calcularDano(p.getDano(), mult, p.isIgnoraArmadura())</code>, donde <code>mult = p.getMultiplicadorCritico()</code> solo si es headshot.
  La granada se crea con <code>radioExplosion = 145.0</code>, <code>multiplicadorCritico = 1.15</code> e <code>ignoraArmadura = true</code>.</p>
  <h2>3.3 IA balística progresiva</h2>
  <p><code>ejecutarDisparoIA()</code> hace una búsqueda exhaustiva: 11 ángulos (122°…152°, paso 3°) × 14 potencias (0.45…0.97, paso 0.04)
  = <b>154 trayectorias simuladas</b> con el viento actual y los obstáculos, y se queda con la que cae más cerca de
  <code>batallonJugador.getX()</code>. Luego “se equivoca a propósito” con un error que decrece por turno:</p>
  <p style="text-align:center;font-size:10.5pt"><code>errorMaximo = Math.max(0.015, 0.14 - (turnoIA - 1) * 0.025)</code></p>
  {img(D_GRAF / 'g2_ia.svg', 'IA', 'Gráfico 2 — Izquierda: errorMaximo exacto por turno (llega al piso 0.015 en el turno 6). Derecha: probabilidad de impacto estimada con 3000 disparos Monte Carlo por turno (arma y viento aleatorios, misma búsqueda de 154 trayectorias, impacto directo en la caja o AoE de granada).', 'chart')}
  <table><tr><th>turnoIA</th><th>errorMaximo</th><th>ruido de ángulo (±0.7·e)</th><th>ruido de potencia</th><th>P(impacto) simulada</th><th>error mediano</th></tr>{ia_filas}</table>
  <div class="grid2">{bloque_codigo(X['ia'], 'Búsqueda + error estocástico')}{bloque_codigo(X['sim'], 'Simulación interna (dtSim = 0.02, 220 pasos)')}</div>
  <h2>3.4 Motor de audio PCM sintetizado</h2>
  <p><code>GestorSonido</code> no carga archivos: en su bloque <code>static</code> sintetiza 11 efectos en arreglos <code>byte[]</code>
  (16-bit little-endian, mono, 44 100 Hz) y los guarda en <code>CACHE</code>. Hay tres sintetizadores: <b>barrido</b> (seno con
  frecuencia lineal; modo metálico para la katana), <b>disparo</b> (tono con caída exponencial mezclado con ruido filtrado
  paso-bajo <code>filtro = filtro·0.45 + ruido·0.55</code>, envolvente <code>(1 − t)<sup>1.9</sup></code>) y <b>arpegio</b> (notas musicales:
  do-mi-sol para suministro/victoria, descendente para derrota).</p>
  {img(D_GRAF / 'g4_audio_pcm.svg', 'Audio PCM', 'Gráfico 4 — Formas de onda reales (bandas min/máx por bin) y envolvente × volumen de cuatro efectos, generadas con los mismos parámetros y semillas de java.util.Random que GestorSonido.java.', 'chart')}
  <table class="audio-table"><tr><th>Clave CACHE</th><th>Método público</th><th>Sintetizador</th><th>Parámetros</th><th>Duración</th><th>Vol.</th><th>Escuchar</th></tr>{''.join(filas_audio)}</table>
  <div class="grid2">
   <div class="card dark"><h3>Ficha: audio asíncrono</h3><p>• <code>ExecutorService POOL = Executors.newCachedThreadPool(...)</code> con hilos
   <b>daemon</b> “AudioFX-Worker” (no impiden cerrar la JVM).<br>• <code>AtomicInteger VOCES_ACTIVAS</code> y <code>MAX_VOCES = 10</code>: si ya
   suenan 10, el efecto se descarta en vez de saturar.<br>• Cada voz abre su <code>SourceDataLine</code>, escribe, hace <code>drain()</code> y
   cierra en <code>finally</code>.<br>• <code>volatile boolean sonidoActivo</code>: tecla <code>[M]</code>.</p></div>
   <div>{bloque_codigo(X['reproducir'])}</div>
  </div>
  <div class="card aqua"><h4>Guía de escucha</h4><p>Abre <code>estudio_audiovisual/audio/00_todos_los_efectos_en_orden.wav</code>: suenan los 11 efectos
  en el orden de la tabla con 0.6 s de silencio entre ellos. Asocia cada sonido a su acción (hover del menú, disparo del rifle,
  explosión…). En la demo, cuando suene uno, nómbralo: “eso que escucharon es <code>sintetizarDisparo</code> con 80 % de ruido”.
  Los enlaces ▶ de la tabla abren cada archivo (en Acrobat/SumatraPDF/Foxit, con el PDF junto a la carpeta <code>estudio_audiovisual/</code>).</p>
  <div class="qr-row">{qr('audio_dir', 'Audios en GitHub*')}{qr('sonido', 'GestorSonido.java')}</div>
  <p class="small">* El QR de audios funciona cuando la carpeta <code>estudio_audiovisual/</code> se suba al repositorio.</p></div>
</section>
""")
    # =================== CAPITULO 4 ===================
    H.append(f"""
<section class="chapter" id="cap4">
  <div class="chapter-head"><div class="num">Capítulo 4</div><h1>Los 6 pilares POO con evidencia de código</h1>
  <p>Para cada pilar: qué es, dónde está exactamente y el fragmento real que debes mostrar en pantalla.</p></div>
  <h2>4.1 Abstracción</h2>
  <div class="card"><p><b>Qué es:</b> definir <i>qué</i> hace algo sin decir <i>cómo</i>. <b>Dónde:</b> 3 interfaces
  (<code>Renderizable</code>, <code>Atacable</code>, <code>ModoJuego</code>) y 5 clases abstractas (<code>EntidadJuego</code>, <code>Combatiente</code>,
  <code>Zombie</code>, <code>Arma</code>, <code>BaseModoJuego</code>). El motor guarda un <code>BaseModoJuego modoActivo</code> y nunca pregunta cuál es.</p></div>
  <div class="grid2">{bloque_codigo(X['modojuego'], 'Contrato de todo modo de juego')}{bloque_codigo(X['renderizable'], 'Contrato de todo lo que se dibuja')}</div>
  <h2>4.2 Encapsulamiento</h2>
  <div class="card aqua"><p><b>Qué es:</b> el estado es <code>private</code> y sólo cambia por métodos que validan. <b>Dónde:</b>
  <code>Batallon.miembros</code>, <code>Inventario.armas/suministros/recursosAcumulados</code>, <code>Suministro.cantidad</code>,
  <code>GestorSonido.CACHE/sonidoActivo</code>. Nadie puede dejar una cantidad negativa: <code>consumirUno()</code> lo impide.</p></div>
  <div class="grid2">{bloque_codigo(X['consumir'])}{bloque_codigo(X['usar'])}</div>
  <h2>4.3 Herencia</h2>
  <div class="card yellow"><p><b>Qué es:</b> una subclase reutiliza y especializa a su padre. Tres jerarquías:
  <code>EntidadJuego → Combatiente → Superviviente | Zombie (ZombieCaminante, ZombieCorredor, ZombieBlindado) | SaqueadorRival | Batallon</code>;
  <code>Arma → RifleAsalto, LanzaGranadas, Revolver, EspadaKatana</code>; <code>BaseModoJuego → ModoSupervivenciaHordas, ModoDueloBatallones, ModoArmeriaCampoTiro</code>.
  Todas heredan <code>x, y, vida, armadura</code>, <code>calcularDano</code> y <code>dibujarBarraVida</code>; los modos heredan cámara, partículas y tecla X.</p></div>
  {bloque_codigo(X['bat_ctor'], 'Batallon llama a super(...) de Combatiente e inyecta el inventario')}
  <h2>4.4 Polimorfismo</h2>
  <h3>Sobreescritura (dinámico, en tiempo de ejecución)</h3>
  <p><code>Superviviente.disparar(...)</code> llama a <code>armaActual.atacar(...)</code> sin saber qué arma tiene. La JVM elige la versión
  correcta: ráfaga de 3 balas (<code>RifleAsalto</code>) o granada AoE (<code>LanzaGranadas</code>).</p>
  {bloque_codigo(X['disparar'])}
  <div class="grid2">{bloque_codigo(X['rifle'], '@Override en RifleAsalto')}{bloque_codigo(X['granada'], '@Override en LanzaGranadas')}</div>
  <h3>Sobrecarga (estático, en compilación)</h3>
  <p>Mismo nombre, distinta lista de parámetros. Las dos versiones cortas delegan en la completa (sin código duplicado):</p>
  {bloque_codigo(X['dano'])}{bloque_codigo(X['dano2'])}{bloque_codigo(X['dano3'], 'Versión completa', 'La armadura reduce round(armadura × 0.55) puntos, con un mínimo de 2 de daño; ignoraArmadura (granada) salta la reducción.')}
  {bloque_codigo(X['atacar_abs'], 'Sobrecarga + abstracción en Arma: la versión de 5 parámetros reutiliza la abstracta')}
  <h2>4.5 Composición fuerte — <code>Batallon *-- MiembroEscuadron</code></h2>
  <div class="card red"><p><b>Qué es:</b> la parte no puede existir sin el todo. <code>MiembroEscuadron</code> es una clase
  <code>private static final</code> <b>anidada</b> en <code>Batallon</code>: ningún otro archivo puede ni nombrarla. Los 4 miembros se crean en
  <code>inicializarMiembros()</code> (dentro del constructor) y desaparecen en <code>destruirBatallon()</code>.</p></div>
  {img(D_GRAF / 'g3_composicion.svg', 'Composición', 'Gráfico 3 — La vida global (320 HP) gobierna cuántos miembros siguen en pie: umbrales 75 % (240), 50 % (160), 25 % (80) y 0 %.', 'chart')}
  <div class="grid2">{bloque_codigo(X['miembro'], 'La parte (privada)')}{bloque_codigo(X['bat_vida'], 'El todo decide quién vive')}</div>
  {bloque_codigo(X['bat_dest'])}
  <h2>4.6 Agregación débil — <code>Inventario</code></h2>
  <div class="card orange"><p><b>Qué es:</b> el todo usa a la parte, pero la parte vive por su cuenta. <code>inventarioCompartido</code> nace en
  <code>WalkingBowmastersPOO</code> y se <b>inyecta</b> por constructor en los 3 modos. Si un personaje muere o cambias de Modo 1 → 2 → 3, el
  inventario (4 armas + suministros + botín) sigue intacto. Incluso puede ser saqueado: <code>robarSuministroAleatorio(rng)</code>.</p></div>
  {bloque_codigo(X['ctor_app'], 'Un solo Inventario, tres modos')}
  {bloque_codigo(X['robar'])}
  <table><tr><th></th><th>Composición (Batallon ◆ MiembroEscuadron)</th><th>Agregación (Combatiente ◇ Inventario)</th></tr>
  <tr><td><b>¿Quién crea la parte?</b></td><td>El propio <code>Batallon</code> (<code>new MiembroEscuadron</code> en <code>inicializarMiembros</code>)</td><td>Un tercero (<code>WalkingBowmastersPOO</code> / <code>ModoDueloBatallones</code>)</td></tr>
  <tr><td><b>¿Visibilidad?</b></td><td><code>private static final class</code></td><td><code>public class</code> en su propio paquete</td></tr>
  <tr><td><b>¿Se comparte?</b></td><td>Nunca</td><td>Sí, entre 3 modos</td></tr>
  <tr><td><b>¿Ciclo de vida?</b></td><td>Muere con el contenedor (<code>miembros.clear()</code>)</td><td>Sobrevive al combatiente y al cambio de modo</td></tr></table>
</section>
""")
    # =================== CAPITULO 5 ===================
    preguntas = [
        ("¿Dónde exactamente ocurre el polimorfismo dinámico y cómo lo demuestran?",
         "En <code>Superviviente.disparar(...)</code> y <code>Batallon.dispararEnUnisono(...)</code>, que invocan <code>armaActual.atacar(...)</code> sobre una referencia de tipo <code>Arma</code>. La JVM despacha a <code>RifleAsalto.atacar</code>, <code>LanzaGranadas.atacar</code>, <code>Revolver.atacar</code> o <code>EspadaKatana.atacar</code> según el objeto real. Demostración: en el Modo 3 pulsar <code>1</code> y luego <code>2</code> y disparar con la misma tecla <code>X</code>: misma línea de código, comportamiento distinto.",
         "entidades/Superviviente.java · disparar(); armas/*.java · atacar()"),
        ("¿Cuál es la diferencia real entre composición y agregación en su código?",
         "Composición: <code>MiembroEscuadron</code> es <code>private static final</code> dentro de <code>Batallon</code>, se crea en <code>inicializarMiembros()</code> y se elimina en <code>destruirBatallon()</code>; nadie fuera puede referenciarlo. Agregación: <code>Inventario</code> se crea en <code>WalkingBowmastersPOO</code> (<code>inventarioCompartido</code>) y se pasa por constructor a los 3 modos; sobrevive a la muerte del combatiente y al cambio de modo.",
         "entidades/Batallon.java; WalkingBowmastersPOO.java · constructor"),
        ("¿Por qué limitan dt a 0.05 en vez de usar el tiempo real?",
         "Si el sistema operativo pausa el programa (por ejemplo 300 ms), un <code>dt</code> grande haría avanzar un proyectil cientos de píxeles en un solo paso y podría atravesar la hitbox sin detectar la colisión (<i>tunneling</i>). Con <code>Math.min(0.05, ...)</code> el paso máximo es de 50 ms: el juego se ralentiza un instante pero la física sigue siendo correcta.",
         "WalkingBowmastersPOO.java · actionPerformed()"),
        ("¿Cómo evitan que el sonido congele el juego a 60 FPS?",
         "<code>GestorSonido.reproducir(clave)</code> no bloquea: envía un <code>Runnable</code> a un <code>ExecutorService</code> de hilos daemon. El hilo de Swing sólo hace <code>POOL.submit</code>. Además, <code>AtomicInteger VOCES_ACTIVAS</code> limita a <code>MAX_VOCES = 10</code>, y los sonidos ya están sintetizados en <code>CACHE</code> desde el bloque <code>static</code>.",
         "audio/GestorSonido.java · reproducir(), POOL"),
        ("¿Por qué usan interfaces y además clases abstractas? ¿No es redundante?",
         "No. La interfaz define un <b>contrato sin estado</b> que pueden cumplir jerarquías distintas (<code>Renderizable</code> lo cumple <code>EntidadJuego</code>; <code>Atacable</code>, <code>Combatiente</code>). La clase abstracta <b>comparte estado y código</b> (<code>x</code>, <code>y</code>, <code>vida</code>, <code>calcularDano</code>, <code>dibujarBarraVida</code>). Java sólo permite heredar de una clase pero implementar muchas interfaces.",
         "interfaces/*.java; entidades/EntidadJuego.java; entidades/Combatiente.java"),
        ("¿La IA hace trampa? ¿Cómo apunta?",
         "No conoce el resultado: simula. <code>simularTrayectoria(...)</code> reproduce la física (gravedad del arma, viento actual, obstáculos, suelo) con <code>dtSim = 0.02</code> durante 220 pasos para 154 combinaciones ángulo/potencia, elige la mejor y luego añade ruido <code>errorMaximo = max(0.015, 0.14 − (turnoIA − 1)·0.025)</code>. Por eso falla al principio y se vuelve letal hacia el turno 6 (ver Gráfico 2).",
         "modos/ModoDueloBatallones.java · ejecutarDisparoIA(), simularTrayectoria()"),
        ("Si agrando la ventana, ¿por qué el clic sigue cayendo en el botón correcto?",
         "Porque todo se dibuja en un lienzo virtual de 1280×720 escalado con <code>escala = min(w/1280, h/720)</code> y centrado con <code>offX/offY</code>. <code>mapearAMundoVirtual(MouseEvent e)</code> aplica la transformación inversa <code>(e.getX() − offX) / escala</code>, así los rectángulos como <code>btnMenuModo1 = new Rectangle(380, 248, 520, 74)</code> se comparan siempre en coordenadas virtuales.",
         "WalkingBowmastersPOO.java · mapearAMundoVirtual(), paintComponent()"),
        ("¿Hay dependencias circulares entre paquetes?",
         f"Sí, y conviene reconocerlo: <b>{ciclo_txt}</b>. <code>Arma.atacar</code> crea <code>entidades.Proyectil</code> y <code>Combatiente</code> referencia <code>armas.Arma</code>. Java lo compila porque resuelve todos los tipos juntos, pero acopla los paquetes. Solución propuesta: mover <code>Proyectil</code> y <code>TipoProyectil</code> a un paquete <code>balistica</code> (o que <code>Arma</code> reciba una fábrica/interfaz), de modo que <code>armas</code> y <code>entidades</code> dependan de él y no entre sí.",
         "Grafo generado automáticamente en el Capítulo 1.3"),
        ("¿Por qué usan Iterator.remove() al recorrer listas de proyectiles y partículas?",
         "Porque eliminar con <code>lista.remove(x)</code> dentro de un <code>for-each</code> lanza <code>ConcurrentModificationException</code>. <code>Iterator.remove()</code> es la única forma segura de quitar el elemento actual durante el recorrido (p. ej. <code>if (!it.next().actualizar(dt)) it.remove();</code>).",
         "modos/BaseModoJuego.java · actualizarEfectos(); modos/ModoArmeriaCampoTiro.java"),
        ("¿Qué hace exactamente la tecla X al 5 % y al 100 %?",
         "Dispara hacia el cursor con la potencia preseleccionada por <code>getPotenciaPresetX()</code> (<code>potenciaXAl100 ? 1.00 : 0.05</code>); <code>[C]</code> o los botones 5 %/100 % la alternan. Si se mantiene presionada, tras 0.18 s carga de 0.05 a 1.00 en 1.05 s (<code>potenciaCargaX</code>). La potencia entra a <code>calcularVelocidadInicial</code>, que la limita con <code>ConstantesJuego.limitar(potencia, 0.05, 1.0)</code>.",
         "modos/BaseModoJuego.java; armas/Arma.java · calcularVelocidadInicial()"),
    ]
    q_html = "".join(f'<div class="q"><div class="qh"><span>P{i}</span>{q}</div><div class="qa">{a}<div class="src">📁 {s}</div></div></div>'
                     for i, (q, a, s) in enumerate(preguntas, 1))

    def sb_tabla(filas):
        return ('<table class="sb"><tr><th>Qué mostrar / acción</th><th>Qué se escucha (GestorSonido)</th><th>Qué decir exactamente</th></tr>'
                + "".join(f'<tr><td><span class="t">{t}</span>{a}</td><td>{s}</td><td class="say">“{d}”</td></tr>' for t, a, s, d in filas)
                + "</table>")

    sb_menu = sb_tabla([
        ("00:00 – 00:30", "Ejecutar <code>java WalkingBowmastersPOO</code>. Pasar el cursor por las 3 tarjetas del menú.", "<code>hover</code> en cada tarjeta (barrido 680→920 Hz, 40 ms)", "Todo lo que ven está dibujado con Graphics2D y cada sonido se sintetiza matemáticamente en memoria; no hay ni una imagen ni un .wav en el proyecto."),
        ("00:30 – 00:45", "Pulsar <code>[M]</code> dos veces para mostrar el silencio y reactivar.", "Silencio → <code>click</code> al reactivar", "GestorSonido es una clase utilitaria con un booleano volatile; los efectos suenan en hilos aparte para no frenar los 60 FPS."),
    ])
    sb_m1 = sb_tabla([
        ("00:45 – 01:15", "Clic en la tarjeta Modo 1. Arrastrar y soltar con el Rifle <code>[1]</code> a un caminante.", "<code>click</code> → <code>disparo_rifle</code> → <code>impacto</code>", "El rifle es una subclase de Arma; su atacar() lanza una ráfaga de tres proyectiles. Esto es polimorfismo por sobreescritura."),
        ("01:15 – 01:40", "Apuntar a la cabeza de un zombie y disparar con el Revólver <code>[3]</code>.", "<code>disparo_revolver</code> + texto ¡CRÍTICO!", "Si la bala entra en el 32 % superior de la caja es headshot y se usa la sobrecarga de calcularDano con multiplicador crítico."),
        ("01:40 – 02:05", "Cambiar a granadas <code>[2]</code>, lanzar al grupo; luego <code>[4]</code> Katana de cerca.", "<code>lanzagranadas</code> → <code>explosion</code> (pantalla tiembla) → <code>katana</code>", "La explosión aplica daño en área con radioExplosion 145 y activa el screen shake: un translate aleatorio que decae 38 píxeles por segundo."),
        ("02:05 – 02:20", "Pulsar <code>[Q]</code> para curar.", "<code>suministro</code> (arpegio do-mi-sol)", "Q consume un botiquín del Inventario compartido; Suministro.consumirUno() impide que la cantidad sea negativa: encapsulamiento."),
    ])
    sb_m2 = sb_tabla([
        ("02:20 – 02:40", "Pulsar <code>F2</code>. Señalar el indicador de viento y usar <code>A/D</code> para panear.", "<code>click</code>", "Cambiamos de modo sin perder armas: el mismo Inventario fue inyectado en los tres modos. Eso es agregación débil."),
        ("02:40 – 03:10", "Seleccionar 100 % en la barra, apuntar con el cursor y pulsar <code>X</code> con el LanzaGranadas.", "<code>lanzagranadas</code> → <code>explosion</code> / <code>impacto</code>", "La cámara sigue a la granada con interpolación lineal y el fondo se mueve por capas a distintas velocidades: parallax."),
        ("03:10 – 03:40", "Esperar el turno de la IA y mostrar cómo cae un soldado aliado.", "disparo de la IA → <code>impacto</code>", "Cada escuadrón es un solo objeto Batallon con 320 de vida; sus cuatro MiembroEscuadron son una clase privada interna: composición fuerte. Al bajar del 75 % cae uno."),
        ("03:40 – 04:00", "(Si termina) mostrar FIN_DUELO y <code>ENTER</code>.", "<code>victoria</code> o <code>derrota</code>", "La IA simula 154 trayectorias antes de disparar y su error se reduce en cada turno: al sexto ya es casi perfecta."),
    ])
    sb_m3 = sb_tabla([
        ("04:00 – 04:20", "Pulsar <code>F3</code>. Con <code>[C]</code> alternar 5 %; pulsar <code>X</code>; luego 100 % y <code>X</code>.", "disparo del arma activa + <code>impacto</code> en el blanco", "La misma fórmula de velocidad inicial con p = 0.05 da un tiro corto y con p = 1.0 uno largo; la guía punteada usa exactamente la misma ecuación."),
        ("04:20 – 04:40", "Mantener <code>X</code> presionada y mostrar la barra de carga.", "—", "Tras 0.18 segundos la potencia sube de 5 a 100 % en 1.05 segundos."),
        ("04:40 – 05:00", "Comprar un suministro con botín y volver al menú con <code>ESC</code>.", "<code>suministro</code> → <code>click</code>", "Cierre: cinco pilares visibles en cinco minutos —abstracción, encapsulamiento, herencia, polimorfismo y composición/agregación."),
    ])
    H.append(f"""
<section class="chapter" id="cap5">
  <div class="chapter-head"><div class="num">Capítulo 5</div><h1>Kit audiovisual de exposición</h1>
  <p>Guion para público general, storyboard minuto a minuto de la demo en vivo, banco de preguntas difíciles y checklist de ensayo.</p></div>
  <h2>5.1 Guion nivel 1 — audiencia general (3 minutos)</h2>
  <table><tr><th style="width:15%">Tiempo</th><th style="width:28%">Analogía visual</th><th>Qué decir</th></tr>
  <tr><td>0:00 – 0:40</td><td>🎯 + 🧟 Bowmasters × The Walking Dead</td><td class="say">“Imaginen unir la puntería con trayectorias curvas de Bowmasters con el mundo de supervivencia de The Walking Dead. Todo lo que ven —edificios, explosiones, sonidos— lo dibuja y sintetiza el propio código en Java, sin imágenes ni audios externos.”</td></tr>
  <tr><td>0:40 – 1:20</td><td>🎼 Director de orquesta</td><td class="say">“WalkingBowmastersPOO es el director: 60 veces por segundo escucha el teclado y el ratón y le dice al modo activo ‘actualízate’ y ‘dibújate’. No sabe qué modo es; sólo sabe que todos cumplen el mismo contrato.”</td></tr>
  <tr><td>1:20 – 2:00</td><td>🎒 Mochila de campamento</td><td class="say">“El Inventario es una mochila compartida: 4 armas, botiquines, munición y botín. No pertenece a ningún personaje; por eso, si pasan del Modo 1 al 2 o al 3, la mochila los acompaña.”</td></tr>
  <tr><td>2:00 – 2:40</td><td>🪖 Escuadrón como un solo equipo</td><td class="say">“En el duelo ven 4 soldados por bando, pero en el código son un solo objeto Batallon con una vida total. Al 75, 50 y 25 % va cayendo un soldado: los soldados no existen fuera de su escuadrón.”</td></tr>
  <tr><td>2:40 – 3:00</td><td>🏹 Física real</td><td class="say">“Cada arma tiene su propia gravedad, y el viento empuja los proyectiles. La tecla X dispara al 5 % para un tiro corto o al 100 % para cruzar el mapa.”</td></tr></table>
  <h2>5.2 Storyboard audiovisual de la demo en vivo (5 minutos)</h2>
  {img(D_SB / 'sb3_ui.png', 'Mapa UI', 'Storyboard 3 — Mapa de navegación con las coordenadas reales de los Rectangle del código: menú con hover y cursor, barra superior [MENÚ | F1 | F2 | F3], selector [X: 5% | 100%], tarjetas [1-4] y [Q/E/R].')}
  <h3>Menú principal</h3>{sb_menu}
  <h3>Modo 1 — ModoSupervivenciaHordas</h3>{sb_m1}
  <h3>Modo 2 — ModoDueloBatallones</h3>{sb_m2}
  <h3>Modo 3 — ModoArmeriaCampoTiro</h3>{sb_m3}
  <div class="card violet"><h4>Plan B si algo falla en vivo</h4><p>Sin audio en el equipo del aula: <code>reproducir()</code> captura la excepción y el juego sigue
  (díganlo: “el audio está protegido con try/catch para equipos sin tarjeta de sonido”) y reproduzcan los <code>.wav</code> desde este dossier.
  Si el modo duelo se alarga, <code>F3</code> lleva directo a la armería.</p></div>
  <h2>5.3 Banco de 10 preguntas difíciles del profesor</h2>
  {q_html}
  <h2>5.4 Checklist de ensayo pre-exposición</h2>
  <div class="grid2">
  <div><h4>Técnico (la noche anterior)</h4><ul class="check">
   <li>Compilar desde la raíz: <code>javac WalkingBowmastersPOO.java armas/*.java audio/*.java efectos/*.java entidades/*.java escenario/*.java interfaces/*.java inventario/*.java modos/*.java util/*.java</code></li>
   <li>Ejecutar: <code>java WalkingBowmastersPOO</code> sin errores en consola</li>
   <li>Sonido: hover del menú audible; <code>[M]</code> silencia y reactiva</li>
   <li>Tecla <code>X</code> al <b>5 %</b>: tiro corto visible en el Modo 3</li>
   <li>Tecla <code>X</code> al <b>100 %</b>: tiro largo; <code>[C]</code> alterna; mantener <code>X</code> carga</li>
   <li>Acceso a Modo 1, 2 y 3 por clic, por <code>1/2/3</code> y por <code>F1/F2/F3</code></li>
   <li>Redimensionar la ventana y comprobar que el clic sigue acertando</li>
   <li>Proyector a 1280×720 o superior; volumen del aula probado</li></ul></div>
  <div><h4>Exposición (el día)</h4><ul class="check">
   <li>Tener abiertos en el IDE: <code>Arma.java</code>, <code>Batallon.java</code>, <code>Combatiente.java</code>, <code>WalkingBowmastersPOO.java</code></li>
   <li>Ensayar el guion de 3 min con cronómetro (máx. 3:15)</li>
   <li>Ensayar la demo de 5 min siguiendo el storyboard</li>
   <li>Repartir roles: narrador / operador del teclado / respuesta a preguntas</li>
   <li>Cada expositor responde en voz alta al menos 3 preguntas del banco</li>
   <li>Saber señalar en el diagrama UML: interfaz, abstracta, composición, agregación</li>
   <li>Escuchar <code>00_todos_los_efectos_en_orden.wav</code> e identificar los 11 sonidos</li>
   <li>Repositorio accesible por el QR de la portada</li></ul></div>
  </div>
  <div class="card dark" style="margin-top:6mm"><h3>Frase de cierre</h3><p>“The Walking Bowmasters demuestra que la POO no es teoría: cada pilar tiene un lugar exacto en el código,
  y gracias a esa arquitectura pudimos añadir tres modos, cuatro armas y once sonidos sin reescribir el motor.”</p></div>
</section>
""")
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Guía de Estudio Audiovisual — The Walking Bowmasters</title>
<style>{CSS}</style></head><body>
{''.join(H)}
<script src="vendor/mermaid.min.js"></script>
<script>
window.__mermaidErrores = []; window.__mermaidListo = false;
(async () => {{
  mermaid.initialize({{ startOnLoad:false, securityLevel:'loose', theme:'base',
    fontFamily:'Inter, Segoe UI, sans-serif',
    themeVariables:{{ primaryColor:'#f4f3ef', primaryBorderColor:'#3d3c39', primaryTextColor:'#0b0b0b', lineColor:'#52514e',
      secondaryColor:'#e8f0fb', tertiaryColor:'#fdf0e9', fontSize:'13px', clusterBkg:'#fbfaf7', clusterBorder:'#cfcdc6' }},
    flowchart:{{ htmlLabels:true, curve:'basis', padding:10 }}, class:{{ htmlLabels:false }}, maxTextSize: 200000 }});
  await document.fonts.ready;
  let n = 0;
  for (const box of document.querySelectorAll('.mermaid-box')) {{
    const src = box.querySelector('.mermaid-src').textContent;
    try {{ const r = await mermaid.render('mmd' + (n++), src); box.innerHTML = r.svg; }}
    catch (e) {{ window.__mermaidErrores.push(box.dataset.nombre + ': ' + e.message); }}
  }}
  window.__mermaidListo = true;
}})();
</script></body></html>"""


# ---------------------------------------------------------------------------
# 8. Render a PDF (Playwright + Chromium/Edge) y post-proceso
# ---------------------------------------------------------------------------
def descargar_mermaid():
    destino = D_VENDOR / "mermaid.min.js"
    if not destino.exists():
        log("descargando mermaid 11.4.1 ...")
        urllib.request.urlretrieve(MERMAID_URL, destino)
    return destino


def render_pdf(html_path: Path):
    from playwright.sync_api import sync_playwright
    header = ('<div style="font-family:Segoe UI,sans-serif;font-size:7.5px;color:#8a8984;width:100%;padding:0 15mm;'
              'display:flex;justify-content:space-between"><span>THE WALKING BOWMASTERS · Guía de Estudio Audiovisual</span>'
              '<span>Lógica de Programación II · Edición POO Modular</span></div>')
    footer = ('<div style="font-family:Segoe UI,sans-serif;font-size:7.5px;color:#8a8984;width:100%;padding:0 15mm;'
              'display:flex;justify-content:space-between"><span>github.com/JOHN-RAVEN-CROWNSON-2008/ProyectoLogicaDeProgramacion-II</span>'
              '<span>Página <b class="pageNumber"></b> / <span class="totalPages"></span></span></div>')
    with sync_playwright() as p:
        try:
            nav = p.chromium.launch(channel="msedge")
        except Exception:
            try:
                nav = p.chromium.launch(channel="chrome")
            except Exception:
                nav = p.chromium.launch()
        pag = nav.new_page()
        pag.goto(html_path.as_uri(), wait_until="networkidle")
        pag.wait_for_function("window.__mermaidListo === true", timeout=120_000)
        errores = pag.evaluate("window.__mermaidErrores")
        if errores:
            print("  ! Errores de Mermaid:", *errores, sep="\n    ")
        # exportar los SVG de Mermaid como archivos independientes
        for nombre, svg in pag.evaluate("""[...document.querySelectorAll('.mermaid-box')]
              .map(b => [b.dataset.nombre, b.querySelector('svg') ? b.querySelector('svg').outerHTML : ''])"""):
            if svg:
                (D_DIAG / f"{nombre}.svg").write_text(svg, encoding="utf-8")
        pag.emulate_media(media="print")
        pag.pdf(path=str(SALIDA_PDF), prefer_css_page_size=True, print_background=True,
                display_header_footer=True, header_template=header, footer_template=footer,
                outline=True, tagged=True)
        nav.close()
    log(f"PDF escrito: {SALIDA_PDF.name}")
    return errores


def postprocesar_y_validar():
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, DictionaryObject, TextStringObject
    lector = PdfReader(str(SALIDA_PDF))
    escritor = PdfWriter(clone_from=lector)
    base = REC.as_uri()
    uris, locales, internos = set(), 0, 0
    for pagina in escritor.pages:
        for ref in pagina.get("/Annots", []) or []:
            an = ref.get_object()
            acc = an.get("/A")
            if acc is None:
                if "/Dest" in an:
                    internos += 1
                continue
            acc = acc.get_object()
            if acc.get("/S") == "/URI":
                u = str(acc["/URI"])
                if u.startswith("file:"):
                    rel = "estudio_audiovisual/" + urllib.request.url2pathname(u[len(base) + 1:]).replace("\\", "/") \
                        if u.startswith(base) else u
                    rel = rel.lstrip("/")
                    an[NameObject("/A")] = DictionaryObject({
                        NameObject("/S"): NameObject("/Launch"),
                        NameObject("/F"): DictionaryObject({NameObject("/Type"): NameObject("/Filespec"),
                                                            NameObject("/F"): TextStringObject(rel),
                                                            NameObject("/UF"): TextStringObject(rel)}),
                    })
                    locales += 1
                else:
                    uris.add(u)
            elif acc.get("/S") == "/GoTo":
                internos += 1
    escritor.add_metadata({"/Title": "Guía de Estudio Audiovisual — The Walking Bowmasters (Edición POO Modular)",
                           "/Subject": "Lógica de Programación II · Dossier de exposición",
                           "/Keywords": "POO, Java, Swing, UML, balística, GestorSonido"})
    with open(SALIDA_PDF, "wb") as fh:
        escritor.write(fh)
    lector = PdfReader(str(SALIDA_PDF))
    n_pag = len(lector.pages)

    def contar(o):
        return sum(1 + contar(x) if isinstance(x, list) else 1 for x in o) if isinstance(o, list) else 0
    marcadores = contar(lector.outline)
    tamaños = sorted({(round(float(p.mediabox.width)), round(float(p.mediabox.height))) for p in lector.pages})
    # comprobar enlaces web (HEAD)
    estados = {}
    for u in sorted(uris):
        base_u = u.split("#")[0]
        if base_u in estados:
            continue
        try:
            r = urllib.request.urlopen(urllib.request.Request(base_u, method="HEAD",
                                                              headers={"User-Agent": "pdf-link-check"}), timeout=10)
            estados[base_u] = r.status
        except Exception as e:  # noqa
            estados[base_u] = getattr(e, "code", type(e).__name__)
    return {"paginas": n_pag, "marcadores": marcadores, "enlaces_web": len(uris), "enlaces_locales": locales,
            "enlaces_internos": internos, "tamaños_pagina_pt": tamaños, "estado_urls": estados}


def main():
    print("Generando dossier de estudio ...")
    for d in (D_GRAF, D_AUDIO, D_DIAG, D_SB, D_QR, D_VENDOR):
        d.mkdir(parents=True, exist_ok=True)
    info, deps, ciclos = analizar_codigo()
    log(f"{len(info)} archivos .java analizados · ciclos de paquetes: {ciclos or 'ninguno'}")
    señales = generar_audio()
    estilo_mpl()
    grafico_balistica()
    datos_ia = grafico_ia()
    grafico_composicion()
    grafico_audio(señales)
    storyboard_parallax(); storyboard_hitboxes(); storyboard_ui()
    generar_qr()
    descargar_mermaid()
    html_path = REC / "guia_estudio.html"
    html_path.write_text(construir_html(info, deps, ciclos, datos_ia), encoding="utf-8")
    log(f"HTML maquetado: {html_path.relative_to(RAIZ)}")
    errores = render_pdf(html_path)
    rep = postprocesar_y_validar()
    print("\nVALIDACION")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    if errores:
        print("  ADVERTENCIA: hubo diagramas Mermaid con errores")
        sys.exit(1)


if __name__ == "__main__":
    main()
