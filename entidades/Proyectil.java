package entidades;

import util.ConstantesJuego;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.geom.Ellipse2D;
import java.awt.geom.Point2D;
import java.awt.geom.RoundRectangle2D;
import java.util.ArrayList;
import java.util.List;

/**
 * [POO - HERENCIA + POLIMORFISMO (Sobrecarga de constructores)]
 * Proyectil balistico afectado por gravedad y viento.
 */
public class Proyectil extends EntidadJuego {
    private double vx;
    private double vy;
    private final int dano;
    private final double factorGravedad;
    private boolean faccionJugador;
    private final TipoProyectil tipo;
    private final double radioExplosion;
    private final double multiplicadorCritico;
    private final boolean ignoraArmadura;
    private double rotacion;
    private double retrasoLanzamiento;
    private boolean yaLanzado;
    private final List<Point2D.Double> estela = new ArrayList<Point2D.Double>();

    // [POO - POLIMORFISMO (Sobrecarga de constructor #1)]
    public Proyectil(double x, double y, double vx, double vy, int dano,
                     double factorGravedad, boolean faccionJugador, TipoProyectil tipo) {
        this(x, y, vx, vy, dano, factorGravedad, faccionJugador, tipo, 0.0, 1.0, false, 0.0);
    }

    // [POO - POLIMORFISMO (Sobrecarga de constructor #2)]
    public Proyectil(double x, double y, double vx, double vy, int dano,
                     double factorGravedad, boolean faccionJugador, TipoProyectil tipo,
                     double radioExplosion, double multiplicadorCritico,
                     boolean ignoraArmadura, double retrasoLanzamiento) {
        super(x, y, 1);
        this.vx = vx;
        this.vy = vy;
        this.dano = dano;
        this.factorGravedad = factorGravedad;
        this.faccionJugador = faccionJugador;
        this.tipo = tipo;
        this.radioExplosion = radioExplosion;
        this.multiplicadorCritico = multiplicadorCritico;
        this.ignoraArmadura = ignoraArmadura;
        this.retrasoLanzamiento = Math.max(0.0, retrasoLanzamiento);
        this.yaLanzado = (this.retrasoLanzamiento <= 0.0001);
        this.rotacion = Math.atan2(vy, vx);
    }

    public void actualizarConViento(double dt, double aceleracionViento) {
        if (!activo) return;
        if (!yaLanzado) {
            retrasoLanzamiento -= dt;
            if (retrasoLanzamiento <= 0.0) {
                yaLanzado = true;
            } else {
                return;
            }
        }
        estela.add(new Point2D.Double(x, y));
        if (estela.size() > (tipo == TipoProyectil.GRANADA ? 20 : 12)) {
            estela.remove(0);
        }

        vx += aceleracionViento * dt;
        vy += ConstantesJuego.GRAVEDAD_BASE * factorGravedad * dt;
        x += vx * dt;
        y += vy * dt;

        if (tipo == TipoProyectil.HOJA_KATANA) {
            rotacion += 18.0 * dt;
        } else if (tipo == TipoProyectil.GRANADA) {
            rotacion += 7.5 * dt;
        } else {
            rotacion = Math.atan2(vy, vx);
        }
    }

    @Override
    public void actualizar(double dt) {
        actualizarConViento(dt, 0.0);
    }

    @Override
    public void renderizar(Graphics2D g) {
        if (!activo || !yaLanzado) return;

        for (int i = 0; i < estela.size(); i++) {
            Point2D.Double p = estela.get(i);
            float alpha = (float) (i + 1) / (estela.size() + 1);
            if (tipo == TipoProyectil.GRANADA) {
                g.setColor(new Color(200, 200, 200, (int) (alpha * 110)));
                double r = 3 + (1 - alpha) * 6;
                g.fill(new Ellipse2D.Double(p.x - r / 2, p.y - r / 2, r, r));
            } else if (tipo == TipoProyectil.HOJA_KATANA) {
                g.setColor(new Color(180, 235, 255, (int) (alpha * 140)));
                g.fill(new Ellipse2D.Double(p.x - 3, p.y - 3, 6, 6));
            } else {
                g.setColor(new Color(255, 210, 90, (int) (alpha * 170)));
                g.fill(new Ellipse2D.Double(p.x - 2, p.y - 2, 4, 4));
            }
        }

        Graphics2D g2 = (Graphics2D) g.create();
        g2.translate(x, y);
        g2.rotate(rotacion);

        switch (tipo) {
            case BALA_RIFLE:
                g2.setColor(new Color(255, 220, 100));
                g2.fill(new RoundRectangle2D.Double(-8, -2, 16, 4, 3, 3));
                g2.setColor(new Color(255, 130, 30));
                g2.fill(new Ellipse2D.Double(4, -2, 5, 4));
                break;
            case BALA_PESADA:
                g2.setColor(new Color(255, 235, 150));
                g2.fill(new RoundRectangle2D.Double(-10, -3, 18, 6, 4, 4));
                g2.setColor(new Color(220, 90, 40));
                g2.fill(new Ellipse2D.Double(4, -3, 6, 6));
                break;
            case GRANADA:
                g2.setColor(new Color(70, 92, 56));
                g2.fill(new Ellipse2D.Double(-9, -7, 18, 14));
                g2.setColor(new Color(210, 180, 70));
                g2.fillRect(-3, -9, 6, 4);
                g2.setColor(new Color(255, 70, 40));
                g2.fill(new Ellipse2D.Double(2, -5, 4, 4));
                break;
            case HOJA_KATANA:
                g2.setColor(new Color(225, 240, 255));
                g2.fill(new RoundRectangle2D.Double(-18, -3, 36, 5, 4, 4));
                g2.setColor(new Color(45, 45, 55));
                g2.fillRect(-20, -4, 9, 8);
                g2.setColor(new Color(200, 160, 50));
                g2.fillRect(-11, -6, 3, 12);
                break;
        }
        g2.dispose();
    }

    public boolean estaYaLanzado() { return yaLanzado; }
    public double getVx() { return vx; }
    public double getVy() { return vy; }
    public int getDano() { return dano; }
    public boolean isFaccionJugador() { return faccionJugador; }
    public void setFaccionJugador(boolean faccionJugador) { this.faccionJugador = faccionJugador; }
    public TipoProyectil getTipo() { return tipo; }
    public double getRadioExplosion() { return radioExplosion; }
    public double getMultiplicadorCritico() { return multiplicadorCritico; }
    public boolean isIgnoraArmadura() { return ignoraArmadura; }
}
