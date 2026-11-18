package inventario;

import java.awt.Color;

/**
 * Tipos de suministros disponibles en el sistema de agregacion.
 */
public enum TipoSuministro {
    BOTIQUIN("Botiquin Medico", 45, new Color(220, 65, 65)),
    CAJA_MUNICION("Caja de Municion", 1, new Color(230, 175, 55)),
    RACION("Racion de Campana", 25, new Color(85, 190, 115));

    public final String nombreLegible;
    public final int valor;
    public final Color color;

    TipoSuministro(String nombreLegible, int valor, Color color) {
        this.nombreLegible = nombreLegible;
        this.valor = valor;
        this.color = color;
    }
}
