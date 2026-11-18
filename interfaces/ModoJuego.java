package interfaces;

import java.awt.Graphics2D;

/**
 * [POO - ABSTRACCION (Interfaz)]
 * Contrato para los distintos modos jugables del motor (Hordas, Duelo 1v1, Armeria).
 */
public interface ModoJuego {
    void iniciarModo();
    void actualizarLogica(double dt);
    void dibujarEscena(Graphics2D g);
    String getNombreModo();
}
