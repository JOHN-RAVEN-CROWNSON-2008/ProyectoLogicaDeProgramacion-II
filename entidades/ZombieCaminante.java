package entidades;

import java.awt.Color;
import java.awt.Graphics2D;

/** [POO - HERENCIA + POLIMORFISMO (@Override)] */
public class ZombieCaminante extends Zombie {
    public ZombieCaminante(double x, double y, double multEscala, int bonusVida) {
        super("Caminante", x, y, 85 + bonusVida, 2, 36 + Math.random() * 16, 12, multEscala);
        this.colorPiel = new Color(124, 142, 112);
        this.colorRopa = new Color(78, 70, 62);
        this.colorOjos = new Color(225, 240, 95);
    }

    @Override
    public void renderizar(Graphics2D g) {
        dibujarCuerpoZombieBase(g, -0.08, false);
    }
}
