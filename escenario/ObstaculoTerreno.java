package escenario;

import java.awt.Color;
import java.awt.Graphics2D;

/**
 * Obstaculo fisico destructible/solido (autobus volcado, coche en ruinas) para el duelo 1v1.
 */
public class ObstaculoTerreno {
    private final double x, y, ancho, alto;
    private final String tipo;

    public ObstaculoTerreno(double x, double ySuelo, double ancho, double alto, String tipo) {
        this.x = x;
        this.y = ySuelo - alto;
        this.ancho = ancho;
        this.alto = alto;
        this.tipo = tipo;
    }

    public boolean colisiona(double px, double py) {
        return px >= x && px <= x + ancho && py >= y && py <= y + alto;
    }

    public void renderizar(Graphics2D g) {
        if ("AUTOBUS".equals(tipo)) {
            g.setColor(new Color(145, 102, 34));
            g.fillRoundRect((int) x, (int) y + 10, (int) ancho, (int) alto - 22, 12, 12);
            g.setColor(new Color(92, 62, 26));
            g.fillRect((int) x + 4, (int) y + 52, (int) ancho - 8, 8);
            g.setColor(new Color(24, 28, 34));
            for (int i = 0; i < 4; i++) {
                g.fillRoundRect((int) (x + 14 + i * 38), (int) y + 20, 28, 22, 4, 4);
            }
            g.setColor(new Color(28, 28, 30));
            g.fillOval((int) x + 20, (int) (y + alto - 28), 30, 30);
            g.fillOval((int) (x + ancho - 52), (int) (y + alto - 28), 30, 30);
            g.setColor(new Color(95, 95, 100));
            g.fillOval((int) x + 28, (int) (y + alto - 20), 14, 14);
            g.fillOval((int) (x + ancho - 44), (int) (y + alto - 20), 14, 14);
        } else {
            g.setColor(new Color(74, 82, 92));
            g.fillRoundRect((int) x, (int) y + 18, (int) ancho, (int) alto - 28, 10, 10);
            g.fillPolygon(
                    new int[]{(int) x + 18, (int) x + 36, (int) (x + ancho - 32), (int) (x + ancho - 16)},
                    new int[]{(int) y + 20, (int) y, (int) y, (int) y + 20}, 4);
            g.setColor(new Color(22, 26, 30));
            g.fillPolygon(
                    new int[]{(int) x + 25, (int) x + 40, (int) (x + ancho - 38), (int) (x + ancho - 24)},
                    new int[]{(int) y + 18, (int) y + 4, (int) y + 4, (int) y + 18}, 4);
            g.setColor(new Color(25, 25, 28));
            g.fillOval((int) x + 14, (int) (y + alto - 22), 24, 24);
            g.fillOval((int) (x + ancho - 38), (int) (y + alto - 22), 24, 24);
        }
    }
}
