package entidades;

import armas.RifleAsalto;
import inventario.Inventario;
import java.awt.AlphaComposite;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.geom.Ellipse2D;
import java.util.ArrayList;
import java.util.List;

/**
 * [POO - COMPOSICION FUERTE (Batallon *-- MiembroEscuadron)]
 * En el Modo 2 (1v1), Batallon actua como UN SOLO OBJETO SINGULAR:
 * posee una unica barra de vida global, una posicion ancla, recibe el dano
 * unificado y ejecuta su turno como entidad unica.
 * Internamente crea y destruye su lista privada de MiembroEscuadron,
 * los cuales NO pueden existir fuera del Batallon.
 */
public class Batallon extends Combatiente {

    /**
     * [POO - COMPOSICION FUERTE (Clase componente privada)]
     * Miembro visual interno dependiente 100% del ciclo de vida del Batallon.
     */
    private static final class MiembroEscuadron {
        final double offsetX;
        final double offsetY;
        final Color colorChaqueta;
        final boolean usaCasco;
        final boolean usaSombrero;
        boolean vivo = true;
        double progresoCaida = 0.0;
        double fase;

        MiembroEscuadron(double offsetX, double offsetY, Color colorChaqueta,
                         boolean usaCasco, boolean usaSombrero, double fase) {
            this.offsetX = offsetX;
            this.offsetY = offsetY;
            this.colorChaqueta = colorChaqueta;
            this.usaCasco = usaCasco;
            this.usaSombrero = usaSombrero;
            this.fase = fase;
        }
    }

    private final List<MiembroEscuadron> miembros = new ArrayList<MiembroEscuadron>();
    private final boolean esJugador;
    private final int totalMiembros = 4;

    public Batallon(String nombre, double x, double y, int vidaGlobal, int armadura,
                    boolean esJugador, Inventario inventarioCompartido) {
        super(nombre, x, y, vidaGlobal, armadura, inventarioCompartido);
        this.esJugador = esJugador;
        this.mirandoDerecha = esJugador;
        this.anguloApuntado = esJugador ? Math.toRadians(35) : Math.toRadians(145);

        if (inventarioCompartido != null && !inventarioCompartido.getArmas().isEmpty()) {
            this.armaActual = inventarioCompartido.getArma(0);
        } else {
            this.armaActual = new RifleAsalto();
        }

        inicializarMiembros();
    }

    private void inicializarMiembros() {
        miembros.clear();
        if (esJugador) {
            miembros.add(new MiembroEscuadron(-52, 0, new Color(88, 70, 52), false, true, 0.0));
            miembros.add(new MiembroEscuadron(-18, -2, new Color(56, 72, 60), true, false, 1.2));
            miembros.add(new MiembroEscuadron(16, 0, new Color(75, 65, 58), false, false, 2.3));
            miembros.add(new MiembroEscuadron(50, -1, new Color(52, 60, 74), true, false, 3.5));
        } else {
            miembros.add(new MiembroEscuadron(-50, -1, new Color(92, 42, 42), false, false, 0.4));
            miembros.add(new MiembroEscuadron(-16, 0, new Color(72, 48, 44), true, false, 1.5));
            miembros.add(new MiembroEscuadron(18, -2, new Color(84, 54, 40), false, false, 2.7));
            miembros.add(new MiembroEscuadron(52, 0, new Color(115, 36, 36), false, true, 3.9));
        }
    }

    @Override
    public void recibirDano(int cantidad) {
        super.recibirDano(cantidad);
        actualizarMiembrosSegunVida();
    }

    /**
     * Sincroniza la caida visual de los MiembroEscuadron al bajar del
     * 75%, 50%, 25% y 0% de la vida global del objeto singular Batallon.
     */
    private void actualizarMiembrosSegunVida() {
        double pct = (double) vida / (double) vidaMaxima;
        int vivosObjetivo = (vida <= 0) ? 0 : (int) Math.ceil(pct * totalMiembros);
        vivosObjetivo = Math.max(0, Math.min(miembros.size(), vivosObjetivo));

        for (int i = 0; i < miembros.size(); i++) {
            int ordenSupervivencia = esJugador ? i : (miembros.size() - 1 - i);
            miembros.get(i).vivo = (ordenSupervivencia < vivosObjetivo);
        }
    }

    public void destruirBatallon() {
        this.vida = 0;
        this.activo = false;
        this.miembros.clear();
    }

    public List<Proyectil> dispararEnUnisono(double angulo, double potencia) {
        this.anguloApuntado = angulo;
        this.potenciaApuntado = potencia;
        this.animRetroceso = 1.0;

        double dir = esJugador ? 1.0 : -1.0;
        double xOrigen = x + dir * 32;
        double yOrigen = y - 56;
        if (armaActual == null) return new ArrayList<Proyectil>();
        return armaActual.atacar(xOrigen, yOrigen, angulo, potencia, esJugador);
    }

    public int getMiembrosVivos() {
        int c = 0;
        for (MiembroEscuadron m : miembros) {
            if (m.vivo) c++;
        }
        return c;
    }

    public int getTotalMiembros() { return miembros.size(); }
    public boolean isEsJugador() { return esJugador; }

    @Override
    public void actualizarComportamiento(double dt) {
        for (MiembroEscuadron m : miembros) {
            m.fase += dt;
            if (!m.vivo && m.progresoCaida < 1.0) {
                m.progresoCaida = Math.min(1.0, m.progresoCaida + dt * 2.4);
            }
        }
    }

    @Override
    public void renderizar(Graphics2D g) {
        if (miembros.isEmpty() && !activo) return;

        g.setColor(new Color(0, 0, 0, 120));
        g.fill(new Ellipse2D.Double(x - 86, y - 8, 172, 16));

        double xSacos = esJugador ? x + 58 : x - 86;
        g.setColor(new Color(122, 108, 82));
        for (int row = 0; row < 2; row++) {
            for (int col = 0; col < 2; col++) {
                g.fillRoundRect((int) (xSacos + col * 14), (int) (y - 16 - row * 9), 18, 10, 5, 5);
                g.setColor(new Color(78, 66, 48));
                g.drawRoundRect((int) (xSacos + col * 14), (int) (y - 16 - row * 9), 18, 10, 5, 5);
                g.setColor(new Color(122, 108, 82));
            }
        }

        for (MiembroEscuadron m : miembros) {
            dibujarMiembro(g, m);
        }

        if (estaVivo()) {
            String titulo = nombre + " [" + getMiembrosVivos() + "/" + totalMiembros + " en pie]";
            dibujarBarraVida(g, x, y - 122, 150, 10, titulo);

            for (int i = 0; i < miembros.size(); i++) {
                boolean vivo = miembros.get(i).vivo;
                g.setColor(vivo ? (esJugador ? new Color(100, 220, 140) : new Color(240, 115, 95))
                        : new Color(55, 55, 62));
                g.fillRoundRect((int) (x - 30 + i * 16), (int) (y - 109), 12, 5, 2, 2);
            }
        }
    }

    private void dibujarMiembro(Graphics2D g, MiembroEscuadron m) {
        double mx = x + m.offsetX;
        double my = y + m.offsetY;
        double bob = m.vivo ? Math.sin(m.fase * 3.0) * 1.4 : 0.0;
        double dir = esJugador ? 1.0 : -1.0;

        Graphics2D gm = (Graphics2D) g.create();
        gm.translate(mx, my);

        if (m.progresoCaida > 0.0) {
            double anguloCaida = -dir * m.progresoCaida * (Math.PI / 2.05);
            gm.rotate(anguloCaida);
            gm.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER,
                    (float) (1.0 - m.progresoCaida * 0.45)));
        }

        double retro = m.vivo ? -dir * animRetroceso * 4.5 : 0.0;
        gm.translate(retro, 0);

        gm.setColor(new Color(40, 44, 52));
        gm.fillRoundRect(-8, -32, 6, 30, 3, 3);
        gm.fillRoundRect(2, -32, 6, 30, 3, 3);

        Color ch = (flashDano > 0.25 && m.vivo) ? new Color(235, 95, 95) : m.colorChaqueta;
        gm.setColor(ch);
        gm.fillRoundRect(-11, (int) (-64 + bob), 22, 34, 6, 6);

        gm.setColor(new Color(216, 176, 142));
        gm.fill(new Ellipse2D.Double(-8, -82 + bob, 16, 17));

        if (!esJugador) {
            gm.setColor(new Color(180, 35, 35));
            gm.fillRect(-8, (int) (-80 + bob), 16, 5);
        }
        if (m.usaCasco) {
            gm.setColor(new Color(52, 58, 64));
            gm.fillArc(-10, (int) (-85 + bob), 20, 14, 0, 180);
        } else if (m.usaSombrero) {
            gm.setColor(new Color(62, 44, 30));
            gm.fillRoundRect(-13, (int) (-83 + bob), 26, 3, 2, 2);
            gm.fillRoundRect(-8, (int) (-91 + bob), 16, 9, 3, 3);
        }

        if (m.vivo && armaActual != null) {
            Graphics2D ga = (Graphics2D) gm.create();
            ga.translate(0, -54 + bob);
            double angLocal = esJugador ? (-anguloApuntado + animRetroceso * 0.14)
                    : (Math.PI - anguloApuntado - animRetroceso * 0.14);
            if (!esJugador) {
                ga.scale(-1, 1);
                ga.rotate(-(Math.PI - anguloApuntado) + animRetroceso * 0.14);
            } else {
                ga.rotate(angLocal);
            }
            ga.setColor(ch);
            ga.fillRoundRect(-2, -3, 13, 6, 3, 3);
            ga.translate(8, 0);
            armaActual.dibujarArmaEnMano(ga, 0.85);
            ga.dispose();
        }
        gm.dispose();
    }
}
