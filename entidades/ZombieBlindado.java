package entidades;

import java.awt.Color;
import java.awt.Graphics2D;

/** [POO - HERENCIA + POLIMORFISMO (@Override)] */
public class ZombieBlindado extends Zombie {
    public ZombieBlindado(double x, double y, int bonusVida) {
        super("Blindado", x, y, 210 + bonusVida, 18, 26 + Math.random() * 10, 22, 1.24);
        this.cadenciaAtaque = 1.65;
        this.colorPiel = new Color(96, 112, 96);
        this.colorRopa = new Color(46, 52, 58);
        this.colorOjos = new Color(255, 170, 50);
    }

    @Override
    public void renderizar(Graphics2D g) {
        dibujarCuerpoZombieBase(g, -0.04, true);
    }
}
