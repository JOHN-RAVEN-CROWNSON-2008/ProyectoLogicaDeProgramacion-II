package inventario;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.geom.Ellipse2D;
import java.awt.geom.RoundRectangle2D;

/**
 * [POO - AGREGACION DEBIL (Objeto independiente)]
 * Recurso utilizable o recolectable que existe fuera de los combatientes.
 */
public class Suministro {
    private final TipoSuministro tipo;
    private int cantidad;
    private final double x;
    private final double y;
    private boolean enSuelo;
    private double tiempoFlotando;

    // [POO - POLIMORFISMO (Sobrecarga de constructor #1: para Inventario)]
    public Suministro(TipoSuministro tipo, int cantidad) {
        this(tipo, cantidad, 0, 0, false);
    }

    // [POO - POLIMORFISMO (Sobrecarga de constructor #2: botin en escenario)]
    public Suministro(TipoSuministro tipo, int cantidad, double x, double y) {
        this(tipo, cantidad, x, y, true);
    }

    private Suministro(TipoSuministro tipo, int cantidad, double x, double y, boolean enSuelo) {
        this.tipo = tipo;
        this.cantidad = Math.max(0, cantidad);
        this.x = x;
        this.y = y;
        this.enSuelo = enSuelo;
        this.tiempoFlotando = 0;
    }

    public void actualizarDrop(double dt) {
        tiempoFlotando += dt;
    }

    public void renderizarDrop(Graphics2D g) {
        if (!enSuelo) return;
        double bob = Math.sin(tiempoFlotando * 4.5) * 4.0;
        double dx = x;
        double dy = y - 16 + bob;

        g.setColor(new Color(tipo.color.getRed(), tipo.color.getGreen(), tipo.color.getBlue(), 75));
        g.fill(new Ellipse2D.Double(dx - 20, dy - 18, 40, 36));

        g.setColor(new Color(45, 48, 52));
        g.fill(new RoundRectangle2D.Double(dx - 13, dy - 11, 26, 22, 6, 6));
        g.setColor(tipo.color);
        g.setStroke(new BasicStroke(2f));
        g.draw(new RoundRectangle2D.Double(dx - 13, dy - 11, 26, 22, 6, 6));

        if (tipo == TipoSuministro.BOTIQUIN) {
            g.fillRect((int) dx - 6, (int) dy - 2, 12, 4);
            g.fillRect((int) dx - 2, (int) dy - 6, 4, 12);
        } else if (tipo == TipoSuministro.CAJA_MUNICION) {
            g.fillRect((int) dx - 6, (int) dy - 5, 3, 10);
            g.fillRect((int) dx - 1, (int) dy - 5, 3, 10);
            g.fillRect((int) dx + 4, (int) dy - 5, 3, 10);
        } else {
            g.fillOval((int) dx - 5, (int) dy - 5, 10, 10);
        }
        g.setStroke(new BasicStroke(1f));
    }

    public TipoSuministro getTipo() { return tipo; }
    public int getCantidad() { return cantidad; }
    public void agregar(int n) { cantidad += Math.max(0, n); }
    public boolean consumirUno() {
        if (cantidad <= 0) return false;
        cantidad--;
        return true;
    }
    public double getX() { return x; }
    public double getY() { return y; }
    public boolean isEnSuelo() { return enSuelo; }
    public void marcarRecogido() { enSuelo = false; }
    public double getTiempoFlotando() { return tiempoFlotando; }
}
