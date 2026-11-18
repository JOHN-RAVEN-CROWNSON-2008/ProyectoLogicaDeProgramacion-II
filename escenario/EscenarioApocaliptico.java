package escenario;

import util.ConstantesJuego;
import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.GradientPaint;
import java.awt.Graphics2D;
import java.awt.geom.Ellipse2D;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Renderizador de fondo post-apocaliptico con capas Parallax y particulas de ceniza.
 */
public class EscenarioApocaliptico {
    private final List<double[]> cenizas = new ArrayList<double[]>();
    private final int[] alturasEdificios = {190, 250, 140, 290, 210, 170, 310, 185, 240, 160, 275, 200, 150, 260};

    public EscenarioApocaliptico() {
        Random r = new Random(42);
        for (int i = 0; i < 45; i++) {
            cenizas.add(new double[]{
                    r.nextDouble() * 1300,
                    r.nextDouble() * 620,
                    12 + r.nextDouble() * 24,
                    1.5 + r.nextDouble() * 2.5
            });
        }
    }

    public void actualizar(double dt) {
        for (double[] c : cenizas) {
            c[0] -= c[2] * dt;
            c[1] += (8 + Math.sin(c[0] * 0.02) * 6) * dt;
            if (c[0] < -10) c[0] = 1300;
            if (c[1] > 600) c[1] = -10;
        }
    }

    public void dibujarFondo(Graphics2D g, double camaraX, int anchoMundo) {
        GradientPaint cielo = new GradientPaint(
                0, 0, new Color(24, 20, 38),
                0, 560, new Color(138, 62, 46));
        g.setPaint(cielo);
        g.fillRect(0, 0, ConstantesJuego.ANCHO_VIRTUAL, ConstantesJuego.ALTO_VIRTUAL);

        double solX = 880 - camaraX * 0.05;
        g.setColor(new Color(245, 145, 75, 45));
        g.fill(new Ellipse2D.Double(solX - 95, 110, 190, 190));
        g.setColor(new Color(255, 175, 95, 110));
        g.fill(new Ellipse2D.Double(solX - 52, 153, 104, 104));

        // Parallax lejano
        double offLejano = -(camaraX * 0.18);
        g.setColor(new Color(34, 25, 38));
        for (int rep = 0; rep < 3; rep++) {
            for (int i = 0; i < alturasEdificios.length; i++) {
                double bx = offLejano + rep * 1400 + i * 100;
                int h = alturasEdificios[i];
                int bw = 82;
                int by = ConstantesJuego.Y_SUELO - h;
                g.fillRect((int) bx, by, bw, h);
                g.fillPolygon(new int[]{(int) bx, (int) bx + 35, (int) bx + bw},
                        new int[]{by, by - 18, by + 12}, 3);
                g.setColor(new Color(175, 105, 55, 45));
                for (int wy = by + 22; wy < ConstantesJuego.Y_SUELO - 30; wy += 24) {
                    if ((i + wy) % 3 != 0) g.fillRect((int) bx + 14, wy, 10, 12);
                    if ((i + wy) % 2 == 0) g.fillRect((int) bx + 48, wy, 10, 12);
                }
                g.setColor(new Color(34, 25, 38));
            }
        }

        // Parallax medio
        double offMedio = -(camaraX * 0.45);
        for (int i = 0; i < 12; i++) {
            double tx = offMedio + i * 240 + 40;
            dibujarArbolSeco(g, tx, ConstantesJuego.Y_SUELO);
            if (i % 2 == 0) {
                dibujarVallaRota(g, tx + 95, ConstantesJuego.Y_SUELO);
            }
        }

        for (double[] c : cenizas) {
            g.setColor(new Color(255, 175, 100, 110));
            g.fill(new Ellipse2D.Double(c[0], c[1], c[3], c[3]));
        }
    }

    public void dibujarSueloMundo(Graphics2D g, int anchoMundo) {
        int ys = ConstantesJuego.Y_SUELO;
        GradientPaint asfalto = new GradientPaint(
                0, ys, new Color(46, 48, 52),
                0, ConstantesJuego.ALTO_VIRTUAL, new Color(24, 25, 28));
        g.setPaint(asfalto);
        g.fillRect(-100, ys, anchoMundo + 200, ConstantesJuego.ALTO_VIRTUAL - ys + 100);

        g.setColor(new Color(72, 74, 78));
        g.fillRect(-100, ys, anchoMundo + 200, 5);

        g.setColor(new Color(185, 145, 50, 145));
        for (int rx = 0; rx < anchoMundo; rx += 95) {
            g.fillRect(rx, ys + 36, 48, 6);
        }

        g.setColor(new Color(22, 23, 26));
        g.setStroke(new BasicStroke(2f));
        for (int gx = 60; gx < anchoMundo; gx += 180) {
            g.drawLine(gx, ys + 12, gx + 18, ys + 24);
            g.drawLine(gx + 18, ys + 24, gx + 6, ys + 42);
        }
        g.setStroke(new BasicStroke(1f));
    }

    private void dibujarArbolSeco(Graphics2D g, double x, double ySuelo) {
        g.setColor(new Color(28, 22, 28));
        g.setStroke(new BasicStroke(6f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
        g.drawLine((int) x, (int) ySuelo, (int) x - 4, (int) ySuelo - 88);
        g.setStroke(new BasicStroke(3.5f));
        g.drawLine((int) x - 3, (int) ySuelo - 55, (int) x - 30, (int) ySuelo - 85);
        g.drawLine((int) x - 3, (int) ySuelo - 68, (int) x + 26, (int) ySuelo - 102);
        g.setStroke(new BasicStroke(1f));
    }

    private void dibujarVallaRota(Graphics2D g, double x, double ySuelo) {
        g.setColor(new Color(38, 34, 42));
        g.setStroke(new BasicStroke(3f));
        g.drawLine((int) x, (int) ySuelo, (int) x, (int) ySuelo - 52);
        g.drawLine((int) x + 75, (int) ySuelo, (int) x + 80, (int) ySuelo - 46);
        g.setStroke(new BasicStroke(1.2f));
        for (int gx = 0; gx <= 75; gx += 15) {
            g.drawLine((int) x + gx, (int) ySuelo - 44, (int) x + gx + 8, (int) ySuelo - 6);
        }
        g.setStroke(new BasicStroke(1f));
    }
}
