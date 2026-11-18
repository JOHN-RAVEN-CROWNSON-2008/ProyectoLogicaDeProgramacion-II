package armas;

import entidades.Proyectil;
import entidades.TipoProyectil;
import java.awt.Color;
import java.awt.Graphics2D;
import java.util.ArrayList;
import java.util.List;

/**
 * [POO - HERENCIA + POLIMORFISMO (@Override)]
 * Revolver Colt Python de alta precision, dano medio-alto y recarga agil.
 */
public class Revolver extends Arma {
    public Revolver() {
        super("Revolver Python .357", 50, 20, 48, 1300.0, 1.9, new Color(215, 225, 235));
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
                true, TipoProyectil.BALA_PESADA, 0.0, 1.65, false, 0.0));
        return proyectiles;
    }

    @Override public double getFactorGravedad() { return 0.55; }
    @Override public double getVelocidadBase() { return 410.0; }
    @Override public double getVelocidadExtra() { return 620.0; }
    @Override public String getDescripcionCorta() { return "Precision critica | Recarga rapida"; }

    @Override
    public void dibujarArmaEnMano(Graphics2D g, double escala) {
        Graphics2D g2 = (Graphics2D) g.create();
        g2.scale(escala, escala);
        g2.setColor(new Color(95, 58, 35));
        g2.fillRoundRect(-5, -1, 7, 10, 3, 3);
        g2.setColor(new Color(185, 195, 205));
        g2.fillRect(0, -5, 22, 5);
        g2.setColor(new Color(130, 140, 150));
        g2.fillRoundRect(2, -4, 8, 7, 3, 3);
        g2.dispose();
    }
}
