package efectos;

import util.ConstantesJuego;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.geom.Ellipse2D;

/**
 * Particula visual para explosiones, sangre, chispas y polvo de impacto.
 */
public class Particula {
    private double x, y, vx, vy, vida, vidaMax, tamano;
    private final Color color;
    private final boolean conGravedad;

    public Particula(double x, double y, double vx, double vy, double vidaMax,
                     double tamano, Color color, boolean conGravedad) {
        this.x = x;
        this.y = y;
        this.vx = vx;
        this.vy = vy;
        this.vida = vidaMax;
        this.vidaMax = vidaMax;
        this.tamano = tamano;
        this.color = color;
        this.conGravedad = conGravedad;
    }

    public boolean actualizar(double dt) {
        vida -= dt;
        if (vida <= 0) return false;
        if (conGravedad) {
            vy += 420.0 * dt;
        } else {
            vx *= (1.0 - 1.4 * dt);
            vy *= (1.0 - 0.8 * dt);
        }
        x += vx * dt;
        y += vy * dt;
        return true;
    }

    public void renderizar(Graphics2D g) {
        float alpha = (float) ConstantesJuego.limitar(vida / vidaMax, 0.0, 1.0);
        g.setColor(new Color(color.getRed(), color.getGreen(), color.getBlue(), (int) (alpha * 235)));
        double r = tamano * (0.4 + 0.6 * alpha);
        g.fill(new Ellipse2D.Double(x - r / 2.0, y - r / 2.0, r, r));
    }
}
