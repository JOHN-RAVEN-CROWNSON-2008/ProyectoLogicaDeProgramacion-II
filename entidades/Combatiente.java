package entidades;

import armas.Arma;
import interfaces.Atacable;
import inventario.Inventario;
import util.ConstantesJuego;
import java.awt.Color;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics2D;

/**
 * [POO - HERENCIA + ABSTRACCION + POLIMORFISMO (Sobrecarga)]
 * Clase padre para todos los personajes humanos, zombies y batallones.
 */
public abstract class Combatiente extends EntidadJuego implements Atacable {
    protected String nombre;
    protected int armadura;
    protected double anguloApuntado;
    protected double potenciaApuntado;
    protected double animRetroceso;
    protected double animCaminata;
    protected double flashDano;
    protected boolean mirandoDerecha;

    // [POO - AGREGACION DEBIL] Referencia externa a Arma e Inventario
    protected Arma armaActual;
    protected Inventario inventario;

    // [POO - POLIMORFISMO (Sobrecarga de constructor #1)]
    public Combatiente(String nombre, double x, double y, int vidaMaxima, int armadura) {
        this(nombre, x, y, vidaMaxima, armadura, null);
    }

    // [POO - POLIMORFISMO (Sobrecarga de constructor #2)]
    public Combatiente(String nombre, double x, double y, int vidaMaxima, int armadura, Inventario inventario) {
        super(x, y, vidaMaxima);
        this.nombre = nombre;
        this.armadura = armadura;
        this.inventario = inventario;
        this.anguloApuntado = Math.toRadians(25);
        this.potenciaApuntado = 0.65;
        this.mirandoDerecha = true;
    }

    // [POO - POLIMORFISMO (Sobrecarga de metodos calcularDano)]
    public int calcularDano(int base) {
        return calcularDano(base, 1.0, false);
    }

    public int calcularDano(int base, double multiplicadorCritico) {
        return calcularDano(base, multiplicadorCritico, false);
    }

    public int calcularDano(int base, double multiplicadorCritico, boolean ignoraArmadura) {
        double bruto = base * multiplicadorCritico;
        if (ignoraArmadura) {
            return Math.max(1, (int) Math.round(bruto));
        }
        int reduccion = (int) Math.round(armadura * 0.55);
        return Math.max(2, (int) Math.round(bruto) - reduccion);
    }

    @Override
    public void recibirDano(int cantidad) {
        if (!estaVivo()) return;
        vida = Math.max(0, vida - Math.max(0, cantidad));
        flashDano = 1.0;
        if (vida == 0) {
            activo = false;
        }
    }

    public void curar(int cantidad) {
        if (!estaVivo()) return;
        vida = Math.min(vidaMaxima, vida + Math.max(0, cantidad));
    }

    @Override
    public boolean estaVivo() {
        return vida > 0 && activo;
    }

    @Override
    public void actualizar(double dt) {
        if (animRetroceso > 0) animRetroceso = Math.max(0.0, animRetroceso - dt * 4.5);
        if (flashDano > 0) flashDano = Math.max(0.0, flashDano - dt * 4.0);
        actualizarComportamiento(dt);
    }

    public abstract void actualizarComportamiento(double dt);

    public void setInventario(Inventario inventario) {
        this.inventario = inventario;
        if (inventario != null && armaActual == null && !inventario.getArmas().isEmpty()) {
            this.armaActual = inventario.getArma(0);
        }
    }

    public Inventario getInventario() { return inventario; }
    public Arma getArmaActual() { return armaActual; }
    public void setArmaActual(Arma arma) { this.armaActual = arma; }
    public String getNombre() { return nombre; }
    public double getAnguloApuntado() { return anguloApuntado; }
    public void setAnguloApuntado(double anguloApuntado) { this.anguloApuntado = anguloApuntado; }
    public int getArmadura() { return armadura; }

    public void dibujarBarraVida(Graphics2D g, double cx, double cy, double ancho, double alto, String etiqueta) {
        double pct = ConstantesJuego.limitar((double) vida / vidaMaxima, 0.0, 1.0);
        int x0 = (int) Math.round(cx - ancho / 2.0);
        int y0 = (int) Math.round(cy);

        if (etiqueta != null && !etiqueta.isEmpty()) {
            g.setFont(new Font("SansSerif", Font.BOLD, 11));
            FontMetrics fm = g.getFontMetrics();
            int tw = fm.stringWidth(etiqueta);
            g.setColor(new Color(0, 0, 0, 170));
            g.drawString(etiqueta, (int) (cx - tw / 2.0) + 1, y0 - 4);
            g.setColor(new Color(235, 235, 240));
            g.drawString(etiqueta, (int) (cx - tw / 2.0), y0 - 5);
        }

        g.setColor(new Color(20, 22, 26, 210));
        g.fillRoundRect(x0 - 2, y0 - 2, (int) ancho + 4, (int) alto + 4, 5, 5);

        Color col = colorInterpoladoSalud(pct);
        g.setColor(col);
        g.fillRoundRect(x0, y0, (int) Math.round(ancho * pct), (int) alto, 3, 3);
        g.setColor(new Color(255, 255, 255, 70));
        g.drawRoundRect(x0, y0, (int) ancho, (int) alto, 3, 3);
    }

    public static Color colorInterpoladoSalud(double pct) {
        pct = ConstantesJuego.limitar(pct, 0.0, 1.0);
        if (pct > 0.5) {
            float t = (float) ((pct - 0.5) * 2.0);
            return new Color((int) (245 * (1 - t) + 70 * t), (int) (195 * (1 - t) + 215 * t), (int) (50 * (1 - t) + 85 * t));
        } else {
            float t = (float) (pct * 2.0);
            return new Color((int) (220 * (1 - t) + 245 * t), (int) (45 * (1 - t) + 195 * t), (int) (45 * (1 - t) + 50 * t));
        }
    }
}
