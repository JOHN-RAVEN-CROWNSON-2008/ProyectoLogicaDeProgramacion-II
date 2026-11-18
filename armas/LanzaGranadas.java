package armas;

import entidades.Proyectil;
import entidades.TipoProyectil;
import java.awt.Color;
import java.awt.Graphics2D;
import java.util.ArrayList;
import java.util.List;

/**
 * [POO - HERENCIA + POLIMORFISMO (@Override)]
 * Lanzagranadas pesado con trayectoria parabolica pronunciada y dano en area (AoE).
 */
public class LanzaGranadas extends Arma {
    public LanzaGranadas() {
        super("Lanzagranadas M79", 74, 10, 24, 1500.0, 0.9, new Color(235, 95, 55));
    }

    @Override
    public List<Proyectil> atacar(double xOrigen, double yOrigen, double angulo, double potencia) {
        List<Proyectil> proyectiles = new ArrayList<Proyectil>();
        if (!puedeDisparar()) return proyectiles;

        consumirMunicionYRegistrar(1);
        double v0 = calcularVelocidadInicial(potencia);
        double vx = v0 * Math.cos(angulo);
        double vy = -v0 * Math.sin(angulo);
        proyectiles.add(new Proyectil(
                xOrigen, yOrigen, vx, vy, danoBase, getFactorGravedad(),
                true, TipoProyectil.GRANADA, 145.0, 1.15, true, 0.0));
        return proyectiles;
    }

    @Override public double getFactorGravedad() { return 1.0; }
    @Override public double getVelocidadBase() { return 300.0; }
    @Override public double getVelocidadExtra() { return 690.0; }
    @Override public String getDescripcionCorta() { return "Arco pesado | Explosion AoE"; }

    @Override
    public void dibujarArmaEnMano(Graphics2D g, double escala) {
        Graphics2D g2 = (Graphics2D) g.create();
        g2.scale(escala, escala);
        g2.setColor(new Color(105, 68, 42));
        g2.fillRoundRect(-8, -3, 18, 8, 3, 3);
        g2.setColor(new Color(55, 60, 65));
        g2.fillRoundRect(4, -6, 25, 10, 4, 4);
        g2.setColor(new Color(210, 90, 45));
        g2.fillRect(25, -5, 4, 8);
        g2.dispose();
    }
}
