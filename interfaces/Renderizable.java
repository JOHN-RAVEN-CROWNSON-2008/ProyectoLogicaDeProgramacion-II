package interfaces;

import java.awt.Graphics2D;

/**
 * [POO - ABSTRACCION (Interfaz)]
 * Contrato grafico para toda entidad capaz de dibujarse en el lienzo 2D.
 */
public interface Renderizable {
    void renderizar(Graphics2D g);
}
