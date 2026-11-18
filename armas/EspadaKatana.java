package armas;

import entidades.Proyectil;
import entidades.TipoProyectil;
import java.awt.Color;
import java.awt.Graphics2D;
import java.util.ArrayList;
import java.util.List;

/**
 * [POO - HERENCIA + POLIMORFISMO (@Override)]
 * Katana estilo Michonne: letal cuerpo a cuerpo sin municion o arrojadiza.
 */
public class EspadaKatana extends Arma {
    public EspadaKatana() {
        super("Katana de Michonne", 90, -1, -1, 950.0, 2.2, new Color(115, 220, 245));
    }

    @Override
    public List<Proyectil> atacar(double xOrigen, double yOrigen, double angulo, double potencia) {
        List<Proyectil> proyectiles = new ArrayList<Proyectil>();
        if (!puedeDisparar()) return proyectiles;

        consumirMunicionYRegistrar(0);
        double v0 = calcularVelocidadInicial(potencia);
        double vx = v0 * Math.cos(angulo);
        double vy = -v0 * Math.sin(angulo);
        proyectiles.add(new Proyectil(
                xOrigen, yOrigen, vx, vy, danoBase, getFactorGravedad(),
                true, TipoProyectil.HOJA_KATANA, 0.0, 1.5, true, 0.0));
        return proyectiles;
    }

    public boolean puedeCortarCuerpoACuerpo() {
        return puedeDisparar();
    }

    public void registrarCorteCuerpoACuerpo() {
        consumirMunicionYRegistrar(0);
    }

    @Override public double getFactorGravedad() { return 0.90; }
    @Override public double getVelocidadBase() { return 310.0; }
    @Override public double getVelocidadExtra() { return 570.0; }
    @Override public String getDescripcionCorta() { return "Infinita | Corte melee o arrojadiza"; }

    @Override
    public void dibujarArmaEnMano(Graphics2D g, double escala) {
        Graphics2D g2 = (Graphics2D) g.create();
        g2.scale(escala, escala);
        g2.setColor(new Color(35, 35, 42));
        g2.fillRect(-6, -2, 12, 4);
        g2.setColor(new Color(210, 170, 60));
        g2.fillRect(5, -5, 3, 10);
        g2.setColor(new Color(225, 242, 255));
        g2.fillPolygon(new int[]{8, 38, 41, 8}, new int[]{-2, -4, -1, 1}, 4);
        g2.dispose();
    }
}
