package entidades;

import armas.Revolver;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.geom.Ellipse2D;

/**
 * [POO - HERENCIA + POLIMORFISMO (@Override)]
 * Enemigo humano hostil (saqueador rival) que avanza hasta posicion de tiro
 * y dispara proyectiles parabolicos contra el jugador.
 */
public class SaqueadorRival extends Combatiente {
    private double faseIdle = 0;
    private final double velocidad = 62.0;
    private final double posicionTiroX;
    private double timerDisparo = 2.6;
    private Proyectil disparoPendiente = null;

    public SaqueadorRival(String nombre, double x, double y, double posicionTiroX) {
        super(nombre, x, y, 125, 8);
        this.posicionTiroX = posicionTiroX;
        this.mirandoDerecha = false;
        this.anguloApuntado = Math.toRadians(166);
        this.armaActual = new Revolver();
    }

    @Override
    public void actualizarComportamiento(double dt) {
        faseIdle += dt;
        if (x > posicionTiroX) {
            x -= velocidad * dt;
            animCaminata += dt * 5.0;
        } else {
            timerDisparo -= dt;
            if (timerDisparo <= 0) {
                timerDisparo = 3.2;
                animRetroceso = 1.0;
                double ang = Math.toRadians(164 + Math.random() * 6);
                double v0 = 760.0;
                disparoPendiente = new Proyectil(
                        x - 24, y - 56,
                        v0 * Math.cos(ang), -v0 * Math.sin(ang),
                        16, 0.45, false, TipoProyectil.BALA_PESADA);
            }
        }
    }

    public Proyectil recogerDisparoPendiente() {
        Proyectil p = disparoPendiente;
        disparoPendiente = null;
        return p;
    }

    @Override
    public void renderizar(Graphics2D g) {
        if (!estaVivo()) return;
        double bob = Math.sin(faseIdle * 3.0) * 1.5;
        double paso = (x > posicionTiroX) ? Math.sin(animCaminata) * 5.0 : 0.0;

        g.setColor(new Color(0, 0, 0, 110));
        g.fill(new Ellipse2D.Double(x - 18, y - 5, 36, 9));

        g.setColor(new Color(45, 40, 42));
        g.fillRoundRect((int) (x - 10 + paso), (int) y - 35, 8, 31, 3, 3);
        g.fillRoundRect((int) (x + 2 - paso), (int) y - 35, 8, 31, 3, 3);

        g.setColor((flashDano > 0.25) ? new Color(230, 90, 90) : new Color(65, 48, 46));
        g.fillRoundRect((int) x - 13, (int) (y - 70 + bob), 26, 38, 6, 6);

        g.setColor(new Color(210, 168, 135));
        g.fill(new Ellipse2D.Double(x - 9, y - 90 + bob, 18, 19));
        g.setColor(new Color(175, 35, 35));
        g.fillRoundRect((int) x - 10, (int) (y - 91 + bob), 20, 7, 3, 3);
        g.fillRect((int) x - 9, (int) (y - 79 + bob), 18, 6);

        Graphics2D ga = (Graphics2D) g.create();
        ga.translate(x - 4, y - 56 + bob);
        ga.scale(-1, 1);
        ga.rotate(-0.18 + animRetroceso * 0.18);
        ga.setColor(new Color(65, 48, 46));
        ga.fillRoundRect(-2, -3, 13, 6, 3, 3);
        ga.translate(9, 0);
        if (armaActual != null) armaActual.dibujarArmaEnMano(ga, 0.95);
        ga.dispose();

        dibujarBarraVida(g, x, y - 108, 56, 6, nombre);
    }
}
