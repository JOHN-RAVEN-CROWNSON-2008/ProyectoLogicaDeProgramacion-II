package util;

/**
 * Constantes fisicas y de resolucion logica compartidas por todo el motor 2D.
 */
public final class ConstantesJuego {
    public static final int ANCHO_VIRTUAL = 1280;
    public static final int ALTO_VIRTUAL = 720;
    public static final int Y_SUELO = 582;
    public static final double GRAVEDAD_BASE = 540.0;

    private ConstantesJuego() {
    }

    public static double limitar(double valor, double min, double max) {
        return Math.max(min, Math.min(max, valor));
    }
}
