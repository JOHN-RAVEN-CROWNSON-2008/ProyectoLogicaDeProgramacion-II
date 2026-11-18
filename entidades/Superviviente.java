package entidades;

import inventario.Inventario;
import util.ConstantesJuego;
import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.Polygon;
import java.awt.geom.Arc2D;
import java.awt.geom.Ellipse2D;
import java.util.ArrayList;
import java.util.List;

/**
 * [POO - HERENCIA + POLIMORFISMO (@Override)]
 * Protagonista principal controlado en el Modo 1 y en el Campo de Tiro (Modo 3).
 */
public class Superviviente extends Combatiente {
    private double animCorteKatana = 0.0;
    private double tiempoRespiracion = 0.0;
    private int escudoTemporal = 0;

    public Superviviente(String nombre, double x, double y, Inventario inventario) {
        super(nombre, x, y, 160, 10, inventario);
        if (inventario != null && !inventario.getArmas().isEmpty()) {
            this.armaActual = inventario.getArma(0);
        }
        this.anguloApuntado = Math.toRadians(12);
    }

    public void equiparArmaPorIndice(int idx) {
        if (inventario != null) {
            this.armaActual = inventario.getArma(idx);
        }
    }

    public List<Proyectil> disparar(double angulo, double potencia) {
        this.anguloApuntado = angulo;
        this.potenciaApuntado = potencia;
        if (armaActual == null || !armaActual.puedeDisparar()) {
            return new ArrayList<Proyectil>();
        }
        this.animRetroceso = 1.0;
        double xBoca = x + 22 * Math.cos(angulo);
        double yBoca = (y - 54) - 22 * Math.sin(angulo);
        return armaActual.atacar(xBoca, yBoca, angulo, potencia, true);
    }

    public void activarAnimacionKatana() {
        this.animCorteKatana = 1.0;
        this.animRetroceso = 0.8;
    }

    public void agregarEscudoRacion(int extra) {
        escudoTemporal = Math.min(25, escudoTemporal + extra);
    }

    @Override
    public void recibirDano(int cantidad) {
        int neto = Math.max(1, cantidad - escudoTemporal / 2);
        if (escudoTemporal > 0) escudoTemporal = Math.max(0, escudoTemporal - 2);
        super.recibirDano(neto);
    }

    @Override
    public void actualizarComportamiento(double dt) {
        tiempoRespiracion += dt;
        if (animCorteKatana > 0) {
            animCorteKatana = Math.max(0.0, animCorteKatana - dt * 4.2);
        }
    }

    @Override
    public void renderizar(Graphics2D g) {
        if (!activo && vida <= 0) return;

        double bob = Math.sin(tiempoRespiracion * 3.0) * 1.5;
        double retroX = -animRetroceso * 6.0;
        double bx = x + retroX;
        double by = y;

        g.setColor(new Color(0, 0, 0, 110));
        g.fill(new Ellipse2D.Double(bx - 20, by - 5, 40, 10));

        g.setColor(new Color(45, 52, 65));
        g.fillRoundRect((int) bx - 11, (int) by - 36, 9, 32, 4, 4);
        g.fillRoundRect((int) bx + 2, (int) by - 36, 9, 32, 4, 4);
        g.setColor(new Color(38, 28, 22));
        g.fillRoundRect((int) bx - 12, (int) by - 10, 12, 10, 3, 3);
        g.fillRoundRect((int) bx + 1, (int) by - 10, 13, 10, 3, 3);

        Color colorAbrigo = (flashDano > 0.2) ? new Color(220, 90, 90) : new Color(92, 72, 54);
        g.setColor(colorAbrigo);
        g.fill(new Polygon(
                new int[]{(int) bx - 15, (int) bx + 13, (int) bx + 16, (int) bx - 17},
                new int[]{(int) (by - 70 + bob), (int) (by - 70 + bob), (int) (by - 28 + bob), (int) (by - 26 + bob)},
                4));
        g.setColor(new Color(48, 52, 56));
        g.fillRoundRect((int) bx - 9, (int) (by - 68 + bob), 18, 32, 4, 4);
        g.setColor(new Color(145, 45, 45));
        g.fillRoundRect((int) bx - 10, (int) (by - 73 + bob), 20, 7, 4, 4);

        g.setColor(new Color(222, 182, 148));
        g.fill(new Ellipse2D.Double(bx - 9, by - 91 + bob, 18, 19));
        g.setColor(new Color(75, 55, 42, 150));
        g.fillArc((int) bx - 8, (int) (by - 83 + bob), 16, 11, 190, 160);
        g.setColor(new Color(25, 25, 30));
        g.fillOval((int) bx + 3, (int) (by - 84 + bob), 3, 3);
        g.setColor(new Color(66, 48, 34));
        g.fillRoundRect((int) bx - 16, (int) (by - 92 + bob), 32, 4, 3, 3);
        g.fillRoundRect((int) bx - 10, (int) (by - 101 + bob), 20, 11, 4, 4);
        g.setColor(new Color(135, 95, 50));
        g.fillRect((int) bx - 10, (int) (by - 94 + bob), 20, 2);

        Graphics2D ga = (Graphics2D) g.create();
        ga.translate(bx + 2, by - 58 + bob);
        ga.rotate(-anguloApuntado + animRetroceso * 0.18);
        ga.setColor(colorAbrigo);
        ga.fillRoundRect(-3, -4, 16, 8, 4, 4);
        if (armaActual != null) {
            ga.translate(10, 0);
            armaActual.dibujarArmaEnMano(ga, 1.0);
        }
        ga.dispose();

        if (animCorteKatana > 0) {
            Graphics2D gk = (Graphics2D) g.create();
            float a = (float) ConstantesJuego.limitar(animCorteKatana, 0.0, 1.0);
            gk.setColor(new Color(165, 240, 255, (int) (a * 210)));
            gk.setStroke(new BasicStroke(7f * a, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
            gk.draw(new Arc2D.Double(bx - 15, by - 115, 165, 115, -55, 115, Arc2D.OPEN));
            gk.setColor(new Color(255, 255, 255, (int) (a * 230)));
            gk.setStroke(new BasicStroke(2.5f * a));
            gk.draw(new Arc2D.Double(bx - 10, by - 110, 155, 105, -50, 105, Arc2D.OPEN));
            gk.dispose();
        }

        dibujarBarraVida(g, bx, by - 118, 62, 7, nombre);
    }
}
