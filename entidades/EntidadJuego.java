package entidades;

import interfaces.Renderizable;
import java.awt.Graphics2D;

/**
 * [POO - ABSTRACCION (Clase Abstracta)]
 * Clase raiz de todas las entidades fisicas del mundo 2D.
 */
public abstract class EntidadJuego implements Renderizable {
    protected double x;
    protected double y;
    protected int vida;
    protected int vidaMaxima;
    protected boolean activo;

    public EntidadJuego(double x, double y, int vidaMaxima) {
        this.x = x;
        this.y = y;
        this.vidaMaxima = Math.max(1, vidaMaxima);
        this.vida = this.vidaMaxima;
        this.activo = true;
    }

    public abstract void actualizar(double dt);

    @Override
    public abstract void renderizar(Graphics2D g);

    public double getX() { return x; }
    public double getY() { return y; }
    public void setPosicion(double x, double y) { this.x = x; this.y = y; }
    public int getVida() { return vida; }
    public int getVidaMaxima() { return vidaMaxima; }
    public boolean estaActivo() { return activo; }
    public void setActivo(boolean activo) { this.activo = activo; }
}
