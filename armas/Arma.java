package armas;

import entidades.Proyectil;
import util.ConstantesJuego;
import java.awt.Color;
import java.awt.Graphics2D;
import java.util.List;

/**
 * [POO - ABSTRACCION (Clase Abstracta)]
 * Base polimorfica para todo el arsenal del juego.
 */
public abstract class Arma {
    protected String nombre;
    protected int danoBase;
    protected int municion;
    protected int municionMaxima;
    protected double alcance;
    protected double cadencia;
    protected long ultimoDisparoMs;
    protected Color colorAcento;

    public Arma(String nombre, int danoBase, int municionInicial, int municionMaxima,
                double alcance, double cadencia, Color colorAcento) {
        this.nombre = nombre;
        this.danoBase = danoBase;
        this.municion = municionInicial;
        this.municionMaxima = municionMaxima;
        this.alcance = alcance;
        this.cadencia = cadencia;
        this.colorAcento = colorAcento;
        this.ultimoDisparoMs = 0L;
    }

    // [POO - ABSTRACCION] Metodo abstracto obligatorio de ataque
    public abstract List<Proyectil> atacar(double xOrigen, double yOrigen, double angulo, double potencia);

    // [POO - POLIMORFISMO (Sobrecarga)] Version extendida con faccion del tirador
    public List<Proyectil> atacar(double xOrigen, double yOrigen, double angulo, double potencia, boolean faccionJugador) {
        List<Proyectil> lista = atacar(xOrigen, yOrigen, angulo, potencia);
        for (Proyectil p : lista) {
            p.setFaccionJugador(faccionJugador);
        }
        return lista;
    }

    public abstract double getFactorGravedad();
    public abstract double getVelocidadBase();
    public abstract double getVelocidadExtra();
    public abstract String getDescripcionCorta();
    public abstract void dibujarArmaEnMano(Graphics2D g, double escala);

    public boolean puedeDisparar() {
        if (municion == 0) return false;
        long ahora = System.currentTimeMillis();
        long cooldownMs = (long) (1000.0 / Math.max(0.2, cadencia));
        return (ahora - ultimoDisparoMs) >= cooldownMs;
    }

    protected void consumirMunicionYRegistrar(int balas) {
        ultimoDisparoMs = System.currentTimeMillis();
        if (municion > 0) {
            municion = Math.max(0, municion - balas);
        }
    }

    public void recargar(int cantidad) {
        if (municion < 0) return;
        municion = Math.min(municionMaxima, municion + Math.max(0, cantidad));
    }

    public boolean esInfinita() { return municion < 0; }
    public String getNombre() { return nombre; }
    public int getDanoBase() { return danoBase; }
    public int getMunicion() { return municion; }
    public int getMunicionMaxima() { return municionMaxima; }
    public double getAlcance() { return alcance; }
    public double getCadencia() { return cadencia; }
    public Color getColorAcento() { return colorAcento; }

    /**
     * Calcula la velocidad inicial soportando desde 5% (0.05) hasta 100% (1.00).
     */
    public double calcularVelocidadInicial(double potencia) {
        double p = ConstantesJuego.limitar(potencia, 0.05, 1.0);
        double vMin = 175.0;
        double vMax = getVelocidadBase() + getVelocidadExtra();
        return vMin + p * (vMax - vMin);
    }
}
