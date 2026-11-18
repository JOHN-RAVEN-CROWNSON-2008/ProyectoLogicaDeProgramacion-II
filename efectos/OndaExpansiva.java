package efectos;

import util.ConstantesJuego;
import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.geom.Ellipse2D;

/**
 * Anillo de onda expansiva generado al impactar granadas o cortes criticos.
 */
public class OndaExpansiva {
    private final double x, y, radioMaximo;
    private double radioActual;
    private double vida = 0.42;
    private final double vidaMax = 0.42;
    private final Color color;

    public OndaExpansiva(double x, double y, double radioMaximo, Color color) {
        this.x = x;
        this.y = y;
        this.radioMaximo = radioMaximo;
        this.radioActual = 10.0;
        this.color = color;
    }

    public boolean actualizar(double dt) {
        vida -= dt;
        if (vida <= 0) return false;
        double progreso = 1.0 - (vida / vidaMax);
        radioActual = 10.0 + (radioMaximo - 10.0) * Math.sqrt(progreso);
        return true;
    }

    public void renderizar(Graphics2D g) {
        float alpha = (float) ConstantesJuego.limitar(vida / vidaMax, 0.0, 1.0);
        g.setColor(new Color(color.getRed(), color.getGreen(), color.getBlue(), (int) (alpha * 190)));
        g.setStroke(new BasicStroke(5f * alpha));
        g.draw(new Ellipse2D.Double(x - radioActual, y - radioActual, radioActual * 2, radioActual * 2));
        g.setStroke(new BasicStroke(1f));
    }
}
