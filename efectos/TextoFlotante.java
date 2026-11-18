package efectos;

import util.ConstantesJuego;
import java.awt.Color;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics2D;

/**
 * Texto flotante de combate (-HP, CRITICO, botin o alertas de turno).
 */
public class TextoFlotante {
    private final double x;
    private double y, vy, vida;
    private final double vidaMax = 1.35;
    private final String texto;
    private final Color color;
    private final int tamanoFuente;

    public TextoFlotante(double x, double y, String texto, Color color, int tamanoFuente) {
        this.x = x;
        this.y = y;
        this.vy = -52.0;
        this.vida = vidaMax;
        this.texto = texto;
        this.color = color;
        this.tamanoFuente = tamanoFuente;
    }

    public boolean actualizar(double dt) {
        vida -= dt;
        y += vy * dt;
        vy *= (1.0 - 1.5 * dt);
        return vida > 0;
    }

    public void renderizar(Graphics2D g) {
        float alpha = (float) ConstantesJuego.limitar(vida / vidaMax, 0.0, 1.0);
        g.setFont(new Font("SansSerif", Font.BOLD, tamanoFuente));
        FontMetrics fm = g.getFontMetrics();
        int tx = (int) (x - fm.stringWidth(texto) / 2.0);
        int ty = (int) y;
        g.setColor(new Color(0, 0, 0, (int) (alpha * 220)));
        g.drawString(texto, tx + 2, ty + 2);
        g.setColor(new Color(color.getRed(), color.getGreen(), color.getBlue(), (int) (alpha * 255)));
        g.drawString(texto, tx, ty);
    }
}
