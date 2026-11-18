package armas;

import entidades.Proyectil;
import entidades.TipoProyectil;
import java.awt.Color;
import java.awt.Graphics2D;
import java.util.ArrayList;
import java.util.List;

/**
 * [POO - HERENCIA + POLIMORFISMO (@Override)]
 * Rifle de asalto que dispara rafagas de 3 proyectiles veloces con poca caida.
 */
public class RifleAsalto extends Arma {
    public RifleAsalto() {
        super("Rifle de Asalto M4", 24, 48, 96, 1450.0, 2.3, new Color(240, 175, 65));
    }

    @Override
    public List<Proyectil> atacar(double xOrigen, double yOrigen, double angulo, double potencia) {
        List<Proyectil> proyectiles = new ArrayList<Proyectil>();
        if (!puedeDisparar()) return proyectiles;

        int balasRafaga = (municion < 0) ? 3 : Math.min(3, municion);
        consumirMunicionYRegistrar(balasRafaga);
        double v0 = calcularVelocidadInicial(potencia);
        double[] dispersiones = {0.0, -0.022, 0.022};

        for (int i = 0; i < balasRafaga; i++) {
            double ang = angulo + dispersiones[i];
            double vx = v0 * Math.cos(ang);
            double vy = -v0 * Math.sin(ang);
            proyectiles.add(new Proyectil(
                    xOrigen, yOrigen, vx, vy, danoBase, getFactorGravedad(),
                    true, TipoProyectil.BALA_RIFLE, 0.0, 1.35, false, i * 0.075));
        }
        return proyectiles;
    }

    @Override public double getFactorGravedad() { return 0.45; }
    @Override public double getVelocidadBase() { return 460.0; }
    @Override public double getVelocidadExtra() { return 640.0; }
    @Override public String getDescripcionCorta() { return "Rafaga rapida x3 | Baja caida"; }

    @Override
    public void dibujarArmaEnMano(Graphics2D g, double escala) {
        Graphics2D g2 = (Graphics2D) g.create();
        g2.scale(escala, escala);
        g2.setColor(new Color(38, 42, 48));
        g2.fillRoundRect(-8, -4, 34, 7, 3, 3);
        g2.fillRect(6, 2, 6, 10);
        g2.setColor(new Color(22, 24, 28));
        g2.fillRect(24, -3, 13, 3);
        g2.fillRect(2, -7, 10, 3);
        g2.dispose();
    }
}
