# -*- coding: utf-8 -*-
"""
generar_presentacion.py
=======================
Genera `Presentacion_The_Walking_Bowmasters_POO.pptx` (16:9, 14 diapositivas)
a partir de GUIA_ARQUITECTURA_Y_EXPOSICION.md y de los valores reales del
codigo Java del proyecto (armas/, entidades/, audio/, modos/, util/).

Dependencias:  pip install python-pptx matplotlib numpy pillow
Ejecucion:     python generar_presentacion.py

Recursos graficos (todos generados por este script, en assets_presentacion/):
  * matplotlib + numpy (300 DPI, fondo transparente): trayectorias balisticas,
    degradacion del Batallon, formas de onda PCM de GestorSonido.
  * Diagramas UML/arquitectura: si existe Graphviz (`dot`) en el PATH se usa
    para los diagramas declarados en DOT; si no existe (o falla), se dibujan de
    forma vectorial nativa con matplotlib. La generacion nunca depende de
    herramientas externas.
  * Pillow: mockups estilo Graphics2D (cielo crepuscular con Parallax,
    siluetas, HUD con selector [X: 5% | 100%] y barras de vida interpoladas).
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE  # noqa: E402
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN  # noqa: E402
from pptx.oxml.ns import qn  # noqa: E402
from pptx.util import Emu, Inches, Pt  # noqa: E402
from lxml import etree  # noqa: E402

# =============================================================================
# RUTAS
# =============================================================================
BASE = Path(__file__).resolve().parent
ASSETS = BASE / "assets_presentacion"
SALIDA = BASE / "Presentacion_The_Walking_Bowmasters_POO.pptx"
GUIA = BASE / "GUIA_ARQUITECTURA_Y_EXPOSICION.md"

# =============================================================================
# IDENTIDAD VISUAL
# =============================================================================
PAL = {
    "bg": "0E1118",
    "card": "181E2A",
    "card2": "11151E",
    "borde": "364156",
    "oro": "EBB95F",
    "rojo": "D9443A",
    "cian": "4FC3F7",
    "verde": "57C785",
    "txt": "F2F4F8",
    "txt2": "A8B3C7",
    "gris": "6B778C",
}
FUENTE = "Segoe UI"
MONO = "Consolas"

SLIDE_W, SLIDE_H = 13.333, 7.5
MARGEN = 0.6
CONT_X = MARGEN
CONT_W = SLIDE_W - 2 * MARGEN  # 12.133
CONT_Y = 1.72                  # inicio del area de contenido
CONT_BOTTOM = 6.45             # fin del area de contenido (pie en 6.62-6.90)
TOTAL = 14
PROYECTO = "THE WALKING BOWMASTERS · Edición POO Modular"


def hx(c: str) -> str:
    return "#" + PAL.get(c, c)


def rgb(c: str) -> RGBColor:
    return RGBColor.from_string(PAL.get(c, c))


# =============================================================================
# DATOS REALES DEL PROYECTO (verificados contra el codigo fuente)
# =============================================================================
GRAVEDAD_BASE = 540.0          # util/ConstantesJuego.java
V_MIN = 175.0                  # armas/Arma.calcularVelocidadInicial
ARMAS = [                      # nombre, factorGravedad, velocidadBase, velocidadExtra, color
    ("RifleAsalto", 0.45, 460.0, 640.0, "oro"),
    ("Revolver", 0.55, 410.0, 620.0, "txt"),
    ("EspadaKatana", 0.90, 310.0, 570.0, "cian"),
    ("LanzaGranadas", 1.00, 300.0, 690.0, "rojo"),
]
VIENTO_SNAPSHOT = -48.5        # vientoActual del diagrama de objetos (Modo 2)
ALTURA_BOCA = 56.0             # yOrigen = y - 56 en Batallon.dispararEnUnisono
RADIO_EXPLOSION = 145.0        # LanzaGranadas -> Proyectil(..., 145.0, ...)
SAMPLE_RATE = 44100            # audio/GestorSonido.SAMPLE_RATE


def velocidad_inicial(potencia: float, v_base: float, v_extra: float) -> float:
    """Replica exacta de Arma.calcularVelocidadInicial(double potencia)."""
    p = min(1.0, max(0.05, potencia))
    v_max = v_base + v_extra
    return V_MIN + p * (v_max - V_MIN)


# =============================================================================
# MATPLOTLIB: ESTILO COMUN
# =============================================================================
plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"],
    "font.size": 9,
    "text.color": hx("txt"),
    "axes.labelcolor": hx("txt2"),
    "axes.edgecolor": hx("borde"),
    "xtick.color": hx("txt2"),
    "ytick.color": hx("txt2"),
    "axes.facecolor": "none",
    "savefig.transparent": True,
})
MONO_MPL = ["Consolas", "DejaVu Sans Mono"]


def guardar_fig(fig, nombre: str) -> Path:
    ruta = ASSETS / nombre
    fig.savefig(ruta, dpi=300, transparent=True)
    plt.close(fig)
    return ruta


# -----------------------------------------------------------------------------
# Grafica 1: trayectorias balisticas (5% vs 100%)
# -----------------------------------------------------------------------------
def simular_trayectoria(potencia, factor_g, v_base, v_extra, viento=0.0,
                        angulo_deg=45.0, dt=1 / 240):
    """Integra Proyectil.actualizarConViento con eje Y hacia arriba (ver nota)."""
    v0 = velocidad_inicial(potencia, v_base, v_extra)
    ang = math.radians(angulo_deg)
    vx, vy = v0 * math.cos(ang), v0 * math.sin(ang)
    x, y = 0.0, ALTURA_BOCA
    xs, ys = [x], [y]
    while y >= 0.0 and len(xs) < 200000:
        vx += viento * dt
        vy -= GRAVEDAD_BASE * factor_g * dt
        x += vx * dt
        y += vy * dt
        xs.append(x)
        ys.append(max(y, 0.0))
    return np.array(xs), np.array(ys)


def grafica_trayectorias() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(7.45, 4.7))
    fig.subplots_adjust(left=0.085, right=0.985, top=0.80, bottom=0.12, wspace=0.24)
    paneles = [(0.05, "Tecla X al 5 %  (tiro corto)"), (1.00, "Tecla X al 100 %  (tiro largo)")]
    for ax, (pot, titulo) in zip(axes, paneles):
        for nombre, g, vb, ve, col in ARMAS:
            xs, ys = simular_trayectoria(pot, g, vb, ve)
            ax.plot(xs, ys, color=hx(col), lw=1.9, solid_capstyle="round",
                    label=f"{nombre}  (g = {g:.2f})")
            ax.plot(xs[-1], 0, "o", ms=3.5, color=hx(col))
        # LanzaGranadas con viento del snapshot (solo Modo 2 aplica viento)
        xs_w, ys_w = simular_trayectoria(pot, 1.0, 300.0, 690.0, viento=VIENTO_SNAPSHOT)
        ax.plot(xs_w, ys_w, color=hx("rojo"), lw=1.2, ls=(0, (3, 2)), alpha=0.85,
                label=f"LanzaGranadas con viento {VIENTO_SNAPSHOT} px/s²")
        if pot == 1.0:
            xs_g, _ = simular_trayectoria(pot, 1.0, 300.0, 690.0)
            xi = xs_g[-1]
            ax.axvspan(xi - RADIO_EXPLOSION, xi + RADIO_EXPLOSION, ymax=0.10,
                       color=hx("rojo"), alpha=0.28, lw=0)
            ax.annotate("AoE 145 px", xy=(xi + 60, 30), xytext=(xi + 420, 260),
                        color=hx("rojo"), fontsize=8,
                        arrowprops=dict(arrowstyle="-", color=hx("rojo"), lw=0.8))
        ax.set_title(titulo, color=hx("cian"), fontsize=10.5, fontweight="bold", loc="left", pad=6)
        ax.set_xlabel("x (px del mundo virtual)", fontsize=8.5)
        ax.grid(True, color=hx("borde"), lw=0.5, alpha=0.6)
        ax.set_ylim(bottom=0)
        ax.set_xlim(left=0)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(labelsize=7.5)
    axes[0].set_ylabel("altura sobre Y_SUELO (px)", fontsize=8.5)
    h, l = axes[1].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=3, frameon=False, fontsize=7.6,
               bbox_to_anchor=(0.5, 1.0), handlelength=2.2, columnspacing=1.2)
    return guardar_fig(fig, "g1_trayectorias.png")


# -----------------------------------------------------------------------------
# Grafica 2: degradacion del Batallon (vivos = ceil(pct * 4))
# -----------------------------------------------------------------------------
def miembros_vivos(vida: float, vida_max: float = 320, total: int = 4) -> int:
    """Replica de Batallon.actualizarMiembrosSegunVida()."""
    if vida <= 0:
        return 0
    return max(0, min(total, math.ceil((vida / vida_max) * total)))


def grafica_batallon() -> Path:
    fig, ax = plt.subplots(figsize=(5.75, 2.85))
    fig.subplots_adjust(left=0.10, right=0.98, top=0.93, bottom=0.20)
    vidas = np.linspace(320, 0, 1601)
    vivos = np.array([miembros_vivos(v) for v in vidas])
    ax.fill_between(vidas, vivos, step="pre", color=hx("verde"), alpha=0.18, lw=0)
    ax.step(vidas, vivos, where="pre", color=hx("verde"), lw=2.2)
    hitos = [(320, 4, "100 %"), (240, 3, "75 %"), (160, 2, "50 %"), (80, 1, "25 %"), (0, 0, "0 %")]
    for v, n, pct in hitos:
        col = hx("rojo") if n == 0 else hx("oro")
        ax.plot(v, n, "o", ms=6, color=col, zorder=5)
        derecha = v == 0
        ax.annotate(f"{v} HP · {pct}\n{n} vivos" if n else f"{v} HP\ndestruido",
                    xy=(v, n), xytext=((-8, 8) if derecha else (8, 6)), textcoords="offset points",
                    ha="right" if derecha else "left", va="bottom", fontsize=7.6, color=hx("txt"))
    ax.set_xlim(335, -15)
    ax.set_ylim(-0.3, 5.6)
    ax.set_yticks([0, 1, 2, 3, 4])
    ax.set_xticks([320, 240, 160, 80, 0])
    ax.set_xlabel("vida global del Batallon (vidaMaxima = 320)", fontsize=8.5)
    ax.set_ylabel("MiembroEscuadron vivos", fontsize=8.5)
    ax.grid(True, axis="y", color=hx("borde"), lw=0.5, alpha=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8)
    return guardar_fig(fig, "g2_batallon.png")


# -----------------------------------------------------------------------------
# Grafica 3: formas de onda PCM (replica de GestorSonido)
# -----------------------------------------------------------------------------
def sintetizar_disparo(dur, f_ini, f_fin, volumen, peso_ruido, seed):
    """Replica numerica de GestorSonido.sintetizarDisparo (ruido: numpy, no java.util.Random)."""
    n = max(1, int(SAMPLE_RATE * dur))
    rng = np.random.default_rng(seed)
    t = np.arange(n) / n
    env = (1.0 - t) ** 1.9
    freq = f_ini * np.power(max(0.05, f_fin / f_ini), t)
    fase = np.cumsum(2 * np.pi * freq / SAMPLE_RATE)
    tono = np.sin(fase)
    ruido = rng.uniform(-1, 1, n)
    filtro = np.empty(n)
    acc = 0.0
    for i in range(n):
        acc = acc * 0.45 + ruido[i] * 0.55
        filtro[i] = acc
    mezcla = tono * (1 - peso_ruido) + filtro * peso_ruido
    return np.clip(mezcla * env * volumen, -1, 1)


def sintetizar_barrido(f_ini, f_fin, dur, volumen, metalico, seed):
    """Replica numerica de GestorSonido.sintetizarBarrido."""
    n = max(1, int(SAMPLE_RATE * dur))
    rng = np.random.default_rng(seed)
    t = np.arange(n) / n
    freq = f_ini + (f_fin - f_ini) * t
    env = np.sin(np.pi * np.minimum(1.0, t * 8.0)) * (1.0 - t)
    fase = np.cumsum(2 * np.pi * freq / SAMPLE_RATE)
    val = np.sin(fase)
    if metalico:
        fase2 = np.cumsum(2 * np.pi * freq * 2.41 / SAMPLE_RATE)
        val = 0.55 * val + 0.30 * np.sin(fase2) + 0.15 * rng.uniform(-1, 1, n)
    return np.clip(val * env * volumen, -1, 1)


def grafica_ondas() -> Path:
    efectos = [
        ('"disparo_rifle"', sintetizar_disparo(0.11, 220, 75, 0.34, 0.65, 102),
         "sintetizarDisparo(0.11, 220, 75, 0.34, 0.65)", "oro"),
        ('"explosion"', sintetizar_disparo(0.46, 95, 28, 0.55, 0.80, 105),
         "sintetizarDisparo(0.46, 95, 28, 0.55, 0.80)", "rojo"),
        ('"katana"', sintetizar_barrido(1350, 2900, 0.15, 0.28, True, 106),
         "sintetizarBarrido(1350, 2900, 0.15, 0.28, true)", "cian"),
    ]
    fig, axes = plt.subplots(3, 1, figsize=(5.75, 3.45), sharex=True)
    fig.subplots_adjust(left=0.035, right=0.985, top=0.90, bottom=0.13, hspace=0.75)
    for ax, (clave, onda, firma, col) in zip(axes, efectos):
        t_ms = np.arange(len(onda)) / SAMPLE_RATE * 1000
        ax.plot(t_ms, onda, color=hx(col), lw=0.35)
        ax.set_ylim(-0.6, 0.6)
        ax.set_yticks([])
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.text(0.0, 1.10, clave, transform=ax.transAxes, fontsize=8.6,
                fontweight="bold", color=hx(col), family=MONO_MPL, va="bottom")
        ax.text(1.0, 1.10, f"{firma}  ·  {len(onda):,} muestras".replace(",", "."),
                transform=ax.transAxes, fontsize=7.0, color=hx("txt2"),
                family=MONO_MPL, va="bottom", ha="right")
        ax.tick_params(labelsize=7.5)
    axes[-1].set_xlabel("tiempo (ms) · PCM 16 bits mono a 44100 Hz", fontsize=8)
    axes[-1].set_xlim(0, 470)
    return guardar_fig(fig, "g3_ondas_pcm.png")


# =============================================================================
# DIAGRAMAS (Graphviz si existe; si no, dibujo vectorial nativo en matplotlib)
# =============================================================================
def intentar_graphviz(dot_src: str, nombre: str) -> Path | None:
    """Renderiza DOT a PNG 300 DPI transparente si `dot` esta disponible."""
    dot = shutil.which("dot")
    if not dot:
        return None
    ruta = ASSETS / nombre
    try:
        subprocess.run([dot, "-Tpng", "-Gdpi=300", "-Gbgcolor=transparent", "-o", str(ruta)],
                       input=dot_src.encode("utf-8"), check=True, timeout=60,
                       capture_output=True)
        return ruta if ruta.exists() else None
    except (subprocess.SubprocessError, OSError):
        return None


def lienzo(w_in: float, h_in: float):
    """Figura cuyo sistema de coordenadas de datos coincide con pulgadas."""
    fig = plt.figure(figsize=(w_in, h_in))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w_in)
    ax.set_ylim(0, h_in)
    ax.axis("off")
    return fig, ax


def caja(ax, x, y, w, h, color="borde", fill="card", lw=1.3, ls="-", radio=0.06, z=2):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radio}",
                       fc=hx(fill) if fill else "none", ec=hx(color), lw=lw, ls=ls, zorder=z)
    ax.add_patch(p)
    return p


def flecha(ax, p1, p2, color="txt2", estilo="-|>", lw=1.1, ls="-", hueca=False, z=3):
    kw = dict(arrowstyle=estilo, mutation_scale=11, color=hx(color), lw=lw, ls=ls, zorder=z,
              shrinkA=0, shrinkB=0)
    a = FancyArrowPatch(p1, p2, **kw)
    if hueca:
        a.set_facecolor(hx("bg"))
    ax.add_patch(a)


def rombo(ax, punto, direccion, relleno, color, tam=0.11):
    """Rombo UML (composicion relleno / agregacion hueco) apuntando en `direccion`."""
    dx, dy = direccion
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    px, py = -uy, ux
    x0, y0 = punto
    pts = [(x0, y0), (x0 + ux * tam + px * tam * 0.45, y0 + uy * tam + py * tam * 0.45),
           (x0 + ux * tam * 2, y0 + uy * tam * 2),
           (x0 + ux * tam - px * tam * 0.45, y0 + uy * tam - py * tam * 0.45)]
    ax.add_patch(Polygon(pts, closed=True, fc=hx(color) if relleno else hx("bg"),
                         ec=hx(color), lw=1.1, zorder=6))
    return (x0 + ux * tam * 2, y0 + uy * tam * 2)


def linea(ax, pts, color="txt2", lw=1.1, ls="-", z=3):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=hx(color), lw=lw, ls=ls, zorder=z, solid_capstyle="round")


# -----------------------------------------------------------------------------
# Diagrama A: arquitectura modular de 9 paquetes + clase raiz
# -----------------------------------------------------------------------------
PAQUETES = {
    "raiz": ("WalkingBowmastersPOO.java", "JPanel + Timer(16, this) · EstadoPantalla", "oro"),
    "modos": ("modos/  ·  4", "BaseModoJuego · Hordas · Duelo · Armeria", "cian"),
    "entidades": ("entidades/  ·  11", "Combatiente · Batallon · Zombie*", "rojo"),
    "armas": ("armas/  ·  5", "Arma + 4 armas", "rojo"),
    "inventario": ("inventario/  ·  3", "Inventario · Suministro", "verde"),
    "audio": ("audio/  ·  1", "GestorSonido (PCM)", "txt2"),
    "efectos": ("efectos/  ·  3", "Particula · OndaExpansiva · TextoFlotante", "txt2"),
    "escenario": ("escenario/  ·  2", "EscenarioApocaliptico · ObstaculoTerreno", "txt2"),
    "interfaces": ("interfaces/  ·  3", "Renderizable · Atacable · ModoJuego", "cian"),
    "util": ("util/  ·  1", "ConstantesJuego (GRAVEDAD_BASE, Y_SUELO)", "txt2"),
}

DOT_ARQUITECTURA = """digraph G {
  rankdir=TB; nodesep=0.35; ranksep=0.45; bgcolor="transparent";
  node [shape=box, style="rounded,filled", fillcolor="#181E2A", color="#364156",
        fontname="Segoe UI", fontcolor="#F2F4F8", fontsize=11];
  edge [color="#A8B3C7", arrowsize=0.7];
  raiz [label="WalkingBowmastersPOO.java", color="#EBB95F"];
  modos [label="modos/ (4)", color="#4FC3F7"];
  subgraph cluster_dom { label="Nucleo de dominio"; fontcolor="#A8B3C7"; color="#364156"; style=dashed;
    entidades [label="entidades/ (11)", color="#D9443A"]; armas [label="armas/ (5)", color="#D9443A"];
    inventario [label="inventario/ (3)", color="#57C785"]; }
  audio [label="audio/ (1)"]; efectos [label="efectos/ (3)"]; escenario [label="escenario/ (2)"];
  interfaces [label="interfaces/ (3)", color="#4FC3F7"]; util [label="util/ (1)"];
  raiz -> modos; raiz -> inventario; raiz -> audio; raiz -> escenario;
  modos -> entidades; modos -> armas; modos -> efectos;
  entidades -> interfaces; entidades -> util; armas -> util; efectos -> util; escenario -> util;
}"""


def diagrama_arquitectura() -> Path:
    W, H = 8.05, 4.73
    fig, ax = lienzo(W, H)
    pos = {}

    def nodo(clave, x, y, w, h=0.62):
        titulo, sub, col = PAQUETES[clave]
        caja(ax, x, y, w, h, color=col, lw=1.5)
        ax.text(x + 0.14, y + h - 0.2, titulo, fontsize=9.6, fontweight="bold",
                color=hx(col if col != "txt2" else "txt"), family=MONO_MPL, va="center")
        ax.text(x + 0.14, y + 0.18, sub, fontsize=7.4, color=hx("txt2"), va="center")
        pos[clave] = (x, y, w, h)

    # Capa 0: raiz
    nodo("raiz", 2.45, 4.02, 3.15)
    # Capa 1: orquestacion
    nodo("modos", 0.15, 2.98, 3.15)
    # Servicios laterales
    nodo("audio", 5.55, 2.98, 2.35)
    # Capa 2: nucleo de dominio (contenedor)
    caja(ax, 0.05, 1.27, 5.25, 1.43, color="borde", fill=None, lw=1.0, ls=(0, (4, 3)), radio=0.1)
    ax.text(0.17, 2.55, "NÚCLEO DE DOMINIO", fontsize=7.2, color=hx("txt2"),
            fontweight="bold", va="center")
    ax.text(1.55, 2.55, "armas ↔ entidades ↔ inventario", fontsize=7.0,
            color=hx("txt2"), va="center", ha="left", family=MONO_MPL)
    nodo("entidades", 0.15, 1.40, 1.95)
    nodo("armas", 2.2, 1.40, 1.45)
    nodo("inventario", 3.75, 1.40, 1.45)
    for k in ("entidades", "armas", "inventario"):
        x, y, w, h = pos[k]
    nodo("efectos", 5.55, 1.98, 2.35)
    nodo("escenario", 5.55, 1.05, 2.35)
    # Capa 3: base
    nodo("interfaces", 0.15, 0.05, 3.0)
    nodo("util", 3.35, 0.05, 4.55)

    def borde(clave, lado, f=0.5):
        x, y, w, h = pos[clave]
        return {"b": (x + w * f, y), "t": (x + w * f, y + h),
                "l": (x, y + h * f), "r": (x + w, y + h * f)}[lado]

    c = "txt2"
    flecha(ax, borde("raiz", "b", 0.2), borde("modos", "t", 0.75), c)
    flecha(ax, borde("raiz", "b", 0.85), borde("audio", "t", 0.25), c)
    linea(ax, [borde("raiz", "r", 0.5), (8.0, borde("raiz", "r")[1]), (8.0, 1.36)], c)
    flecha(ax, (8.0, 1.36), (borde("escenario", "r")[0], 1.36), c)
    flecha(ax, borde("raiz", "b", 0.62), borde("inventario", "t", 0.5), "verde", lw=1.3)
    ax.text(borde("raiz", "b", 0.62)[0] + 0.07, 3.68, "crea inventarioCompartido",
            fontsize=6.6, color=hx("verde"), va="center")
    flecha(ax, borde("modos", "b", 0.3), (0.62, 1.27 + 1.43), c)
    flecha(ax, borde("modos", "r", 0.5), borde("audio", "l", 0.5), c)
    linea(ax, [(3.3, 3.12), (5.1, 3.12), (5.1, borde("efectos", "l")[1])], c)
    flecha(ax, (5.1, borde("efectos", "l")[1]), borde("efectos", "l"), c)
    flecha(ax, (1.1, 1.27), borde("interfaces", "t", 0.32), c)
    flecha(ax, (4.4, 1.27), borde("util", "t", 0.23), c)
    flecha(ax, borde("escenario", "b", 0.5), borde("util", "t", 0.79), c)
    ax.text(W - 0.05, H - 0.1, "→  dependencia (import)", fontsize=7, color=hx("txt2"),
            ha="right", va="top")
    return guardar_fig(fig, "d1_arquitectura.png")


# -----------------------------------------------------------------------------
# Diagrama B: arboles de herencia (<|-- y <|..)
# -----------------------------------------------------------------------------
def nodo_clase(ax, cx, cy, nombre, estereo=None, col="borde", w=None, fs=8.6):
    w = w or max(1.05, 0.072 * len(nombre) + 0.28)
    h = 0.5 if estereo else 0.38
    caja(ax, cx - w / 2, cy - h / 2, w, h, color=col, lw=1.4)
    if estereo:
        etiqueta = estereo if estereo.startswith("«") else f"«{estereo}»"
        ax.text(cx, cy + 0.1, etiqueta, fontsize=6.4, color=hx("txt2"),
                ha="center", va="center", style="italic")
        ax.text(cx, cy - 0.09, nombre, fontsize=fs, color=hx("txt"), ha="center",
                va="center", fontweight="bold", family=MONO_MPL)
    else:
        ax.text(cx, cy, nombre, fontsize=fs, color=hx("txt"), ha="center", va="center",
                family=MONO_MPL)
    return (cx, cy, w, h)


def herencia(ax, hijo, padre, realiza=False, col="txt2", via_y=None):
    """Linea hijo -> padre con triangulo hueco UML en el padre."""
    cx, cy, w, h = hijo
    px, py, pw, ph = padre
    inicio = (cx, cy + h / 2)
    fin = (px, py - ph / 2)
    ls = (0, (3, 2)) if realiza else "-"
    if via_y is None:
        via_y = (inicio[1] + fin[1]) / 2
    linea(ax, [inicio, (cx, via_y), (px, via_y), (px, fin[1] - 0.16)], col, ls=ls)
    tri = [(px, fin[1]), (px - 0.075, fin[1] - 0.16), (px + 0.075, fin[1] - 0.16)]
    ax.add_patch(Polygon(tri, closed=True, fc=hx("bg"), ec=hx(col), lw=1.1, zorder=6))


def herencia_lateral(ax, hijos, padre, x_tronco, col="txt2"):
    """Hijos apilados verticalmente conectados a un tronco que sube al padre."""
    px, py, pw, ph = padre
    fin_y = py - ph / 2
    ys = [h[1] for h in hijos]
    y_mid = (fin_y - 0.16 + max(h[1] + h[3] / 2 for h in hijos)) / 2
    linea(ax, [(x_tronco, min(ys)), (x_tronco, y_mid), (px, y_mid), (px, fin_y - 0.16)], col)
    tri = [(px, fin_y), (px - 0.075, fin_y - 0.16), (px + 0.075, fin_y - 0.16)]
    ax.add_patch(Polygon(tri, closed=True, fc=hx("bg"), ec=hx(col), lw=1.1, zorder=6))
    for (cx, cy, w, h) in hijos:
        linea(ax, [(x_tronco, cy), (cx - w / 2, cy)], col)


def diagrama_herencia() -> Path:
    W, H = 7.2, 4.73
    fig, ax = lienzo(W, H)
    # --- Arbol 1: EntidadJuego / Combatiente ---------------------------------
    rend = nodo_clase(ax, 1.2, 4.43, "Renderizable", "interface", "cian")
    atac = nodo_clase(ax, 3.55, 4.43, "Atacable", "interface", "cian")
    ent = nodo_clase(ax, 1.2, 3.5, "EntidadJuego", "abstract", "oro")
    herencia(ax, ent, rend, realiza=True, col="cian")
    comb = nodo_clase(ax, 2.35, 2.55, "Combatiente", "abstract", "oro")
    proy = nodo_clase(ax, 0.62, 2.55, "Proyectil", None, "borde", w=1.05)
    herencia(ax, comb, ent, via_y=3.08)
    herencia(ax, proy, ent, via_y=3.08)
    # Combatiente implementa Atacable
    linea(ax, [(comb[0] + 0.45, comb[1] + comb[3] / 2), (comb[0] + 0.45, 3.85),
               (atac[0], 3.85), (atac[0], atac[1] - atac[3] / 2 - 0.16)], "cian", ls=(0, (3, 2)))
    tri = [(atac[0], atac[1] - atac[3] / 2), (atac[0] - 0.075, atac[1] - atac[3] / 2 - 0.16),
           (atac[0] + 0.075, atac[1] - atac[3] / 2 - 0.16)]
    ax.add_patch(Polygon(tri, closed=True, fc=hx("bg"), ec=hx("cian"), lw=1.1, zorder=6))
    y4 = 1.62
    sup = nodo_clase(ax, 0.62, y4, "Superviviente", None, "verde", w=1.12, fs=8.0)
    zom = nodo_clase(ax, 1.84, y4, "Zombie", "abstract", "rojo", w=1.0)
    saq = nodo_clase(ax, 3.06, y4, "SaqueadorRival", None, "rojo", w=1.24, fs=8.0)
    bat = nodo_clase(ax, 4.2, y4, "Batallon", None, "verde", w=0.92, fs=8.0)
    for hijo in (sup, zom, saq, bat):
        herencia(ax, hijo, comb, via_y=2.08)
    y5 = 0.42
    zc = nodo_clase(ax, 0.68, y5, "ZombieCaminante", None, "rojo", w=1.24, fs=7.6)
    zr = nodo_clase(ax, 2.0, y5, "ZombieCorredor", None, "rojo", w=1.2, fs=7.6)
    zb = nodo_clase(ax, 3.3, y5, "ZombieBlindado", None, "rojo", w=1.2, fs=7.6)
    for hijo in (zc, zr, zb):
        herencia(ax, hijo, zom, via_y=0.98)
    # --- Arbol 2: Arma ---------------------------------------------------------
    xa = 5.12
    arma = nodo_clase(ax, 6.1, 4.43, "Arma", "abstract", "oro", w=1.1)
    hijos = []
    for i, n in enumerate(["RifleAsalto", "LanzaGranadas", "Revolver", "EspadaKatana"]):
        hijos.append(nodo_clase(ax, 6.2, 3.68 - i * 0.4, n, None, "borde", w=1.75, fs=7.8))
    herencia_lateral(ax, hijos, arma, x_tronco=xa)
    # --- Arbol 3: ModoJuego -> BaseModoJuego -> 3 modos -------------------------
    bm = nodo_clase(ax, 6.1, 1.95, "BaseModoJuego", "«abstract» implementa ModoJuego", "oro", w=1.95)
    modos = []
    for i, n in enumerate(["ModoSupervivenciaHordas", "ModoDueloBatallones", "ModoArmeriaCampoTiro"]):
        modos.append(nodo_clase(ax, 6.2, 1.2 - i * 0.4, n, None, "borde", w=1.95, fs=7.0))
    herencia_lateral(ax, modos, bm, x_tronco=xa)
    ax.text(W - 0.03, 0.03, "△ hereda    △┄ implementa", fontsize=6.6, color=hx("txt2"),
            ha="right", va="bottom")
    return guardar_fig(fig, "d2_herencia.png")


# -----------------------------------------------------------------------------
# Diagrama C: objetos en runtime (Modo 2, duelo 1v1)
# -----------------------------------------------------------------------------
def objeto(ax, x, y_top, w, cabecera, lineas, col="borde", fs=7.2):
    lh = fs * 1.32 / 72
    h = 0.1 + (1 + len(lineas)) * lh + 0.1
    y = y_top - h
    caja(ax, x, y, w, h, color=col, lw=1.4, radio=0.05)
    ty = y_top - 0.1 - lh / 2
    ax.text(x + 0.1, ty, cabecera, fontsize=fs + 0.6, fontweight="bold", color=hx(
        col if col not in ("borde", "txt2") else "txt"), family=MONO_MPL, va="center")
    ax.plot([x + 0.1, x + w - 0.1], [ty - lh * 0.58] * 2, color=hx(col), lw=0.6, zorder=4)
    for i, ln in enumerate(lineas):
        ax.text(x + 0.1, ty - (i + 1) * lh - 0.02, ln, fontsize=fs, color=hx("txt2"),
                family=MONO_MPL, va="center")
    return (x, y, w, h)


def diagrama_objetos() -> Path:
    W, H = 12.13, 4.73
    fig, ax = lienzo(W, H)
    # Contenedores (subgraphs)
    grupos = [
        (0.03, 3.2, "Entidades activas en escena", "cian"),
        (3.35, 5.25, "batallonJugador  *--  MiembroEscuadron  (composición fuerte)", "oro"),
        (8.72, 3.38, "Agregación débil (objetos independientes)", "verde"),
    ]
    for gx, gw, etiqueta, col in grupos:
        caja(ax, gx, 0.03, gw, 3.67, color=col, fill=None, lw=1.0, ls=(0, (4, 3)), radio=0.1)
        ax.text(gx + gw - 0.12, 3.56, etiqueta, fontsize=7.2, color=hx(col), ha="right",
                va="center", fontweight="bold")
    # Fila superior
    modo = objeto(ax, 0.9, 4.71, 4.25, "modoDuelo : ModoDueloBatallones",
                  ["fase = PROYECTIL_EN_VUELO  |  turnoIA = 1",
                   "vientoActual = -48.5  |  camaraX = 310.0",
                   "botinProcesadoEnTurno = false"], col="cian")
    motor = objeto(ax, 8.95, 4.71, 2.95, "app : WalkingBowmastersPOO",
                   ["estado = JUGANDO_MODO_2"], col="oro")
    # Grupo 1: mundo
    be = objeto(ax, 0.3, 3.38, 2.8, "batallonEnemigo : Batallon",
                ["nombre = 'Batallon Saqueador'", "x = 1620.0  |  y = 582.0",
                 "vida = 320 / 320  |  esJugador = false"], col="rojo")
    pr = objeto(ax, 0.3, 2.45, 2.8, "proyectiles[0] : Proyectil",
                ["tipo = GRANADA | faccionJugador = true", "x = 785.4  |  y = 264.2",
                 "vx = 512.0  |  vy = -190.5", "dano = 74  |  factorGravedad = 1.0",
                 "radioExplosion = 145.0", "yaLanzado = true"], col="rojo")
    ob = objeto(ax, 0.3, 1.04, 2.8, "obstaculos[0] : ObstaculoTerreno",
                ["tipo = 'AUTOBUS'  |  x = 780.0", "ancho = 185.0  |  alto = 118.0"], col="txt2")
    # Grupo 2: composicion
    bj = objeto(ax, 3.58, 3.38, 4.4, "batallonJugador : Batallon",
                ["nombre = 'Batallon Aliado'  |  x = 210.0  |  y = 582.0",
                 "vida = 240  |  vidaMaxima = 320   (75 %)",
                 "armadura = 8  |  esJugador = true  |  activo = true",
                 "anguloApuntado = 0.68 rad"], col="oro")
    miembros_def = [
        ("miembros[0] : MiembroEscuadron", ["offsetX = -52.0 | usaSombrero = true", "vivo = true | progresoCaida = 0.0"], "verde"),
        ("miembros[1] : MiembroEscuadron", ["offsetX = -18.0 | usaCasco = true", "vivo = true | progresoCaida = 0.0"], "verde"),
        ("miembros[2] : MiembroEscuadron", ["offsetX = 16.0", "vivo = true | progresoCaida = 0.0"], "verde"),
        ("miembros[3] : MiembroEscuadron", ["offsetX = 50.0 | vivo = false", "progresoCaida = 1.0 (caído al 75 %)"], "rojo"),
    ]
    mx = [3.58, 6.13]
    my = [2.12, 1.05]
    miembros = []
    for i, (cab, lns, col) in enumerate(miembros_def):
        miembros.append(objeto(ax, mx[i % 2], my[i // 2], 2.25, cab, lns, col=col, fs=6.9))
    # Grupo 3: agregacion
    inv = objeto(ax, 8.92, 3.38, 2.7, "inventarioCompartido : Inventario",
                 ["recursosAcumulados = 160", "bajasTotales = 1"], col="verde", fs=7.0)
    lg = objeto(ax, 8.92, 2.6, 2.7, "armas[1] : LanzaGranadas",
                ["nombre = 'Lanzagranadas M79'", "danoBase = 74",
                 "municion = 9  |  municionMaxima = 24"], col="verde", fs=7.0)
    bo = objeto(ax, 8.92, 1.62, 2.7, "suministros[0] : Suministro",
                ["tipo = BOTIQUIN | cantidad = 3", "enSuelo = false"], col="verde", fs=7.0)
    mu = objeto(ax, 8.92, 0.8, 2.7, "suministros[1] : Suministro",
                ["tipo = CAJA_MUNICION | cantidad = 3", "enSuelo = false"], col="verde", fs=7.0)

    def cen(o, lado, f=0.5):
        x, y, w, h = o
        return {"t": (x + w * f, y + h), "b": (x + w * f, y),
                "l": (x, y + h * f), "r": (x + w, y + h * f)}[lado]

    c = "txt2"
    # app --> modoDuelo
    flecha(ax, cen(motor, "l"), (modo[0] + modo[2], cen(motor, "l")[1]), "oro")
    ax.text((modo[0] + modo[2] + motor[0]) / 2, cen(motor, "l")[1] + 0.09, "modoActivo",
            fontsize=6.8, color=hx("oro"), ha="center", family=MONO_MPL)
    # app o-- inventarioCompartido
    p0 = cen(motor, "b", 0.5)
    p1 = rombo(ax, p0, (0, -1), False, "verde")
    flecha(ax, p1, (p0[0], inv[1] + inv[3]), "verde")
    # modoDuelo --> batallonJugador
    flecha(ax, cen(modo, "b", 0.88), (cen(modo, "b", 0.88)[0], bj[1] + bj[3]), "cian")
    # modoDuelo --> entidades en escena (tronco a la izquierda)
    xt = 0.16
    linea(ax, [cen(modo, "b", 0.12), (cen(modo, "b", 0.12)[0], 3.47), (xt, 3.47),
               (xt, cen(ob, "l")[1])], "cian")
    for o in (be, pr, ob):
        flecha(ax, (xt, cen(o, "l")[1]), cen(o, "l"), "cian")
    # batallonJugador *-- miembros (tronco central)
    xt2 = 6.0
    p0 = (xt2, bj[1])
    p1 = rombo(ax, p0, (0, -1), True, "oro")
    yb = cen(miembros[2], "l")[1]
    linea(ax, [p1, (xt2, yb)], "oro")
    for i, m in enumerate(miembros):
        lado = "r" if i % 2 == 0 else "l"
        destino = cen(m, lado)
        linea(ax, [(xt2, destino[1]), destino], "oro")
    # batallonJugador o-- inventario / armaActual
    a0 = (bj[0] + bj[2], cen(inv, "l")[1])
    a1 = rombo(ax, a0, (1, 0), False, "verde")
    flecha(ax, a1, cen(inv, "l"), "verde")
    ax.text(a1[0] + 0.2, a0[1] + 0.07, "inventario", fontsize=5.9,
            color=hx("verde"), ha="center", family=MONO_MPL)
    b0 = (bj[0] + bj[2], bj[1] + 0.12)
    b1 = rombo(ax, b0, (1, -0.9), False, "verde")
    flecha(ax, b1, cen(lg, "l", 0.62), "verde")
    ax.text(8.3, 2.3, "armaActual", fontsize=6.4, color=hx("verde"), ha="center",
            family=MONO_MPL, rotation=0)
    # inventario o-- arma / suministros (tronco derecho)
    xt3 = 11.85
    q0 = cen(inv, "r")
    q1 = rombo(ax, q0, (1, 0), False, "verde")
    linea(ax, [q1, (xt3, q1[1]), (xt3, cen(mu, "r")[1])], "verde")
    for o in (lg, bo, mu):
        flecha(ax, (xt3, cen(o, "r")[1]), cen(o, "r"), "verde")
    return guardar_fig(fig, "d3_objetos_runtime.png")


# =============================================================================
# PILLOW: MOCKUPS ESTILO Graphics2D
# =============================================================================
def fuente_pil(nombre: str, tam: int):
    for cand in (f"C:/Windows/Fonts/{nombre}", f"/usr/share/fonts/truetype/dejavu/{nombre}"):
        if Path(cand).exists():
            return ImageFont.truetype(cand, tam)
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", tam)
    except OSError:
        return ImageFont.load_default()


def color_vida(pct: float):
    """Interpolacion verde -> amarillo -> rojo como en dibujarBarraVida."""
    rojo, amarillo, verde = (217, 68, 58), (235, 205, 80), (87, 199, 133)
    if pct >= 0.5:
        t = (pct - 0.5) / 0.5
        a, b = amarillo, verde
    else:
        t = pct / 0.5
        a, b = rojo, amarillo
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def cielo(w, h, y_horizonte):
    stops = [(0.0, (16, 14, 34)), (0.38, (62, 30, 60)), (0.62, (150, 62, 66)),
             (0.80, (226, 128, 74)), (1.0, (240, 180, 96))]
    ys = np.linspace(0, 1, h)[:, None] * (h / max(1, y_horizonte))
    ys = np.clip(ys, 0, 1)
    img = np.zeros((h, w, 3), dtype=np.float32)
    for c in range(3):
        img[..., c] = np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops])
    return Image.fromarray(img.astype(np.uint8), "RGB").convert("RGBA")


def capa_edificios(w, h, base_y, color, alto_min, alto_max, ancho_min, ancho_max, seed,
                   ventanas=False):
    rng = np.random.default_rng(seed)
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    x = -int(rng.integers(0, ancho_max))
    while x < w:
        bw = int(rng.integers(ancho_min, ancho_max))
        bh = int(rng.integers(alto_min, alto_max))
        top = base_y - bh
        roto = rng.random() < 0.45
        if roto:
            pts = [(x, base_y), (x, top + int(bh * 0.12)), (x + bw * 0.3, top),
                   (x + bw * 0.5, top + int(bh * 0.18)), (x + bw * 0.72, top + int(bh * 0.05)),
                   (x + bw, top + int(bh * 0.22)), (x + bw, base_y)]
            d.polygon(pts, fill=color)
        else:
            d.rectangle([x, top, x + bw, base_y], fill=color)
        if ventanas:
            for wy in range(top + 18, base_y - 12, 26):
                for wx in range(x + 10, x + bw - 12, 22):
                    if rng.random() < 0.11:
                        d.rectangle([wx, wy, wx + 8, wy + 11], fill=(235, 170, 90, 150))
        x += bw + int(rng.integers(4, 30))
    return capa


def silueta_humana(d, x, base, s, rim, casco=False, sombrero=False, mira=1, caido=False):
    oscuro = (14, 12, 20, 255)
    if caido:
        d.rounded_rectangle([x - 26 * s, base - 12 * s, x + 26 * s, base], radius=6 * s,
                            fill=oscuro, outline=rim, width=max(1, int(2 * s)))
        return
    d.line([(x - 6 * s, base - 30 * s), (x - 10 * s, base)], fill=oscuro, width=int(7 * s))
    d.line([(x + 6 * s, base - 30 * s), (x + 10 * s, base)], fill=oscuro, width=int(7 * s))
    d.rounded_rectangle([x - 12 * s, base - 64 * s, x + 12 * s, base - 26 * s],
                        radius=int(7 * s), fill=oscuro, outline=rim, width=max(1, int(2 * s)))
    d.ellipse([x - 9 * s, base - 84 * s, x + 9 * s, base - 66 * s], fill=oscuro,
              outline=rim, width=max(1, int(2 * s)))
    if casco:
        d.chord([x - 11 * s, base - 88 * s, x + 11 * s, base - 70 * s], 180, 360, fill=rim)
    if sombrero:
        d.rectangle([x - 15 * s, base - 80 * s, x + 15 * s, base - 77 * s], fill=rim)
        d.rectangle([x - 8 * s, base - 90 * s, x + 8 * s, base - 78 * s], fill=rim)
    d.line([(x, base - 54 * s), (x + mira * 34 * s, base - 70 * s)], fill=(60, 60, 70, 255),
           width=int(6 * s))


def silueta_zombie(d, x, base, s, casco=False):
    piel = (52, 70, 52, 255)
    ropa = (40, 30, 34, 255)
    d.line([(x - 4 * s, base - 30 * s), (x - 12 * s, base)], fill=ropa, width=int(7 * s))
    d.line([(x + 6 * s, base - 30 * s), (x + 4 * s, base)], fill=ropa, width=int(7 * s))
    d.polygon([(x - 12 * s, base - 28 * s), (x + 10 * s, base - 28 * s),
               (x + 2 * s, base - 64 * s), (x - 22 * s, base - 60 * s)], fill=ropa)
    d.ellipse([x - 32 * s, base - 82 * s, x - 14 * s, base - 64 * s], fill=piel)
    if casco:
        d.chord([x - 34 * s, base - 86 * s, x - 12 * s, base - 68 * s], 180, 360,
                fill=(110, 118, 128, 255))
    d.ellipse([x - 28 * s, base - 75 * s, x - 24 * s, base - 71 * s], fill=(255, 60, 50, 255))
    d.line([(x - 14 * s, base - 56 * s), (x - 46 * s, base - 58 * s)], fill=piel, width=int(5 * s))


def autobus(d, x, base, s):
    d.rounded_rectangle([x, base - 118 * s, x + 185 * s, base - 14 * s], radius=int(10 * s),
                        fill=(36, 30, 38, 255), outline=(70, 58, 62, 255), width=int(2 * s))
    for i in range(6):
        wx = x + (12 + i * 28) * s
        d.rectangle([wx, base - 104 * s, wx + 20 * s, base - 78 * s], fill=(70, 46, 40, 255))
    for wx in (x + 38 * s, x + 145 * s):
        d.ellipse([wx - 15 * s, base - 30 * s, wx + 15 * s, base], fill=(12, 10, 14, 255))


def coche(d, x, base, s):
    d.rounded_rectangle([x, base - 50 * s, x + 130 * s, base - 12 * s], radius=int(8 * s),
                        fill=(40, 32, 36, 255))
    d.polygon([(x + 28 * s, base - 50 * s), (x + 44 * s, base - 74 * s),
               (x + 92 * s, base - 74 * s), (x + 108 * s, base - 50 * s)], fill=(40, 32, 36, 255))
    for wx in (x + 26 * s, x + 104 * s):
        d.ellipse([wx - 13 * s, base - 26 * s, wx + 13 * s, base], fill=(12, 10, 14, 255))


def trayectoria(d, p0, p1, altura, color, n=26, r=4):
    (x0, y0), (x1, y1) = p0, p1
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t - 4 * altura * t * (1 - t)
        rr = r * (0.55 + 0.45 * (1 - t))
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=color)


def barra_vida(d, x, y, w, h, pct, etiqueta, fnt):
    d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=(14, 17, 24, 220),
                        outline=(54, 65, 86, 255), width=2)
    d.rounded_rectangle([x + 3, y + 3, x + 3 + (w - 6) * pct, y + h - 3], radius=(h - 6) // 2,
                        fill=color_vida(pct) + (255,))
    d.text((x, y - fnt.size - 6), etiqueta, font=fnt, fill=(242, 244, 248, 255))


def selector_x(d, x, y, fnt, activo_100=True):
    partes = [("[X: ", (168, 179, 199)), ("5%", (79, 195, 247) if not activo_100 else (120, 130, 150)),
              (" | ", (168, 179, 199)), ("100%", (79, 195, 247) if activo_100 else (120, 130, 150)),
              ("]", (168, 179, 199))]
    total = sum(d.textlength(t, font=fnt) for t, _ in partes)
    pad = 16
    d.rounded_rectangle([x, y, x + total + 2 * pad, y + fnt.size + 20], radius=12,
                        fill=(14, 17, 24, 225), outline=(79, 195, 247, 255), width=2)
    cx = x + pad
    for t, c in partes:
        d.text((cx, y + 8), t, font=fnt, fill=c + (255,))
        cx += d.textlength(t, font=fnt)


def escena(w, h, variante: str, seed=7, oscurecer_izq=False) -> Image.Image:
    S = 2  # supermuestreo para antialiasing
    W, H = w * S, h * S
    suelo = int(H * 0.80)
    img = cielo(W, H, suelo)
    # Sol con halo
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    sx, sy, sr = int(W * 0.70), int(suelo - H * 0.16), int(H * 0.085)
    hd.ellipse([sx - sr * 3, sy - sr * 3, sx + sr * 3, sy + sr * 3], fill=(255, 170, 90, 70))
    halo = halo.filter(ImageFilter.GaussianBlur(sr))
    img = Image.alpha_composite(img, halo)
    ImageDraw.Draw(img).ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(255, 196, 120, 255))
    # Parallax: lejano (0.05/0.18) -> medio -> cercano (0.45)
    img = Image.alpha_composite(img, capa_edificios(W, H, suelo, (70, 40, 66, 255), int(H * .18),
                                                    int(H * .40), 50 * S, 120 * S, seed))
    img = Image.alpha_composite(img, capa_edificios(W, H, suelo, (36, 24, 40, 255), int(H * .10),
                                                    int(H * .28), 70 * S, 160 * S, seed + 1, True))
    d = ImageDraw.Draw(img)
    d.rectangle([0, suelo, W, H], fill=(20, 17, 24, 255))
    d.line([(0, suelo), (W, suelo)], fill=(92, 58, 60, 255), width=3 * S)
    for x in range(0, W, 90 * S):
        d.rectangle([x, suelo + int(H * 0.09), x + 44 * S, suelo + int(H * 0.09) + 4 * S],
                    fill=(70, 62, 50, 255))
    # Cenizas
    rng = np.random.default_rng(seed + 9)
    for _ in range(int(W * H / 26000)):
        ax_, ay_ = rng.uniform(0, W), rng.uniform(0, suelo)
        rr = rng.uniform(0.8, 2.2) * S
        d.ellipse([ax_ - rr, ay_ - rr, ax_ + rr, ay_ + rr], fill=(230, 220, 210, int(rng.uniform(40, 120))))

    s = H / 720 * 1.05
    f_hud = fuente_pil("segoeuib.ttf", int(17 * S * (H / S) / 720))
    f_big = fuente_pil("segoeuib.ttf", int(22 * S * (H / S) / 720))
    oro, rojo, cian, verde = (235, 185, 95, 255), (217, 68, 58, 255), (79, 195, 247, 255), (87, 199, 133, 255)

    if variante in ("duelo", "portada"):
        x_j = W * (0.60 if variante == "portada" else 0.12)
        x_e = W * (0.93 if variante == "portada" else 0.88)
        x_bus = W * (0.68 if variante == "portada" else 0.38)
        autobus(d, x_bus, suelo, s)
        if variante != "portada":
            coche(d, W * 0.62, suelo, s)
        for i, off in enumerate((-52, -18, 16, 50)):
            silueta_humana(d, x_j + off * s, suelo, s, oro, casco=(i in (1, 3)), sombrero=(i == 0),
                           mira=1, caido=(i == 3))
        for i, off in enumerate((-50, -16, 18, 52)):
            silueta_humana(d, x_e + off * s, suelo, s, rojo, casco=(i == 1), sombrero=(i == 3), mira=-1)
        p0 = (x_j + 40 * s, suelo - 70 * s)
        p1 = (x_e - 70 * s, suelo - 40 * s)
        trayectoria(d, p0, p1, H * 0.42, (79, 195, 247, 200), n=30, r=4 * S)
        gx = p0[0] + (p1[0] - p0[0]) * 0.55
        gy = p0[1] + (p1[1] - p0[1]) * 0.55 - 4 * H * 0.42 * 0.55 * 0.45
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([gx - 30 * S, gy - 30 * S, gx + 30 * S, gy + 30 * S],
                                     fill=(255, 120, 60, 160))
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(10 * S)))
        d = ImageDraw.Draw(img)
        d.ellipse([gx - 9 * S, gy - 9 * S, gx + 9 * S, gy + 9 * S], fill=(255, 210, 140, 255))
        # HUD
        bw = int(W * (0.15 if variante == "portada" else 0.30))
        y_hud = int(H * 0.11)
        x_hud = int(W * (0.56 if variante == "portada" else 0.04))
        barra_vida(d, x_hud, y_hud, bw, 22 * S, 0.75, "Batallon Aliado  240/320", f_hud)
        barra_vida(d, W - bw - int(W * 0.04), y_hud, bw, 22 * S, 1.0, "Batallon Saqueador  320/320", f_hud)
        if variante == "portada":
            selector_x(d, int(W * 0.665), int(H * 0.22), f_big)
        tx, ty = (W * 0.5, H * 0.30) if variante == "duelo" else (W * 0.90, H * 0.30)
        d.text((tx, ty), "VIENTO  ←  -48.5", font=f_hud, fill=(168, 179, 199, 255), anchor="mm")
    elif variante == "hordas":
        bx = W * 0.22
        for k in range(4):
            d.line([(bx - 30 * S, suelo - (14 + k * 26) * s), (bx + 30 * S, suelo - (30 + k * 26) * s)],
                   fill=(120, 86, 56, 255), width=int(12 * s))
        d.rectangle([bx - 6 * S, suelo - 120 * s, bx + 6 * S, suelo], fill=(90, 64, 44, 255))
        silueta_humana(d, W * 0.12, suelo, s, verde, casco=False, mira=1)
        d.arc([W * 0.12 - 10 * S, suelo - 120 * s, W * 0.12 + 90 * s, suelo - 20 * s], 290, 60,
              fill=cian, width=int(5 * s))
        silueta_zombie(d, W * 0.44, suelo, s * 1.05)
        silueta_zombie(d, W * 0.57, suelo, s * 0.95, casco=True)
        silueta_zombie(d, W * 0.70, suelo, s * 1.1)
        silueta_humana(d, W * 0.88, suelo, s, rojo, sombrero=True, mira=-1)
        barra_vida(d, int(W * 0.04), int(H * 0.11), int(W * 0.30), 22 * S, 0.42, "Barricada", f_hud)
        d.text((W * 0.96, H * 0.10), "OLEADA 3", font=f_big, fill=oro, anchor="ra")
    elif variante == "armeria":
        x0 = W * 0.08
        silueta_humana(d, x0, suelo, s, verde, casco=True, mira=1)
        nombres = [(0.30, "Blanco 5%"), (0.56, "Blanco Medio"), (0.86, "Blanco 100%")]
        for fx, et in nombres:
            cx, cy = W * fx, suelo - 60 * s
            for r, c in ((40, (242, 244, 248, 255)), (28, (217, 68, 58, 255)),
                         (16, (242, 244, 248, 255)), (7, (217, 68, 58, 255))):
                d.ellipse([cx - r * s, cy - r * s, cx + r * s, cy + r * s], fill=c)
            d.rectangle([cx - 3 * S, cy + 40 * s, cx + 3 * S, suelo], fill=(90, 64, 44, 255))
            d.text((cx, cy - 58 * s), et, font=f_hud, fill=(242, 244, 248, 255), anchor="mm")
        p0 = (x0 + 36 * s, suelo - 70 * s)
        trayectoria(d, p0, (W * 0.30, suelo - 60 * s), H * 0.08, (79, 195, 247, 220), n=12, r=4 * S)
        trayectoria(d, p0, (W * 0.86, suelo - 60 * s), H * 0.40, (235, 185, 95, 220), n=30, r=4 * S)
        selector_x(d, int(W * 0.04), int(H * 0.08), f_big)

    if oscurecer_izq:
        xs = np.linspace(0, 1, W)
        alpha = np.clip(1 - xs / 0.60, 0, 1) ** 1.25 * 238
        mask = np.tile(alpha[None, :], (H, 1)).astype(np.uint8)
        sombra = Image.new("RGBA", (W, H), (14, 17, 24, 0))
        sombra.putalpha(Image.fromarray(mask, "L"))
        img = Image.alpha_composite(img, sombra)
    # Fundido inferior hacia el fondo de la diapositiva
    fade = np.clip((np.linspace(0, 1, H) - 0.88) / 0.12, 0, 1) * (200 if oscurecer_izq else 0)
    if fade.max() > 0:
        m = np.tile(fade[:, None], (1, W)).astype(np.uint8)
        capa = Image.new("RGBA", (W, H), (14, 17, 24, 0))
        capa.putalpha(Image.fromarray(m, "L"))
        img = Image.alpha_composite(img, capa)
    return img.resize((w, h), Image.LANCZOS).convert("RGB")


def generar_mockups() -> dict:
    rutas = {}
    portada = escena(1920, 1080, "portada", seed=11, oscurecer_izq=True)
    rutas["portada"] = ASSETS / "m0_portada.png"
    portada.save(rutas["portada"])
    for v, sd in (("hordas", 3), ("duelo", 5), ("armeria", 8)):
        im = escena(900, 380, v, seed=sd)
        rutas[v] = ASSETS / f"m_{v}.png"
        im.save(rutas[v])
    return rutas


# =============================================================================
# PYTHON-PPTX: PRIMITIVAS DE MAQUETACION
# =============================================================================
def sin_sombra(shape):
    try:
        shape.shadow.inherit = False
    except Exception:  # conectores no exponen shadow
        pass


def texto(slide, x, y, w, h, contenido, tam=14, color="txt", negrita=False, fuente=FUENTE,
          alin=PP_ALIGN.LEFT, ancla=MSO_ANCHOR.TOP, italica=False, margen=0.0,
          interlineado=None, espacio_despues=0):
    """`contenido`: str | lista de parrafos; cada parrafo str | lista de runs (texto, opciones)."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    for lado in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{lado}", Inches(margen))
    tf.vertical_anchor = ancla
    parrafos = contenido if isinstance(contenido, list) else [contenido]
    for i, par in enumerate(parrafos):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = alin
        if interlineado:
            p.line_spacing = interlineado
        p.space_after = Pt(espacio_despues)
        runs = par if isinstance(par, list) else [(par, {})]
        for t, op in runs:
            r = p.add_run()
            r.text = t
            f = r.font
            f.name = op.get("fuente", fuente)
            f.size = Pt(op.get("tam", tam))
            f.bold = op.get("negrita", negrita)
            f.italic = op.get("italica", italica)
            f.color.rgb = rgb(op.get("color", color))
    return tb


def rect(slide, x, y, w, h, relleno="card", borde="borde", radio=0.08, grosor=1.0,
         forma=MSO_SHAPE.ROUNDED_RECTANGLE, discontinuo=False):
    s = slide.shapes.add_shape(forma, Inches(x), Inches(y), Inches(w), Inches(h))
    sin_sombra(s)
    if relleno:
        s.fill.solid()
        s.fill.fore_color.rgb = rgb(relleno)
    else:
        s.fill.background()
    if borde:
        s.line.color.rgb = rgb(borde)
        s.line.width = Pt(grosor)
        if discontinuo:
            from pptx.enum.dml import MSO_LINE
            s.line.dash_style = MSO_LINE.DASH
    else:
        s.line.fill.background()
    if forma == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = min(0.5, radio / max(0.01, min(w, h)))
    s.text_frame.text = ""
    return s


def circulo(slide, x, y, d, relleno, borde=None, txt=None, tam=12, color_txt="bg"):
    s = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    sin_sombra(s)
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(relleno)
    if borde:
        s.line.color.rgb = rgb(borde)
    else:
        s.line.fill.background()
    if txt is not None:
        tf = s.text_frame
        for lado in ("left", "right", "top", "bottom"):
            setattr(tf, f"margin_{lado}", 0)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = txt
        r.font.size = Pt(tam)
        r.font.bold = True
        r.font.name = FUENTE
        r.font.color.rgb = rgb(color_txt)
    return s


def pildora(slide, x, y, w, h, txt, color, tam=12, fuente=FUENTE, relleno="card",
            color_txt=None, negrita=True):
    s = rect(slide, x, y, w, h, relleno=relleno, borde=color, radio=h / 2, grosor=1.25)
    tf = s.text_frame
    for lado in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{lado}", Inches(0.04))
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = txt
    r.font.size = Pt(tam)
    r.font.bold = negrita
    r.font.name = fuente
    r.font.color.rgb = rgb(color_txt or color)
    return s


def conector(slide, x1, y1, x2, y2, color="txt2", grosor=1.5, punta=True, discontinuo=False,
             punta_inicio=None):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1),
                                   Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(grosor)
    if discontinuo:
        from pptx.enum.dml import MSO_LINE
        c.line.dash_style = MSO_LINE.DASH
    ln = c.line._get_or_add_ln()
    if punta_inicio:
        he = etree.SubElement(ln, qn("a:headEnd"))
        he.set("type", punta_inicio)
        he.set("w", "med")
        he.set("len", "med")
    if punta:
        te = etree.SubElement(ln, qn("a:tailEnd"))
        te.set("type", "triangle")
        te.set("w", "med")
        te.set("len", "med")
    return c


def polilinea(slide, puntos, color="txt2", grosor=1.5, punta=True, punta_inicio=None):
    for i in range(len(puntos) - 1):
        (x1, y1), (x2, y2) = puntos[i], puntos[i + 1]
        conector(slide, x1, y1, x2, y2, color, grosor,
                 punta=(punta and i == len(puntos) - 2),
                 punta_inicio=(punta_inicio if i == 0 else None))


def imagen(slide, ruta, x, y, w=None, h=None):
    kw = {}
    if w is not None:
        kw["width"] = Inches(w)
    if h is not None:
        kw["height"] = Inches(h)
    return slide.shapes.add_picture(str(ruta), Inches(x), Inches(y), **kw)


def imagen_ajustada(slide, ruta, x, y, w_max, h_max, centrar=True):
    with Image.open(ruta) as im:
        iw, ih = im.size
    escala = min(w_max / iw, h_max / ih)
    w, h = iw * escala, ih * escala
    if centrar:
        x += (w_max - w) / 2
    return imagen(slide, ruta, x, y, w, h)


KW_JAVA = {"public", "private", "protected", "static", "final", "class", "return", "new",
           "double", "int", "boolean", "void", "for", "if", "else", "this", "super", "true",
           "false", "null", "abstract", "interface", "extends", "implements"}
TOKEN_RE = re.compile(r"(//.*$|\"[^\"]*\"|'[^']*'|@\w+|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b|\s+|.)")


def colorear_java(linea_codigo: str):
    runs = []
    for m in TOKEN_RE.finditer(linea_codigo):
        tok = m.group(0)
        if tok.startswith("//"):
            col = "gris"
        elif tok.startswith('"') or tok.startswith("'"):
            col = "verde"
        elif tok.startswith("@"):
            col = "rojo"
        elif re.fullmatch(r"\d+(?:\.\d+)?", tok):
            col = "verde"
        elif tok in KW_JAVA:
            col = "oro"
        elif re.fullmatch(r"[A-Z]\w*", tok):
            col = "cian"
        else:
            col = "txt"
        if runs and runs[-1][1]["color"] == col:
            runs[-1] = (runs[-1][0] + tok, runs[-1][1])
        else:
            runs.append((tok, {"color": col, "fuente": MONO, "italica": col == "gris"}))
    return runs or [(" ", {"fuente": MONO})]


def bloque_codigo(slide, x, y, w, h, codigo: str, tam=11, titulo=None, color_titulo="txt2"):
    rect(slide, x, y, w, h, relleno="card2", borde="borde", radio=0.08)
    y_txt = y + 0.12
    if titulo:
        texto(slide, x + 0.18, y + 0.1, w - 0.36, 0.28, titulo, tam=10.5, color=color_titulo,
              fuente=MONO, negrita=True)
        y_txt = y + 0.42
    lineas = codigo.strip("\n").split("\n")
    texto(slide, x + 0.18, y_txt, w - 0.3, h - (y_txt - y) - 0.08,
          [colorear_java(l) for l in lineas], tam=tam, fuente=MONO, interlineado=1.0)


def encabezado(slide, n: int, seccion: str, titulo: str, color_kicker="oro"):
    texto(slide, CONT_X, 0.6, 9.5, 0.3, f"{n:02d} · {seccion.upper()}", tam=12,
          color=color_kicker, negrita=True)
    texto(slide, CONT_X, 0.88, CONT_W, 0.7, titulo, tam=30, color="txt", negrita=True)


def pie(slide, n: int, seccion: str):
    texto(slide, CONT_X, 6.64, 6.0, 0.26, PROYECTO, tam=10, color="gris")
    texto(slide, 6.0, 6.64, 4.0, 0.26, seccion, tam=10, color="gris", alin=PP_ALIGN.CENTER)
    texto(slide, SLIDE_W - MARGEN - 2.0, 6.64, 2.0, 0.26, f"{n} / {TOTAL}", tam=10,
          color="txt2", negrita=True, alin=PP_ALIGN.RIGHT)


def nueva_diapositiva(prs, n, seccion, titulo, notas, kicker="oro"):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb("bg")
    if titulo:
        encabezado(s, n, seccion, titulo, kicker)
    pie(s, n, seccion)
    s.notes_slide.notes_text_frame.text = notas.strip()
    return s


def tarjeta(slide, x, y, w, h, color_icono, icono, titulo, cuerpo, tam_cuerpo=13,
            tam_titulo=15, subtitulo=None):
    rect(slide, x, y, w, h)
    circulo(slide, x + 0.2, y + 0.2, 0.42, color_icono, txt=icono, tam=12)
    texto(slide, x + 0.75, y + 0.2, w - 0.95, 0.42, titulo, tam=tam_titulo, negrita=True,
          ancla=MSO_ANCHOR.MIDDLE)
    yy = y + 0.72
    if subtitulo:
        texto(slide, x + 0.2, yy, w - 0.4, 0.3, subtitulo, tam=11, fuente=MONO, color=color_icono)
        yy += 0.32
    texto(slide, x + 0.2, yy, w - 0.4, h - (yy - y) - 0.12, cuerpo, tam=tam_cuerpo, color="txt2",
          espacio_despues=4)


# =============================================================================
# DIAPOSITIVAS
# =============================================================================
def d01_portada(prs, rec):
    s = nueva_diapositiva(prs, 1, "Portada", None, NOTAS[1])
    imagen(s, rec["portada"], 0, 0, SLIDE_W, SLIDE_H)
    texto(s, CONT_X, 0.85, 7.2, 0.35, "LÓGICA DE PROGRAMACIÓN II · PROGRAMACIÓN ORIENTADA A OBJETOS",
          tam=12, color="oro", negrita=True)
    texto(s, CONT_X, 1.22, 7.6, 1.6, ["THE WALKING", "BOWMASTERS"], tam=48, negrita=True,
          interlineado=0.9)
    texto(s, CONT_X, 2.8, 7.0, 0.5, "Edición POO Modular", tam=26, color="oro", negrita=True)
    texto(s, CONT_X, 3.38, 6.3, 0.9,
          [[("Arquitectura Orientada a Objetos, Física Balística y Motor 2D Procedural en Java Swing (", {}),
            ("Graphics2D", {"fuente": MONO, "color": "cian"}), (")", {})]],
          tam=16, color="txt2")
    badges = [("60 FPS", "oro", 1.15), ("Java Swing + PCM Audio", "cian", 2.55),
              ("9 Paquetes Modulares", "verde", 2.35), ("3 Modos Jugables", "rojo", 1.95)]
    x = CONT_X
    for t, c, w in badges:
        pildora(s, x, 4.38, w, 0.42, t, c, tam=12, relleno="bg")
        x += w + 0.15
    texto(s, CONT_X, 4.98, 7.5, 0.3,
          [[("⌂  ", {"color": "oro"}),
            ("github.com/JOHN-RAVEN-CROWNSON-2008/ProyectoLogicaDeProgramacion-II",
             {"fuente": MONO, "color": "txt2"})]], tam=12)


def d02_vision(prs, rec):
    s = nueva_diapositiva(prs, 2, "Visión general", "Tres modos de juego, un mismo campamento", NOTAS[2])
    modos = [
        ("1", "rojo", "Supervivencia de Hordas", "ModoSupervivenciaHordas", rec["hordas"],
         "Defiendes una barricada contra oleadas procedurales. Rifle, granada, revólver o corte "
         "cuerpo a cuerpo con la Katana.",
         ["ZombieCaminante", "ZombieCorredor", "ZombieBlindado", "SaqueadorRival"]),
        ("2", "cian", "Duelo de Batallones 1v1", "ModoDueloBatallones", rec["duelo"],
         "Duelo por turnos tras obstáculos, con viento aleatorio, cámara dinámica e IA balística "
         "que afina la puntería cada turno.",
         ["AUTOBUS", "COCHE", "FaseTurno", "vientoActual"]),
        ("3", "verde", "Armería y Campo de Tiro", "ModoArmeriaCampoTiro", rec["armeria"],
         "Gestionas el Inventario compartido, compras con botín y calibras cada arma con la tecla X.",
         ["Blanco 5%", "Blanco Medio", "Blanco 100%"]),
    ]
    gap = 0.3
    w = (CONT_W - 2 * gap) / 3
    y, h = CONT_Y, CONT_BOTTOM - CONT_Y
    for i, (num, col, titulo, clase, img, desc, chips) in enumerate(modos):
        x = CONT_X + i * (w + gap)
        rect(s, x, y, w, h)
        imagen(s, img, x + 0.15, y + 0.15, w - 0.3, (w - 0.3) * 380 / 900)
        yi = y + 0.15 + (w - 0.3) * 380 / 900 + 0.18
        circulo(s, x + 0.2, yi, 0.4, col, txt=num, tam=13)
        texto(s, x + 0.72, yi - 0.03, w - 0.9, 0.3, titulo, tam=15, negrita=True)
        texto(s, x + 0.72, yi + 0.26, w - 0.9, 0.25, clase, tam=11, fuente=MONO, color=col)
        texto(s, x + 0.2, yi + 0.62, w - 0.4, 1.1, desc, tam=13, color="txt2")
        # chips
        filas, fila, ancho = [], [], 0.0
        for ch in chips:
            cw = 0.08 * len(ch) + 0.3
            if fila and ancho + cw > w - 0.4:
                filas.append(fila)
                fila, ancho = [], 0.0
            fila.append((ch, cw))
            ancho += cw + 0.1
        filas.append(fila)
        cy = y + h - 0.12 - len(filas) * 0.4
        for fila in filas:
            cx = x + 0.2
            for ch, cw in fila:
                pildora(s, cx, cy, cw, 0.32, ch, col, tam=10.5, fuente=MONO, negrita=False)
                cx += cw + 0.1
            cy += 0.4


def d03_arquitectura(prs, rec):
    s = nueva_diapositiva(prs, 3, "Arquitectura", "Arquitectura modular: 9 paquetes y una clase raíz",
                          NOTAS[3])
    imagen_ajustada(s, rec["arquitectura"], CONT_X, CONT_Y, 8.05, CONT_BOTTOM - CONT_Y, centrar=False)
    x, w = 9.0, SLIDE_W - MARGEN - 9.0
    # Stats
    for i, (num, et, col) in enumerate((("34", "archivos .java", "oro"), ("4.455", "líneas de código", "cian"))):
        xx = x + i * (w / 2 + 0.08)
        ww = w / 2 - 0.08
        rect(s, xx, CONT_Y, ww, 1.1)
        texto(s, xx, CONT_Y + 0.08, ww, 0.6, num, tam=30, negrita=True, color=col, alin=PP_ALIGN.CENTER)
        texto(s, xx, CONT_Y + 0.68, ww, 0.3, et, tam=11, color="txt2", alin=PP_ALIGN.CENTER)
    items = [
        ("↓", "oro", "Control descendente",
         "Raíz → modos → dominio → base. Ningún paquete importa modos/ ni la clase raíz."),
        ("◇", "verde", "Núcleo cohesivo",
         "armas, entidades e inventario se referencian entre sí (Combatiente → Arma → Proyectil)."),
        ("■", "cian", "Base sin dependencias",
         "interfaces/, util/ y audio/ no importan nada del proyecto: son la capa más estable."),
    ]
    yy = CONT_Y + 1.28
    hh = (CONT_BOTTOM - yy - 2 * 0.15) / 3
    for ic, col, t, c in items:
        rect(s, x, yy, w, hh)
        circulo(s, x + 0.15, yy + 0.15, 0.36, col, txt=ic, tam=12)
        texto(s, x + 0.62, yy + 0.13, w - 0.75, 0.4, t, tam=14, negrita=True, ancla=MSO_ANCHOR.MIDDLE)
        texto(s, x + 0.15, yy + 0.58, w - 0.3, hh - 0.62, c, tam=12, color="txt2")
        yy += hh + 0.15


def d04_librerias(prs, rec):
    s = nueva_diapositiva(prs, 4, "Librerías y APIs", "Librerías Java estándar: cero dependencias externas",
                          NOTAS[4])
    filas = [
        ("javax.swing.*", "JFrame · JPanel · Timer · SwingUtilities",
         "Ventana, lienzo con double buffering y latido de 60 FPS: new Timer(16, this)", "oro"),
        ("java.awt.*", "Graphics2D · RenderingHints · GradientPaint",
         "Dibujo vectorial procedural, degradados del cielo, transparencias y KEY_ANTIALIASING", "oro"),
        ("java.awt.event.*", "MouseAdapter · KeyAdapter · ActionListener",
         "Arrastre estilo Bowmasters, hover del cursor y teclas 1-4, Q/E/R, X, F1-F3, ESC", "cian"),
        ("java.awt.geom.*", "Point2D.Double · Ellipse2D · Arc2D",
         "Coordenadas virtuales en double, proyectiles, ondas expansivas y arcos de la Katana", "cian"),
        ("java.util.*", "List · ArrayList · Iterator · HashMap · Random",
         "Colecciones dinámicas, Iterator.remove() en colisiones, oleadas y viento procedurales", "verde"),
        ("javax.sound.sampled.*", "AudioFormat · AudioSystem · SourceDataLine",
         "Síntesis PCM de 16 bits a 44100 Hz en memoria, sin archivos .wav externos", "rojo"),
        ("java.util.concurrent.*", "ExecutorService · ThreadFactory · AtomicInteger",
         "Pool daemon en GestorSonido: hasta 10 voces sin bloquear el hilo de render", "rojo"),
    ]
    cols = [(CONT_X + 0.55, 2.75, "PAQUETE"), (CONT_X + 3.45, 3.75, "CLASES CLAVE"),
            (CONT_X + 7.35, CONT_W - 7.5, "ROL EN EL PROYECTO")]
    for cx, cw, et in cols:
        texto(s, cx, CONT_Y - 0.05, cw, 0.28, et, tam=10.5, color="gris", negrita=True)
    y = CONT_Y + 0.3
    hh, gap = 0.565, 0.075
    for api, clases, rol, col in filas:
        rect(s, CONT_X, y, CONT_W, hh, radio=0.08)
        circulo(s, CONT_X + 0.2, y + hh / 2 - 0.09, 0.18, col)
        texto(s, cols[0][0], y, cols[0][1], hh, api, tam=13, fuente=MONO, color=col, negrita=True,
              ancla=MSO_ANCHOR.MIDDLE)
        texto(s, cols[1][0], y, cols[1][1], hh, clases, tam=11, fuente=MONO, color="txt",
              ancla=MSO_ANCHOR.MIDDLE)
        texto(s, cols[2][0], y, cols[2][1], hh, rol, tam=12, color="txt2", ancla=MSO_ANCHOR.MIDDLE)
        y += hh + gap


def d05_gameloop(prs, rec):
    s = nueva_diapositiva(prs, 5, "Game loop", "El corazón del juego: bucle a 60 FPS y estados", NOTAS[5])
    # --- Ciclo -----------------------------------------------------------------
    cx = 3.62
    nodos = {
        "top": (cx - 1.15, 1.85, "1 · Entrada", "MouseAdapter · KeyAdapter", "oro"),
        "der": (4.42, 3.72, "2 · actionPerformed()", "dt = min(0.05, Δnano)", "cian"),
        "abj": (cx - 1.15, 5.55, "3 · actualizarLogica(dt)", "IA · física · colisiones", "verde"),
        "izq": (CONT_X, 3.72, "4 · repaint()", "→ paintComponent(g)", "rojo"),
    }
    W_N, H_N = 2.3, 0.86
    for x, y, t, sub, col in nodos.values():
        rect(s, x, y, W_N, H_N, borde=col, grosor=1.5)
        texto(s, x + 0.12, y + 0.08, W_N - 0.24, 0.35, t, tam=13, negrita=True, color=col)
        texto(s, x + 0.12, y + 0.45, W_N - 0.24, 0.32, sub, tam=11, fuente=MONO, color="txt2")
    t, d, a, i = nodos["top"], nodos["der"], nodos["abj"], nodos["izq"]
    conector(s, t[0] + W_N, t[1] + H_N / 2, d[0] + W_N / 2, d[1], "txt2", 1.75)
    conector(s, d[0] + W_N / 2, d[1] + H_N, a[0] + W_N, a[1] + H_N / 2, "txt2", 1.75)
    conector(s, a[0], a[1] + H_N / 2, i[0] + W_N / 2, i[1] + H_N, "txt2", 1.75)
    conector(s, i[0] + W_N / 2, i[1], t[0], t[1] + H_N / 2, "txt2", 1.75)
    circulo(s, cx - 0.72, 3.43, 1.44, "card", borde="oro")
    texto(s, cx - 0.72, 3.68, 1.44, 0.5, "60", tam=30, negrita=True, color="oro", alin=PP_ALIGN.CENTER)
    texto(s, cx - 0.72, 4.18, 1.44, 0.3, "FPS", tam=12, negrita=True, color="txt2", alin=PP_ALIGN.CENTER)
    texto(s, cx - 1.1, 4.92, 2.2, 0.3, "Timer(16, this)", tam=11, fuente=MONO, color="oro",
          alin=PP_ALIGN.CENTER)
    # --- Estados de pantalla ---------------------------------------------------
    x0, w0 = 7.25, SLIDE_W - MARGEN - 7.25
    rect(s, x0, CONT_Y, w0, 1.92)
    texto(s, x0 + 0.2, CONT_Y + 0.12, w0 - 0.4, 0.3, "EstadoPantalla", tam=13, negrita=True,
          fuente=MONO, color="oro")
    pildora(s, x0 + 0.2, CONT_Y + 0.92, 2.0, 0.4, "MENU_PRINCIPAL", "oro", tam=11, fuente=MONO)
    estados = [("JUGANDO_MODO_1", "rojo"), ("JUGANDO_MODO_2", "cian"), ("JUGANDO_MODO_3", "verde")]
    for k, (e, c) in enumerate(estados):
        yy = CONT_Y + 0.5 + k * 0.45
        pildora(s, x0 + w0 - 2.25, yy, 2.05, 0.36, e, c, tam=11, fuente=MONO)
        conector(s, x0 + 2.2, CONT_Y + 1.12, x0 + w0 - 2.25, yy + 0.18, "txt2", 1.25)
    # --- FaseTurno --------------------------------------------------------------
    y1 = CONT_Y + 2.12
    rect(s, x0, y1, w0, CONT_BOTTOM - y1)
    texto(s, x0 + 0.2, y1 + 0.12, w0 - 0.4, 0.3, "ModoDueloBatallones.FaseTurno", tam=13,
          negrita=True, fuente=MONO, color="cian")
    c1, c2 = x0 + 0.2, x0 + w0 - 2.35
    pw, ph = 2.15, 0.38
    r1, r2, r3 = y1 + 0.6, y1 + 1.3, y1 + 2.0
    pildora(s, c1, r1, pw, ph, "TURNO_JUGADOR", "verde", tam=11, fuente=MONO)
    pildora(s, c2, r1, pw, ph, "PROYECTIL_EN_VUELO", "cian", tam=11, fuente=MONO)
    pildora(s, c2, r2, pw, ph, "PAUSA_IMPACTO", "oro", tam=11, fuente=MONO)
    pildora(s, c1, r2, pw, ph, "TURNO_IA", "rojo", tam=11, fuente=MONO)
    pildora(s, c2, r3, pw, ph, "FIN_DUELO", "txt2", tam=11, fuente=MONO)
    conector(s, c1 + pw, r1 + ph / 2, c2, r1 + ph / 2, "txt2", 1.25)
    conector(s, c2 + pw / 2, r1 + ph, c2 + pw / 2, r2, "txt2", 1.25)
    conector(s, c2, r2 + ph / 2, c1 + pw, r2 + ph / 2, "txt2", 1.25)
    conector(s, c1 + pw * 0.8, r2, c2 + 0.25, r1 + ph, "txt2", 1.0, discontinuo=True)
    conector(s, c2 + pw / 2, r2 + ph, c2 + pw / 2, r3, "txt2", 1.25)
    texto(s, c1, r3 - 0.04, 2.3, 0.5, "Pausa de 1.05 s; tras el disparo IA vuelve a TURNO_JUGADOR",
          tam=10.5, color="txt2")


def d06_render(prs, rec):
    s = nueva_diapositiva(prs, 6, "Render y audio", "Pipeline de render 2D y audio procedural", NOTAS[6])
    capas = [
        ("Double buffering", "setDoubleBuffered(true)", "oro"),
        ("Antialiasing", "KEY_ANTIALIASING · KEY_TEXT_ANTIALIASING", "oro"),
        ("Escalado virtual 1280×720", "escala = min(w/1280, h/720) · mapearAMundoVirtual(e)", "cian"),
        ("Screen shake + cámara Lerp", "gw.translate(-camaraX, 0) · dt * 6.5", "cian"),
        ("Parallax procedural", "sol 0.05 · ruinas 0.18 · árboles 0.45", "verde"),
    ]
    w = 6.0
    hh, gap = 0.76, 0.12
    texto(s, CONT_X, CONT_Y - 0.05, w, 0.28, "paintComponent(Graphics g)  ·  capas en orden",
          tam=11, fuente=MONO, color="gris", negrita=True)
    y = CONT_Y + 0.3
    for i, (t, det, col) in enumerate(capas):
        rect(s, CONT_X, y, w, hh)
        circulo(s, CONT_X + 0.18, y + hh / 2 - 0.2, 0.4, col, txt=str(i + 1), tam=12)
        texto(s, CONT_X + 0.75, y + 0.06, w - 0.9, 0.34, t, tam=14, negrita=True)
        texto(s, CONT_X + 0.75, y + 0.4, w - 0.9, 0.3, det, tam=11, fuente=MONO, color="txt2")
        y += hh + gap
    # Audio
    x = 6.95
    wr = SLIDE_W - MARGEN - x
    texto(s, x, CONT_Y - 0.05, wr, 0.28, "audio.GestorSonido  ·  ondas sintetizadas en memoria",
          tam=11, fuente=MONO, color="gris", negrita=True)
    rect(s, x, CONT_Y + 0.3, wr, 3.35)
    imagen_ajustada(s, rec["ondas"], x + 0.05, CONT_Y + 0.35, wr - 0.1, 3.25)
    stats = [("44100 Hz", "PCM 16 bits mono", "cian"), ("10", "voces (MAX_VOCES)", "oro"),
             ("0", "archivos .wav", "verde")]
    sw = (wr - 2 * 0.15) / 3
    for i, (n, et, col) in enumerate(stats):
        xx = x + i * (sw + 0.15)
        rect(s, xx, CONT_Y + 3.82, sw, CONT_BOTTOM - CONT_Y - 3.82)
        texto(s, xx, CONT_Y + 3.9, sw, 0.45, n, tam=22, negrita=True, color=col, alin=PP_ALIGN.CENTER)
        texto(s, xx, CONT_Y + 4.38, sw, 0.3, et, tam=11, color="txt2", alin=PP_ALIGN.CENTER)


def d07_fisica(prs, rec):
    s = nueva_diapositiva(prs, 7, "Física balística",
                          "Física balística, tecla X (5 % / 100 %) e IA", NOTAS[7], kicker="cian")
    w = 4.55
    # Ecuacion
    rect(s, CONT_X, CONT_Y, w, 1.28)
    texto(s, CONT_X + 0.2, CONT_Y + 0.1, w - 0.4, 0.28, "Arma.calcularVelocidadInicial(potencia)",
          tam=11, fuente=MONO, color="cian", negrita=True)
    texto(s, CONT_X + 0.2, CONT_Y + 0.42, w - 0.4, 0.4,
          [[("v", {}), ("0", {"tam": 12}), (" = 175 + p · (vBase + vExtra − 175)", {})]],
          tam=16, negrita=True)
    texto(s, CONT_X + 0.2, CONT_Y + 0.86, w - 0.4, 0.3, "p ∈ [0.05, 1.00]   ·   GRAVEDAD_BASE = 540.0",
          tam=11, fuente=MONO, color="txt2")
    bloque_codigo(s, CONT_X, CONT_Y + 1.43, w, 1.42, """
vx += aceleracionViento * dt;
vy += ConstantesJuego.GRAVEDAD_BASE
      * factorGravedad * dt;
x += vx * dt;  y += vy * dt;""", tam=11, titulo="Proyectil.actualizarConViento(dt, viento)",
                  color_titulo="cian")
    # IA
    yia = CONT_Y + 3.0
    rect(s, CONT_X, yia, w, CONT_BOTTOM - yia)
    texto(s, CONT_X + 0.2, yia + 0.1, w - 0.4, 0.28, "IA · simularTrayectoria(...)", tam=11,
          fuente=MONO, color="rojo", negrita=True)
    texto(s, CONT_X + 0.2, yia + 0.38, w - 0.4, 0.5,
          "Busca ángulo 122°–152° y potencia 0.45–1.0 + error",
          tam=12, color="txt2")
    # mini barras errorMaximo por turno
    errores = [max(0.015, 0.14 - (t - 1) * 0.025) for t in range(1, 7)]
    bx, by, bh_max = CONT_X + 0.3, CONT_BOTTOM - 0.36, 0.6
    bw = 0.34
    for k, e in enumerate(errores):
        h = bh_max * e / 0.14
        xx = bx + k * (bw + 0.14)
        r_ = rect(s, xx, by - h, bw, h, relleno="rojo", borde=None, radio=0.04)
        texto(s, xx - 0.1, by + 0.02, bw + 0.2, 0.25, f"T{k + 1}", tam=10, color="txt2",
              alin=PP_ALIGN.CENTER)
    texto(s, bx + 6 * (bw + 0.14) + 0.1, by - 0.6, 1.3, 0.62,
          ["errorMaximo", "0.14 → 0.015"], tam=10.5, color="txt2", fuente=MONO)
    # Grafica
    xg = CONT_X + w + 0.25
    imagen_ajustada(s, rec["trayectorias"], xg, CONT_Y, SLIDE_W - MARGEN - xg, CONT_BOTTOM - CONT_Y)


def d08_abstraccion(prs, rec):
    s = nueva_diapositiva(prs, 8, "Pilares POO 1 y 2", "Abstracción y encapsulamiento", NOTAS[8])
    w_izq = 6.55
    texto(s, CONT_X, CONT_Y - 0.05, w_izq, 0.3, "ABSTRACCIÓN · contratos sin implementación", tam=11,
          color="gris", negrita=True)
    contratos = [
        ("interface", "Renderizable", "renderizar(Graphics2D g)", "cian"),
        ("interface", "Atacable", "recibirDano(int) · estaVivo()", "cian"),
        ("interface", "ModoJuego", "actualizarLogica(double dt)", "cian"),
        ("abstract", "EntidadJuego", "actualizar(double dt)", "oro"),
        ("abstract", "Arma", "atacar(...) · getFactorGravedad()", "oro"),
        ("abstract", "Combatiente", "actualizarComportamiento(dt)", "oro"),
        ("abstract", "Zombie", "dibujarCuerpoZombieBase(...)", "oro"),
        ("abstract", "BaseModoJuego", "dispararConTeclaX(potencia)", "oro"),
    ]
    cw, ch, g = (w_izq - 0.2) / 2, 0.98, 0.155
    for k, (est, nom, met, col) in enumerate(contratos):
        xx = CONT_X + (k % 2) * (cw + 0.2)
        yy = CONT_Y + 0.3 + (k // 2) * (ch + g)
        rect(s, xx, yy, cw, ch)
        texto(s, xx + 0.18, yy + 0.1, cw - 0.3, 0.25, f"«{est}»", tam=10, color=col, italica=True)
        texto(s, xx + 0.18, yy + 0.32, cw - 0.3, 0.3, nom, tam=14, negrita=True, fuente=MONO)
        texto(s, xx + 0.18, yy + 0.64, cw - 0.3, 0.28, met, tam=10.5, fuente=MONO, color="txt2")
    # Encapsulamiento
    x = CONT_X + w_izq + 0.35
    wr = SLIDE_W - MARGEN - x
    texto(s, x, CONT_Y - 0.05, wr, 0.3, "ENCAPSULAMIENTO · estado private + métodos validados",
          tam=11, color="gris", negrita=True)
    clases = [("Inventario", "verde"), ("Suministro", "verde"), ("Proyectil", "rojo"), ("Batallon", "oro")]
    cx = x
    for nom, col in clases:
        cw2 = 0.085 * len(nom) + 0.38
        pildora(s, cx, CONT_Y + 0.3, cw2, 0.34, nom, col, tam=11, fuente=MONO)
        cx += cw2 + 0.1
    bloque_codigo(s, x, CONT_Y + 0.82, wr, 2.6, """
private TipoSuministro tipo;
private int cantidad;      // nadie lo toca directo

public boolean consumirUno() {
    if (cantidad <= 0) return false;
    cantidad--;
    return true;
}""", tam=11.5, titulo="inventario/Suministro.java", color_titulo="verde")
    rect(s, x, CONT_Y + 3.57, wr, CONT_BOTTOM - CONT_Y - 3.57)
    texto(s, x + 0.2, CONT_Y + 3.67, wr - 0.4, CONT_BOTTOM - CONT_Y - 3.77,
          [[("Nunca hay munición o botiquines negativos: ", {"color": "txt", "negrita": True}),
            ("el estado solo cambia vía consumirUno(), recargar(), recibirDano() y "
             "ConstantesJuego.limitar().", {})]], tam=12.5, color="txt2")


def d09_herencia(prs, rec):
    s = nueva_diapositiva(prs, 9, "Pilar POO 3", "Herencia en personajes, armas y modos", NOTAS[9])
    imagen_ajustada(s, rec["herencia"], CONT_X, CONT_Y, 7.2, CONT_BOTTOM - CONT_Y, centrar=False)
    x = CONT_X + 7.4
    wr = SLIDE_W - MARGEN - x
    filas = [
        ("Zombie* (×3)", "x, y, vida, armadura, calcularDano", "velocidad, danoAtaque, escala", "rojo"),
        ("SaqueadorRival", "anguloApuntado, armaActual", "posicionTiroX, disparoPendiente", "rojo"),
        ("Superviviente", "inventario, dibujarBarraVida", "animCorteKatana, escudoTemporal", "verde"),
        ("Batallon", "vida (global), recibirDano", "miembros, esJugador, totalMiembros", "verde"),
        ("4 armas", "danoBase, municion, cadencia", "getFactorGravedad(), atacar(...)", "oro"),
        ("3 modos", "camaraX, proyectiles, tecla X", "dibujarEscena(g), lógica propia", "cian"),
    ]
    texto(s, x, CONT_Y - 0.05, wr, 0.28, "HEREDA  vs  ESPECIALIZA", tam=11, color="gris", negrita=True)
    y = CONT_Y + 0.28
    hh, gap = 0.66, 0.1
    for nom, her, esp, col in filas:
        rect(s, x, y, wr, hh)
        texto(s, x + 0.15, y + 0.06, wr - 0.3, 0.26, nom, tam=12, negrita=True, fuente=MONO, color=col)
        texto(s, x + 0.15, y + 0.33, wr - 0.3, 0.3,
              [[("↑ ", {"color": "gris"}), (her, {"color": "txt2"}), ("   + ", {"color": col}),
                (esp, {"color": "txt"})]], tam=9.5)
        y += hh + gap


def d10_polimorfismo(prs, rec):
    s = nueva_diapositiva(prs, 10, "Pilar POO 4", "Polimorfismo: sobreescritura vs sobrecarga", NOTAS[10])
    w = (CONT_W - 0.3) / 2
    # Izquierda: dinamico
    x = CONT_X
    pildora(s, x, CONT_Y - 0.02, 2.7, 0.36, "DINÁMICO · @Override", "rojo", tam=12)
    bloque_codigo(s, x, CONT_Y + 0.46, w, 1.05, """
// entidades/Batallon.dispararEnUnisono(...)
return armaActual.atacar(xOrigen, yOrigen, angulo,
                         potencia, esJugador);""", tam=11)
    armas = [
        ("RifleAsalto", "ráfaga ×3 · BALA_RIFLE · crítico 1.35", "oro"),
        ("LanzaGranadas", "GRANADA · AoE radioExplosion 145.0", "rojo"),
        ("Revolver", "BALA_PESADA · crítico 1.65×", "txt"),
        ("EspadaKatana", "HOJA_KATANA · ignora armadura · munición -1 (infinita)", "cian"),
    ]
    y = CONT_Y + 1.66
    hh, gap = 0.62, 0.12
    for nom, desc, col in armas:
        rect(s, x, y, w, hh)
        circulo(s, x + 0.18, y + hh / 2 - 0.08, 0.16, col)
        texto(s, x + 0.48, y, 1.85, hh, nom, tam=12.5, negrita=True, fuente=MONO, color=col,
              ancla=MSO_ANCHOR.MIDDLE)
        texto(s, x + 2.35, y, w - 2.5, hh, desc, tam=11.5, color="txt2", ancla=MSO_ANCHOR.MIDDLE)
        y += hh + gap
    # Derecha: estatico
    x = CONT_X + w + 0.3
    pildora(s, x, CONT_Y - 0.02, 2.7, 0.36, "ESTÁTICO · sobrecarga", "cian", tam=12)
    bloque_codigo(s, x, CONT_Y + 0.46, w, 2.2, """
public int calcularDano(int base) {
    return calcularDano(base, 1.0, false);
}
public int calcularDano(int base, double multiplicadorCritico) {
    return calcularDano(base, multiplicadorCritico, false);
}
public int calcularDano(int base, double multiplicadorCritico,
                        boolean ignoraArmadura) { ... }""", tam=10.5,
                  titulo="entidades/Combatiente.java", color_titulo="cian")
    ctor = [("Proyectil(...)", "8 ó 12 parámetros"), ("Suministro(...)", "(tipo, cantidad) · + (x, y)"),
            ("Zombie(...)", "7 ó 8 parámetros (+ escala)")]
    y = CONT_Y + 2.84
    texto(s, x, y, w, 0.28, "SOBRECARGA DE CONSTRUCTORES", tam=10.5, color="gris", negrita=True)
    y += 0.32
    hh = (CONT_BOTTOM - y - 2 * 0.12) / 3
    for nom, desc in ctor:
        rect(s, x, y, w, hh)
        texto(s, x + 0.2, y, 2.2, hh, nom, tam=12, fuente=MONO, negrita=True, color="cian",
              ancla=MSO_ANCHOR.MIDDLE)
        texto(s, x + 2.4, y, w - 2.55, hh, desc, tam=11.5, color="txt2", ancla=MSO_ANCHOR.MIDDLE)
        y += hh + 0.12


def d11_composicion(prs, rec):
    s = nueva_diapositiva(prs, 11, "Pilar POO 5", "Composición fuerte: Batallon *-- MiembroEscuadron",
                          NOTAS[11], kicker="oro")
    w = 5.85
    # Diagrama nativo
    rect(s, CONT_X, CONT_Y, w, 1.55)
    pildora(s, CONT_X + 0.2, CONT_Y + 0.55, 1.5, 0.46, "Batallon", "oro", tam=13, fuente=MONO)
    d = s.shapes.add_shape(MSO_SHAPE.DIAMOND, Inches(CONT_X + 1.7), Inches(CONT_Y + 0.66),
                           Inches(0.3), Inches(0.24))
    sin_sombra(d)
    d.fill.solid()
    d.fill.fore_color.rgb = rgb("oro")
    d.line.fill.background()
    conector(s, CONT_X + 2.0, CONT_Y + 0.78, CONT_X + 2.55, CONT_Y + 0.78, "oro", 1.5, punta=False)
    texto(s, CONT_X + 2.02, CONT_Y + 0.36, 0.5, 0.3, "4", tam=10, color="oro", fuente=MONO)
    estados = [("verde", "vivo"), ("verde", "vivo"), ("verde", "vivo"), ("rojo", "caído")]
    for k, (col, et) in enumerate(estados):
        xx = CONT_X + 2.6 + k * 0.8
        circulo(s, xx + 0.1, CONT_Y + 0.42, 0.5, col if col == "rojo" else "card", borde=col,
                txt="✕" if col == "rojo" else str(k), tam=12,
                color_txt="bg" if col == "rojo" else "verde")
        texto(s, xx - 0.05, CONT_Y + 0.96, 0.8, 0.25, et, tam=10, color=col, alin=PP_ALIGN.CENTER)
    texto(s, CONT_X + 0.2, CONT_Y + 1.2, w - 0.4, 0.3, "MiembroEscuadron: private static final · nace y muere con su Batallon",
          tam=10.5, color="txt2")
    rect(s, CONT_X, CONT_Y + 1.72, w, CONT_BOTTOM - CONT_Y - 1.72)
    imagen_ajustada(s, rec["batallon"], CONT_X + 0.05, CONT_Y + 1.78, w - 0.1,
                    CONT_BOTTOM - CONT_Y - 1.84)
    # Codigo
    x = CONT_X + w + 0.3
    wr = SLIDE_W - MARGEN - x
    bloque_codigo(s, x, CONT_Y, wr, CONT_BOTTOM - CONT_Y, """
private static final class MiembroEscuadron { ... }
private final List<MiembroEscuadron> miembros = new ArrayList<>();

private void inicializarMiembros() {    // nacen dentro
    miembros.add(new MiembroEscuadron(-52, 0, ...));
    // ... 4 miembros en total (totalMiembros = 4)
}
private void actualizarMiembrosSegunVida() {
    double pct = (double) vida / (double) vidaMaxima;
    int vivosObjetivo = (vida <= 0) ? 0
        : (int) Math.ceil(pct * totalMiembros);
    ...
}
public void destruirBatallon() {        // mueren con él
    this.vida = 0;
    this.activo = false;
    this.miembros.clear();
}""", tam=11, titulo="entidades/Batallon.java", color_titulo="oro")


def d12_agregacion(prs, rec):
    s = nueva_diapositiva(prs, 12, "Pilar POO 6", "Agregación débil: Inventario o-- Arma / Suministro",
                          NOTAS[12], kicker="verde")
    w = 6.75
    rect(s, CONT_X, CONT_Y, w, CONT_BOTTOM - CONT_Y)
    # raiz
    pildora(s, CONT_X + 1.6, CONT_Y + 0.22, 3.55, 0.46, "WalkingBowmastersPOO", "oro", tam=13, fuente=MONO)
    conector(s, CONT_X + 3.375, CONT_Y + 0.68, CONT_X + 3.375, CONT_Y + 1.12, "oro", 1.5)
    texto(s, CONT_X + 3.5, CONT_Y + 0.72, 3.0, 0.3, "new Inventario()", tam=10.5, fuente=MONO, color="oro")
    # inventario
    rect(s, CONT_X + 1.35, CONT_Y + 1.12, 4.05, 1.0, relleno="card2", borde="verde", grosor=1.75)
    texto(s, CONT_X + 1.35, CONT_Y + 1.18, 4.05, 0.32, "inventarioCompartido", tam=14, negrita=True,
          fuente=MONO, color="verde", alin=PP_ALIGN.CENTER)
    texto(s, CONT_X + 1.35, CONT_Y + 1.52, 4.05, 0.5, "4 Arma  ·  Suministro*  ·  recursosAcumulados",
          tam=11, fuente=MONO, color="txt2", alin=PP_ALIGN.CENTER)
    # tres modos
    modos = [("Modo 1", "Superviviente", "rojo"), ("Modo 2", "Batallon", "cian"),
             ("Modo 3", "Superviviente", "verde")]
    mw = 1.85
    gx = (w - 0.4 - 3 * mw) / 2
    ym = CONT_Y + 3.0
    for k, (m, quien, col) in enumerate(modos):
        xx = CONT_X + 0.2 + k * (mw + gx)
        rect(s, xx, ym, mw, 1.05, borde=col, grosor=1.5)
        texto(s, xx, ym + 0.1, mw, 0.32, m, tam=13, negrita=True, color=col, alin=PP_ALIGN.CENTER)
        texto(s, xx, ym + 0.5, mw, 0.3, quien, tam=11, fuente=MONO, color="txt2", alin=PP_ALIGN.CENTER)
        # rombo hueco en el lado del todo (Combatiente o-- Inventario)
        dx = xx + mw / 2
        d = s.shapes.add_shape(MSO_SHAPE.DIAMOND, Inches(dx - 0.12), Inches(ym - 0.3),
                               Inches(0.24), Inches(0.3))
        sin_sombra(d)
        d.fill.solid()
        d.fill.fore_color.rgb = rgb("card")
        d.line.color.rgb = rgb("verde")
        d.line.width = Pt(1.5)
        conector(s, dx, ym - 0.3, CONT_X + 3.375 + (k - 1) * 1.3, CONT_Y + 2.12, "verde", 1.5)
    texto(s, CONT_X + 0.2, CONT_Y + 4.25, w - 0.4, 0.45,
          "Misma referencia en los 3 modos: si cambias de modo o cae un combatiente, armas y "
          "suministros persisten.", tam=12, color="txt2")
    # Derecha: codigo + flujo
    x = CONT_X + w + 0.3
    wr = SLIDE_W - MARGEN - x
    bloque_codigo(s, x, CONT_Y, wr, 1.45, """
private final Inventario inventarioCompartido
        = new Inventario();
modoDuelo = new ModoDueloBatallones(
        inventarioCompartido, escenario);""", tam=11, titulo="WalkingBowmastersPOO.java",
                  color_titulo="oro")
    pasos = [
        ("rojo", "Modo 2 · te impactan", "inventario.robarSuministroAleatorio(rng)",
         "−1 suministro y −15 recursos"),
        ("verde", "Modo 2 · aciertas", "sumarPuntosRecurso(40)", "55 % de botín: CAJA_MUNICION o BOTIQUIN"),
        ("oro", "Modo 3 · armería", "comprarSuministroConBotin(tipo, costo)",
         "gasta recursosAcumulados"),
    ]
    y = CONT_Y + 1.6
    hh = (CONT_BOTTOM - y - 2 * 0.12) / 3
    for col, t, met, desc in pasos:
        rect(s, x, y, wr, hh)
        circulo(s, x + 0.17, y + 0.14, 0.22, col)
        texto(s, x + 0.5, y + 0.06, wr - 0.6, 0.32, t, tam=13, negrita=True, ancla=MSO_ANCHOR.MIDDLE)
        texto(s, x + 0.2, y + 0.4, wr - 0.35, 0.26, met, tam=10.5, fuente=MONO, color=col)
        texto(s, x + 0.2, y + 0.64, wr - 0.35, 0.26, desc, tam=11, color="txt2")
        y += hh + 0.12


def d13_runtime(prs, rec):
    s = nueva_diapositiva(prs, 13, "Diagrama de objetos",
                          "Fotografía en memoria: duelo 1v1 con la granada en vuelo", NOTAS[13], kicker="cian")
    imagen_ajustada(s, rec["objetos"], CONT_X, CONT_Y, CONT_W, CONT_BOTTOM - CONT_Y)


def d14_cierre(prs, rec):
    s = nueva_diapositiva(prs, 14, "Sustentación y demo", "Preguntas del docente y demo en vivo",
                          NOTAS[14])
    w = 7.0
    preguntas = [
        ("¿Composición vs agregación?",
         "Batallon *-- MiembroEscuadron (destruirBatallon) · Inventario o-- Arma/Suministro", "oro"),
        ("¿Polimorfismo estático vs dinámico?",
         "Combatiente.calcularDano(...) ×3 · armaActual.atacar(...) con @Override", "rojo"),
        ("¿60 FPS sin congelar el audio?",
         "Timer(16, this) en el EDT + ExecutorService daemon en GestorSonido", "cian"),
        ("¿Por qué las balas no atraviesan?",
         "actionPerformed(): dt = Math.min(0.05, ...) limita cada paso de física", "verde"),
    ]
    texto(s, CONT_X, CONT_Y - 0.05, w, 0.28, "MATRIZ DE SUSTENTACIÓN", tam=11, color="gris", negrita=True)
    y = CONT_Y + 0.28
    hh, gap = 0.94, 0.13
    for q, a, col in preguntas:
        rect(s, CONT_X, y, w, hh)
        circulo(s, CONT_X + 0.18, y + 0.17, 0.3, col, txt="?", tam=11)
        texto(s, CONT_X + 0.62, y + 0.12, w - 0.8, 0.32, q, tam=14, negrita=True)
        texto(s, CONT_X + 0.62, y + 0.48, w - 0.8, 0.4, a, tam=10.5, fuente=MONO, color="txt2")
        y += hh + gap
    # Demo
    x = CONT_X + w + 0.35
    wr = SLIDE_W - MARGEN - x
    texto(s, x, CONT_Y - 0.05, wr, 0.28, "DEMO EN VIVO · 60 SEGUNDOS", tam=11, color="gris", negrita=True)
    pasos = [
        ("0–10 s", "Menú con cursor", "detectarHoverMenu", "oro"),
        ("10–25 s", "Modo 1: Katana + Rifle", "ráfaga ×3 y corte cuerpo a cuerpo", "rojo"),
        ("25–45 s", "Modo 2: viento + granada", "cae un MiembroEscuadron", "cian"),
        ("45–60 s", "Modo 3: tecla X", "Blanco 5% y Blanco 100%", "verde"),
    ]
    y = CONT_Y + 0.28
    hh = 0.94
    for k, (t, titulo, det, col) in enumerate(pasos):
        if k < len(pasos) - 1:
            conector(s, x + 0.5, y + 0.7, x + 0.5, y + hh + gap + 0.1, "borde", 1.5, punta=False)
        pildora(s, x, y + 0.12, 1.0, 0.36, t, col, tam=10.5, relleno="bg")
        texto(s, x + 1.18, y + 0.08, wr - 1.2, 0.32, titulo, tam=14, negrita=True)
        texto(s, x + 1.18, y + 0.45, wr - 1.2, 0.3, det, tam=11, color="txt2",
              fuente=MONO if k == 0 else FUENTE)
        y += hh + gap


# =============================================================================
# NOTAS DEL ORADOR (12-15 minutos en total)
# =============================================================================
NOTAS = {
    1: """[~1 min · Apertura, nivel intuitivo]
"Imaginen unir la puntería con trayectorias curvas de Bowmasters con el mundo de supervivencia de The Walking Dead. Todo lo que ven en pantalla —desde los edificios en ruinas hasta las explosiones y los sonidos de disparos— está dibujado y sintetizado matemáticamente por el propio código en Java, sin usar imágenes ni audios externos."
Por qué sin recursos externos: el juego es 100 % Java estándar. Cada personaje es Graphics2D (rectángulos redondeados, polígonos, elipses) y cada sonido es una onda PCM generada en memoria por audio.GestorSonido. Así el proyecto compila y corre en cualquier JDK sin carpetas de assets.
Presentar los cuatro sellos: 60 FPS, Swing + audio PCM, 9 paquetes y 3 modos jugables.""",
    2: """[~1 min · Visión general]
Analogía del campamento: WalkingBowmastersPOO es el director de orquesta; recibe clics, cursor y teclas y le dice al modo activo qué actualizar 60 veces por segundo. El Inventario es la mochila del campamento: no pertenece a un personaje, viaja entre los tres escenarios.
Modo 1 (ModoSupervivenciaHordas): defender la barricada contra ZombieCaminante, ZombieCorredor, ZombieBlindado y SaqueadorRival.
Modo 2 (ModoDueloBatallones): dos escuadrones separados por un AUTOBUS y un COCHE se disparan por turnos con viento; la IA afina su puntería.
Modo 3 (ModoArmeriaCampoTiro): gastar botín y calibrar armas contra Blanco 5%, Blanco Medio y Blanco 100%.""",
    3: """[~1 min · Arquitectura]
Pasamos de un archivo monolítico a 9 paquetes + la clase raíz (34 archivos .java, ~4.455 líneas). Ventajas: cada paquete tiene una responsabilidad, los cambios quedan localizados y el código se puede explicar por capas.
Las flechas del diagrama son los import reales. El control fluye hacia abajo: la raíz crea los modos y el inventarioCompartido; los modos orquestan entidades, armas, efectos, escenario y audio; todo descansa sobre interfaces/ y util/.
Honestidad técnica: armas, entidades e inventario forman un núcleo de dominio con referencias mutuas (Combatiente tiene un Arma y Arma crea Proyectil). Es una dependencia cíclica entre paquetes, aceptable porque los tres modelan el mismo dominio de combate; lo importante es que nada importa modos/ ni la clase raíz.""",
    4: """[~45 s · Librerías]
Todo es JDK estándar: no hay Maven ni librerías de terceros.
Swing da la ventana, el JPanel con double buffering y el Timer(16, this), que dispara actionPerformed cada 16 ms (≈60 FPS) en el Event Dispatch Thread.
AWT y java.awt.geom dibujan todo de forma vectorial con coordenadas double.
java.util aporta las colecciones; se usa Iterator.remove() para eliminar proyectiles y zombies mientras se recorren las listas sin ConcurrentModificationException.
javax.sound.sampled reproduce PCM 16 bits a 44100 Hz por SourceDataLine, y java.util.concurrent mantiene un pool de hilos daemon para que el audio nunca bloquee el render.""",
    5: """[~1 min 15 s · Game loop y estados]
El ciclo: (1) los listeners de ratón y teclado registran la entrada; (2) el Timer llama a actionPerformed(), que mide el tiempo real con System.nanoTime() y lo limita a 0.05 s; (3) actualizarLogica(dt) mueve IA, física, colisiones y partículas; (4) repaint() pide a Swing que ejecute paintComponent.
Limitar dt hace que la física sea independiente del procesador y que un microcorte no haga que una bala atraviese a un enemigo.
EstadoPantalla decide qué se dibuja: MENU_PRINCIPAL o JUGANDO_MODO_1/2/3; la barra superior (manejarClicBarraSuperior) permite saltar de modo.
En el duelo, FaseTurno: TURNO_JUGADOR → PROYECTIL_EN_VUELO (la cámara sigue al proyectil) → PAUSA_IMPACTO (1.05 s) → TURNO_IA, que espera 1.0 s, dispara y vuelve a PROYECTIL_EN_VUELO; FIN_DUELO cuando cae un batallón.""",
    6: """[~1 min · Render y audio]
paintComponent dibuja por capas: double buffering (sin parpadeo), antialiasing, escalado a un mundo virtual de 1280×720 (mapearAMundoVirtual invierte la transformación para que el clic coincida en cualquier resolución), screen shake por explosiones y cámara con Lerp: camaraX += (camaraObjetivoX - camaraX) * Math.min(1.0, dt * 6.5).
El Parallax mueve el sol a 0.05, las ruinas a 0.18 y los árboles a 0.45 de la velocidad de la cámara: profundidad 3D en 2D.
Las ondas de la derecha son la réplica numérica de sintetizarDisparo y sintetizarBarrido: tono con barrido de frecuencia + ruido filtrado y envolvente. El CACHE las genera una vez y el ExecutorService las reproduce en paralelo (hasta 10 voces).""",
    7: """[~1 min 30 s · Física balística]
Cada arma define factorGravedad, velocidadBase y velocidadExtra. calcularVelocidadInicial interpola linealmente entre 175 px/s (5 %) y vBase + vExtra (100 %).
En cada fotograma actualizarConViento integra con Euler: el viento acelera vx, la gravedad (540 × factor) acelera vy. Recordar que en Swing el eje Y crece hacia abajo: por eso vy = -v0·sin(ángulo).
La gráfica simula 45° desde la boca del arma (56 px sobre Y_SUELO). Al 5 % los tiros caen a pocos píxeles; al 100 % el RifleAsalto (g = 0.45) llega mucho más lejos que el LanzaGranadas (g = 1.0), que compensa con daño en área de 145 px. La línea discontinua muestra cómo el viento de -48.5 acorta la granada.
Tecla X: dispara al instante con el preset 5 % o 100 % hacia el cursor.
IA: simularTrayectoria prueba combinaciones de ángulo y potencia, elige la mejor y añade un error que baja de 0.14 a un mínimo de 0.015 cada turno.""",
    8: """[~1 min · Abstracción y encapsulamiento]
Abstracción: el motor trabaja contra contratos. Renderizable, Atacable y ModoJuego son interfaces; EntidadJuego, Arma, Combatiente, Zombie y BaseModoJuego son clases abstractas con métodos abstractos que cada subclase debe implementar. WalkingBowmastersPOO solo conoce un BaseModoJuego modoActivo, no le importa cuál.
Encapsulamiento: los atributos sensibles son private (miembros en Batallon, armas/suministros/recursosAcumulados en Inventario, cantidad en Suministro, la física en Proyectil, CACHE y sonidoActivo en GestorSonido). Solo cambian por métodos que validan: consumirUno() nunca deja cantidades negativas.""",
    9: """[~1 min · Herencia]
Árbol principal: EntidadJuego (x, y, vida, activo) → Combatiente (nombre, armadura, anguloApuntado, armaActual, inventario, calcularDano, dibujarBarraVida) → Superviviente, Zombie, SaqueadorRival y Batallon. Zombie añade velocidad y ataque, y sus tres hijos solo cambian apariencia y comportamiento.
Arma concentra munición, cadencia y calcularVelocidadInicial; las 4 armas solo definen su física y su ataque.
BaseModoJuego reutiliza cámara, partículas, guía parabólica y tecla X en los 3 modos.
La tabla muestra qué recibe cada clase por herencia y qué agrega por sí misma.""",
    10: """[~1 min 15 s · Polimorfismo]
Dinámico (en tiempo de ejecución): Batallon y Superviviente llaman siempre armaActual.atacar(...). Según el objeto real, Java ejecuta la versión @Override de RifleAsalto (ráfaga de 3), LanzaGranadas (granada AoE), Revolver (crítico 1.65) o EspadaKatana (hoja que ignora armadura). Además, Arma tiene la sobrecarga atacar(..., faccionJugador), que reutiliza la versión abstracta.
Estático (en compilación): calcularDano tiene 3 firmas; las cortas delegan en la completa, que aplica crítico y armadura (reducción = armadura × 0.55, daño mínimo 2). Lo mismo pasa con los constructores de Proyectil, Suministro, Combatiente y Zombie.""",
    11: """[~1 min · Composición]
MiembroEscuadron es una clase private static final dentro de Batallon: ninguna clase externa puede crearla ni guardarla. Los 4 miembros nacen en inicializarMiembros() dentro del constructor y desaparecen con destruirBatallon(), que limpia la lista: ciclo de vida dependiente = composición fuerte.
El Batallon tiene una sola vida global (320). Cada recibirDano llama a actualizarMiembrosSegunVida, que calcula ceil(pct × 4): de 320 a 241 HP hay 4 vivos, a 240 (75 %) quedan 3, a 160 (50 %) 2, a 80 (25 %) 1 y en 0 queda destruido.""",
    12: """[~1 min · Agregación]
inventarioCompartido nace en WalkingBowmastersPOO, fuera de cualquier personaje o modo, y se pasa por referencia a los tres modos; dentro de ellos se inyecta en Superviviente y en el Batallon aliado. Si el combatiente muere, el inventario sigue existiendo: agregación débil (rombo hueco).
Flujo de botín: en el Modo 2, si te impactan, robarSuministroAleatorio quita un suministro y 15 recursos; si aciertas, sumas 40 recursos y 55 % de probabilidad de botín. En el Modo 3 se gasta con comprarSuministroConBotin. Lo que pierdes en el duelo se nota en la armería.""",
    13: """[~1 min · Diagrama de objetos]
Esta es una instantánea de la memoria durante el turno del jugador en el duelo. modoDuelo está en PROYECTIL_EN_VUELO con viento -48.5.
batallonJugador tiene 240/320 (75 %): por eso miembros[3] tiene vivo = false y progresoCaida = 1.0. Rombo relleno: composición.
El Batallon apunta al mismo inventarioCompartido que conoce app, y su armaActual es armas[1], el LanzaGranadas con municion = 9 de 24. Rombos huecos: agregación.
proyectiles[0] es la granada en vuelo (tipo GRANADA, radioExplosion 145) y obstaculos[0] es el AUTOBUS.""",
    14: """[~2 min · Cierre y demo]
Usar la matriz para responder rápido, siempre señalando clase y método.
Demo en 60 s: (1) mover el cursor en el menú para mostrar hover y sonido; (2) Modo 1: ráfaga con RifleAsalto y corte con Katana; (3) Modo 2: señalar el viento, lanzar una granada y mostrar cómo cae un MiembroEscuadron al bajar al 75 %; (4) Modo 3: tecla X al 5 % y al 100 % contra los blancos.
Cierre: "Cada pilar de la POO tiene un lugar concreto en el código y un efecto visible en pantalla." Abrir ronda de preguntas.""",
}


# =============================================================================
# VERIFICACION
# =============================================================================
def verificar(prs_path: Path, esperadas: list[Path]) -> None:
    prs = Presentation(str(prs_path))
    assert len(prs.slides) == TOTAL, f"Se esperaban {TOTAL} diapositivas, hay {len(prs.slides)}"
    imagenes = 0
    sw, sh = prs.slide_width, prs.slide_height
    for i, sl in enumerate(prs.slides, 1):
        notas = sl.notes_slide.notes_text_frame.text if sl.has_notes_slide else ""
        assert len(notas) > 80, f"Diapositiva {i} sin notas del orador"
        for sh_ in sl.shapes:
            if sh_.shape_type == 13:  # PICTURE
                imagenes += 1
            if i > 1 and sh_.shape_type != 13:
                assert sh_.left >= 0 and sh_.top >= 0, f"Forma fuera de lienzo en diapositiva {i}"
                assert sh_.left + sh_.width <= sw + Emu(1000), f"Desborde horizontal en {i}"
                assert sh_.top + sh_.height <= sh + Emu(1000), f"Desborde vertical en {i}"
    for r in esperadas:
        assert r.exists() and r.stat().st_size > 10_000, f"Recurso faltante o vacío: {r.name}"
    print(f"  ✓ {len(prs.slides)} diapositivas · {imagenes} imágenes incrustadas · notas en todas")


# =============================================================================
# MAIN
# =============================================================================
def main() -> int:
    if not GUIA.exists():
        print(f"AVISO: no se encontró {GUIA.name}; se usan los datos embebidos en el script.")
    ASSETS.mkdir(exist_ok=True)
    print("1/4 Gráficas matplotlib (300 DPI)...")
    rec = {
        "trayectorias": grafica_trayectorias(),
        "batallon": grafica_batallon(),
        "ondas": grafica_ondas(),
    }
    print("2/4 Diagramas...")
    motor = "Graphviz" if shutil.which("dot") else "matplotlib (fallback vectorial)"
    rec["arquitectura"] = diagrama_arquitectura()
    print(f"      motor de diagramas: {motor}")
    rec["herencia"] = diagrama_herencia()
    rec["objetos"] = diagrama_objetos()
    if shutil.which("dot"):
        alt = intentar_graphviz(DOT_ARQUITECTURA, "d1_arquitectura_graphviz.png")
        if alt:
            print(f"      versión Graphviz adicional: {alt.name}")
    print("3/4 Mockups Pillow...")
    rec.update(generar_mockups())

    print("4/4 Construyendo .pptx...")
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    for fn in (d01_portada, d02_vision, d03_arquitectura, d04_librerias, d05_gameloop, d06_render,
               d07_fisica, d08_abstraccion, d09_herencia, d10_polimorfismo, d11_composicion,
               d12_agregacion, d13_runtime, d14_cierre):
        fn(prs, rec)
    prs.core_properties.title = "The Walking Bowmasters — Edición POO Modular"
    prs.core_properties.subject = "Lógica de Programación II (POO)"
    prs.save(str(SALIDA))
    verificar(SALIDA, list(rec.values()))
    print(f"Listo: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
