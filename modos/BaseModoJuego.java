package modos;

import armas.*;
import audio.GestorSonido;
import efectos.*;
import entidades.Proyectil;
import escenario.EscenarioApocaliptico;
import interfaces.ModoJuego;
import inventario.Inventario;
import inventario.TipoSuministro;
import util.ConstantesJuego;
import java.awt.*;
import java.awt.geom.Ellipse2D;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Random;

/**
 * Clase base compartida para los modos jugables (Modo 1, Modo 2 y Modo 3).
 * Implementa seguimiento de cursor, sistema de disparo con Tecla X (5% y 100%),
 * fisica de particulas y renderizado de trayectoria parabolica.
 */
public abstract class BaseModoJuego implements ModoJuego {
    protected final Inventario inventario;
    protected final EscenarioApocaliptico escenario;
    protected final Random rng = new Random();
    protected final List<Proyectil> proyectiles = new ArrayList<Proyectil>();
    protected final List<Particula> particulas = new ArrayList<Particula>();
    protected final List<OndaExpansiva> ondas = new ArrayList<OndaExpansiva>();
    protected final List<TextoFlotante> textos = new ArrayList<TextoFlotante>();

    protected double camaraX = 0.0;
    protected double intensidadShake = 0.0;
    protected boolean arrastrando = false;
    protected double dragStartX, dragStartY, dragActualX, dragActualY;

    // Seguimiento de cursor y disparo rapido con Tecla X (5% o 100%)
    protected double cursorVirtualX = 640.0;
    protected double cursorVirtualY = 420.0;
    protected boolean cursorEnArena = false;
    protected boolean potenciaXAl100 = true; // true = 100%, false = 5%
    protected boolean cargandoTeclaX = false;
    protected double tiempoCargaX = 0.0;
    protected double potenciaCargaX = 0.05;

    public BaseModoJuego(Inventario inventario, EscenarioApocaliptico escenario) {
        this.inventario = inventario;
        this.escenario = escenario;
    }

    protected void generarExplosion(double ex, double ey, double radio) {
        intensidadShake = Math.max(intensidadShake, 16.0);
        GestorSonido.reproducirExplosion();
        ondas.add(new OndaExpansiva(ex, ey, radio, new Color(255, 165, 65)));
        for (int i = 0; i < 36; i++) {
            double ang = rng.nextDouble() * Math.PI * 2;
            double spd = 70 + rng.nextDouble() * 340;
            Color c = (i % 3 == 0) ? new Color(255, 220, 95)
                    : (i % 3 == 1 ? new Color(245, 95, 35) : new Color(75, 75, 80));
            particulas.add(new Particula(ex, ey, Math.cos(ang) * spd, Math.sin(ang) * spd - 60,
                    0.35 + rng.nextDouble() * 0.45, 6 + rng.nextDouble() * 10, c, i % 3 != 2));
        }
    }

    protected void generarImpacto(double ix, double iy, Color color, int cantidad) {
        for (int i = 0; i < cantidad; i++) {
            double ang = rng.nextDouble() * Math.PI * 2;
            double spd = 50 + rng.nextDouble() * 210;
            particulas.add(new Particula(ix, iy, Math.cos(ang) * spd, Math.sin(ang) * spd - 50,
                    0.25 + rng.nextDouble() * 0.35, 4 + rng.nextDouble() * 5, color, true));
        }
    }

    protected void reproducirSonidoArma(Arma arma) {
        if (arma instanceof RifleAsalto) GestorSonido.reproducirDisparoRifle();
        else if (arma instanceof LanzaGranadas) GestorSonido.reproducirLanzagranadas();
        else if (arma instanceof Revolver) GestorSonido.reproducirDisparoRevolver();
        else if (arma instanceof EspadaKatana) GestorSonido.reproducirCorteKatana();
    }

    protected void actualizarEfectos(double dt) {
        if (intensidadShake > 0) intensidadShake = Math.max(0.0, intensidadShake - dt * 38.0);

        if (cargandoTeclaX) {
            tiempoCargaX += dt;
            if (tiempoCargaX >= 0.18) {
                double progreso = ConstantesJuego.limitar((tiempoCargaX - 0.18) / 1.05, 0.0, 1.0);
                potenciaCargaX = 0.05 + progreso * 0.95;
            }
        }

        Iterator<Particula> ip = particulas.iterator();
        while (ip.hasNext()) {
            if (!ip.next().actualizar(dt)) ip.remove();
        }
        Iterator<OndaExpansiva> io = ondas.iterator();
        while (io.hasNext()) {
            if (!io.next().actualizar(dt)) io.remove();
        }
        Iterator<TextoFlotante> it = textos.iterator();
        while (it.hasNext()) {
            if (!it.next().actualizar(dt)) it.remove();
        }
    }

    protected void dibujarEfectos(Graphics2D g) {
        for (OndaExpansiva o : ondas) o.renderizar(g);
        for (Particula p : particulas) p.renderizar(g);
        for (TextoFlotante t : textos) t.renderizar(g);
    }

    protected double[] calcularVectorDisparo(double minAnguloDeg, double maxAnguloDeg) {
        double dx = dragStartX - dragActualX;
        double dy = dragStartY - dragActualY;
        if (dragActualX > dragStartX + 18) {
            dx = dragActualX - dragStartX;
            dy = dragActualY - dragStartY;
        }
        double dist = Math.hypot(dx, dy);
        double potencia = ConstantesJuego.limitar(dist / 175.0, 0.05, 1.0);
        double angulo = Math.atan2(-dy, Math.max(12.0, Math.abs(dx)));
        double minRad = Math.toRadians(minAnguloDeg);
        double maxRad = Math.toRadians(maxAnguloDeg);
        angulo = ConstantesJuego.limitar(angulo, minRad, maxRad);
        return new double[]{angulo, potencia};
    }

    protected double calcularAnguloHaciaCursor(double xOrigen, double yOrigen, double minDeg, double maxDeg) {
        double mundoCursorX = cursorVirtualX + camaraX;
        double dx = Math.max(20.0, mundoCursorX - xOrigen);
        double dy = yOrigen - cursorVirtualY;
        double ang = Math.atan2(dy, dx);
        return ConstantesJuego.limitar(ang, Math.toRadians(minDeg), Math.toRadians(maxDeg));
    }

    protected void dibujarGuiaParabolica(Graphics2D g, double x0, double y0,
                                         double angulo, double potencia, Arma arma,
                                         double viento, boolean modoSutil) {
        if (arma == null) return;
        double v0 = arma.calcularVelocidadInicial(potencia);
        double vx = v0 * Math.cos(angulo);
        double vy = -v0 * Math.sin(angulo);
        double gEff = ConstantesJuego.GRAVEDAD_BASE * arma.getFactorGravedad();

        int maxPuntos = modoSutil ? 12 : 18;
        float alphaBase = modoSutil ? 120f : 225f;
        for (int i = 1; i <= maxPuntos; i++) {
            double t = i * 0.052;
            double px = x0 + vx * t + 0.5 * viento * 0.35 * t * t;
            double py = y0 + vy * t + 0.5 * gEff * t * t;
            if (py > ConstantesJuego.Y_SUELO) break;
            float alpha = (1.0f - (i / (float) (maxPuntos + 2))) * (alphaBase / 255f);
            g.setColor(modoSutil
                    ? new Color(130, 225, 255, (int) (alpha * 255))
                    : new Color(255, 235, 130, (int) (alpha * 255)));
            double r = (modoSutil ? 4.8 : 6.5) - (i * 0.20);
            g.fill(new Ellipse2D.Double(px - r / 2, py - r / 2, r, r));
        }

        if (!modoSutil) {
            g.setFont(new Font("SansSerif", Font.BOLD, 13));
            String info = String.format("%d\u00b0 | %d%%", (int) Math.round(Math.toDegrees(angulo)),
                    (int) Math.round(potencia * 100));
            g.setColor(new Color(0, 0, 0, 185));
            g.fillRoundRect((int) x0 - 44, (int) y0 - 52, 88, 22, 8, 8);
            g.setColor(new Color(255, 225, 110));
            g.drawString(info, (int) x0 - 34, (int) y0 - 36);
        }
    }

    protected void dibujarBarraCargaX(Graphics2D g, double xBase, double yBase) {
        if (!cargandoTeclaX) return;
        int bx = (int) (xBase - 55);
        int by = (int) (yBase - 148);
        g.setColor(new Color(18, 22, 28, 225));
        g.fillRoundRect(bx, by, 110, 22, 8, 8);
        g.setColor(new Color(90, 205, 255));
        g.drawRoundRect(bx, by, 110, 22, 8, 8);

        double pct = (tiempoCargaX < 0.18) ? getPotenciaPresetX() : potenciaCargaX;
        g.setColor(pct >= 0.90 ? new Color(245, 95, 65) : new Color(95, 215, 165));
        g.fillRoundRect(bx + 4, by + 13, (int) Math.round(102 * pct), 5, 3, 3);
        g.setFont(new Font("SansSerif", Font.BOLD, 10));
        g.setColor(Color.WHITE);
        g.drawString("TECLA X: " + (int) Math.round(pct * 100) + "%", bx + 12, by + 11);
    }

    protected void dibujarMiraCursor(Graphics2D g) {
        if (!cursorEnArena || arrastrando) return;
        double cx = cursorVirtualX + camaraX;
        double cy = cursorVirtualY;
        g.setColor(new Color(125, 225, 255, 165));
        g.setStroke(new BasicStroke(1.6f));
        g.draw(new Ellipse2D.Double(cx - 11, cy - 11, 22, 22));
        g.drawLine((int) cx - 16, (int) cy, (int) cx - 6, (int) cy);
        g.drawLine((int) cx + 6, (int) cy, (int) cx + 16, (int) cy);
        g.drawLine((int) cx, (int) cy - 16, (int) cx, (int) cy - 6);
        g.drawLine((int) cx, (int) cy + 6, (int) cx, (int) cy + 16);
        g.setStroke(new BasicStroke(1f));
    }

    public double getPotenciaPresetX() {
        return potenciaXAl100 ? 1.00 : 0.05;
    }

    public boolean isPotenciaXAl100() { return potenciaXAl100; }

    public void setPotenciaXAl100(boolean al100) {
        this.potenciaXAl100 = al100;
        GestorSonido.reproducirClickMenu();
    }

    public void alternarPotenciaX() {
        setPotenciaXAl100(!potenciaXAl100);
    }

    public void alMoverRaton(double xVirtual, double yVirtual) {
        this.cursorVirtualX = xVirtual;
        this.cursorVirtualY = yVirtual;
        this.cursorEnArena = (yVirtual > 58 && yVirtual < 622);
    }

    public void alSoltarTecla(int keyCode, boolean shiftDown) {
        if (keyCode == java.awt.event.KeyEvent.VK_X && cargandoTeclaX) {
            cargandoTeclaX = false;
            double pot = (tiempoCargaX < 0.18)
                    ? (shiftDown ? 0.05 : getPotenciaPresetX())
                    : potenciaCargaX;
            dispararConTeclaX(pot);
        }
    }

    protected abstract void dispararConTeclaX(double potencia);
    public abstract void alPresionarRaton(double xVirtual, double yVirtual);
    public abstract void alArrastrarRaton(double xVirtual, double yVirtual);
    public abstract void alSoltarRaton(double xVirtual, double yVirtual);
    public abstract void alPresionarTecla(int keyCode, boolean shiftDown);
    public abstract void usarSuministroDesdeHud(TipoSuministro tipo);
    public abstract void equiparArmaDesdeHud(int indice);

    public double getCamaraX() { return camaraX; }
    public double getIntensidadShake() { return intensidadShake; }
}
