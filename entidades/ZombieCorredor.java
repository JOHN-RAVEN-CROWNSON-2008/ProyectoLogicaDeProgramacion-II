package entidades;

import java.awt.Color;
import java.awt.Graphics2D;

/** [POO - HERENCIA + POLIMORFISMO (@Override)] */
public class ZombieCorredor extends Zombie {
    public ZombieCorredor(double x, double y, int bonusVida) {
        super("Corredor", x, y, 56 + bonusVida, 0, 105 + Math.random() * 35, 14, 0.94);
        this.cadenciaAtaque = 0.85;
        this.colorPiel = new Color(138, 115, 108);
        this.colorRopa = new Color(96, 44, 44);
        this.colorOjos = new Color(255, 55, 55);
    }

    @Override
    public void actualizarComportamiento(double dt) {
        super.actualizarComportamiento(dt);
        animCaminata += dt * 4.5;
    }

    @Override
    public void renderizar(Graphics2D g) {
        dibujarCuerpoZombieBase(g, -0.22, false);
    }
}
