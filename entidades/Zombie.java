package entidades;

import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.geom.Ellipse2D;

/**
 * [POO - HERENCIA + ABSTRACCION]
 * Clase base de la familia de zombies infectados.
 */
public abstract class Zombie extends Combatiente {
    protected double velocidad;
    protected int danoAtaque;
    protected double cadenciaAtaque;
    protected double timerAtaque;
    protected double escala;
    protected Color colorPiel;
    protected Color colorRopa;
    protected Color colorOjos;
    protected double objetivoX = 215.0;
    protected boolean intentandoAtacar = false;

    // [POO - POLIMORFISMO (Sobrecarga de constructor #1)]
    public Zombie(String nombre, double x, double y, int vidaMaxima, int armadura,
                  double velocidad, int danoAtaque) {
        this(nombre, x, y, vidaMaxima, armadura, velocidad, danoAtaque, 1.0);
    }

    // [POO - POLIMORFISMO (Sobrecarga de constructor #2)]
    public Zombie(String nombre, double x, double y, int vidaMaxima, int armadura,
                  double velocidad, int danoAtaque, double escala) {
        super(nombre, x, y, vidaMaxima, armadura);
        this.velocidad = velocidad;
        this.danoAtaque = danoAtaque;
        this.cadenciaAtaque = 1.25;
        this.timerAtaque = 0.3;
        this.escala = escala;
        this.mirandoDerecha = false;
        this.colorPiel = new Color(118, 138, 110);
        this.colorRopa = new Color(68, 62, 58);
        this.colorOjos = new Color(240, 245, 95);
    }

    public void setObjetivoX(double objetivoX) { this.objetivoX = objetivoX; }

    public boolean listoParaGolpear(double dt) {
        if (x > objetivoX) {
            intentandoAtacar = false;
            return false;
        }
        intentandoAtacar = true;
        timerAtaque -= dt;
        if (timerAtaque <= 0) {
            timerAtaque = cadenciaAtaque;
            return true;
        }
        return false;
    }

    @Override
    public void actualizarComportamiento(double dt) {
        animCaminata += dt * (velocidad * 0.085);
        if (x > objetivoX) {
            x -= velocidad * dt;
        }
    }

    public double getAlturaVisual() { return 88.0 * escala; }
    public double getAnchoVisual() { return 38.0 * escala; }
    public int getDanoAtaque() { return danoAtaque; }

    protected void dibujarCuerpoZombieBase(Graphics2D g, double inclinacion, boolean conCasco) {
        if (!estaVivo()) return;
        Graphics2D g2 = (Graphics2D) g.create();
        g2.translate(x, y);
        g2.scale(escala, escala);

        g2.setColor(new Color(0, 0, 0, 100));
        g2.fill(new Ellipse2D.Double(-18, -5, 36, 9));

        double paso = Math.sin(animCaminata) * 7.0;
        double balanceo = Math.cos(animCaminata) * 0.08;
        g2.rotate(inclinacion + balanceo);

        g2.setColor(new Color(45, 48, 52));
        g2.fillRoundRect((int) (-8 + paso * 0.5), -34, 8, 31, 3, 3);
        g2.fillRoundRect((int) (2 - paso * 0.5), -34, 8, 31, 3, 3);

        Color ropa = (flashDano > 0.25) ? new Color(235, 90, 90) : colorRopa;
        g2.setColor(ropa);
        g2.fillRoundRect(-12, -66, 24, 34, 6, 6);
        g2.setColor(new Color(115, 22, 22, 160));
        g2.fillOval(-5, -58, 10, 9);

        double movBrazo = Math.sin(animCaminata * 1.3) * 4.0;
        g2.setColor(colorPiel);
        g2.fillRoundRect(-28, (int) (-62 + movBrazo), 20, 6, 3, 3);
        g2.fillRoundRect(-25, (int) (-54 - movBrazo), 17, 6, 3, 3);

        g2.setColor((flashDano > 0.25) ? new Color(255, 140, 140) : colorPiel);
        g2.fill(new Ellipse2D.Double(-10, -86, 20, 21));

        g2.setColor(new Color(colorOjos.getRed(), colorOjos.getGreen(), colorOjos.getBlue(), 110));
        g2.fillOval(-10, -81, 8, 8);
        g2.setColor(colorOjos);
        g2.fillOval(-8, -79, 4, 4);

        g2.setColor(new Color(75, 15, 20));
        g2.fillOval(-8, -72, 7, 5);

        if (conCasco) {
            g2.setColor(new Color(38, 44, 52));
            g2.fillArc(-13, -90, 26, 20, 0, 180);
            g2.fillRoundRect(-14, -67, 28, 24, 5, 5);
            g2.setColor(new Color(140, 195, 215, 140));
            g2.fillRect(-12, -82, 8, 8);
            g2.setColor(new Color(95, 105, 115));
            g2.drawRoundRect(-14, -67, 28, 24, 5, 5);
        }
        g2.dispose();

        dibujarBarraVida(g, x, y - getAlturaVisual() - 16, 48 * escala, 6, "");
    }
}
