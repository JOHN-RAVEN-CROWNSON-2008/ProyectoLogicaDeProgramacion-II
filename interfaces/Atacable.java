package interfaces;

/**
 * [POO - ABSTRACCION (Interfaz)]
 * Contrato de combate para cualquier entidad susceptible de recibir dano.
 */
public interface Atacable {
    void recibirDano(int cantidad);
    boolean estaVivo();
    int getVida();
    int getVidaMaxima();
}
