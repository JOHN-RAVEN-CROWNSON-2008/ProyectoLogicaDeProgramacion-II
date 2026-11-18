package inventario;

import armas.*;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * [POO - AGREGACION DEBIL]
 * Armeria y almacen global compartido entre modos y combatientes.
 * Sus objetos Arma y Suministro persisten aunque un Combatiente caiga.
 */
public class Inventario {
    private final List<Arma> armas = new ArrayList<Arma>();
    private final List<Suministro> suministros = new ArrayList<Suministro>();
    private int recursosAcumulados = 120;
    private int bajasTotales = 0;

    public Inventario() {
        armas.add(new RifleAsalto());
        armas.add(new LanzaGranadas());
        armas.add(new Revolver());
        armas.add(new EspadaKatana());

        suministros.add(new Suministro(TipoSuministro.BOTIQUIN, 3));
        suministros.add(new Suministro(TipoSuministro.CAJA_MUNICION, 3));
        suministros.add(new Suministro(TipoSuministro.RACION, 2));
    }

    public List<Arma> getArmas() { return armas; }

    public Arma getArma(int indice) {
        if (indice < 0 || indice >= armas.size()) return armas.get(0);
        return armas.get(indice);
    }

    public List<Suministro> getSuministros() { return suministros; }

    public int getCantidadSuministro(TipoSuministro tipo) {
        for (Suministro s : suministros) {
            if (s.getTipo() == tipo) return s.getCantidad();
        }
        return 0;
    }

    public void agregarSuministro(TipoSuministro tipo, int cantidad) {
        for (Suministro s : suministros) {
            if (s.getTipo() == tipo) {
                s.agregar(cantidad);
                recursosAcumulados += cantidad * 15;
                return;
            }
        }
        suministros.add(new Suministro(tipo, cantidad));
        recursosAcumulados += cantidad * 15;
    }

    public boolean comprarSuministroConBotin(TipoSuministro tipo, int costo) {
        if (recursosAcumulados < costo) return false;
        recursosAcumulados -= costo;
        for (Suministro s : suministros) {
            if (s.getTipo() == tipo) {
                s.agregar(1);
                return true;
            }
        }
        suministros.add(new Suministro(tipo, 1));
        return true;
    }

    public boolean usarSuministro(TipoSuministro tipo) {
        for (Suministro s : suministros) {
            if (s.getTipo() == tipo) {
                return s.consumirUno();
            }
        }
        return false;
    }

    public void recargarTodasLasArmas() {
        for (Arma a : armas) {
            if (a instanceof RifleAsalto) a.recargar(24);
            else if (a instanceof LanzaGranadas) a.recargar(4);
            else if (a instanceof Revolver) a.recargar(12);
        }
    }

    public String robarSuministroAleatorio(Random rng) {
        List<Suministro> disponibles = new ArrayList<Suministro>();
        for (Suministro s : suministros) {
            if (s.getCantidad() > 0) disponibles.add(s);
        }
        if (disponibles.isEmpty()) return null;
        Suministro elegido = disponibles.get(rng.nextInt(disponibles.size()));
        elegido.consumirUno();
        recursosAcumulados = Math.max(0, recursosAcumulados - 15);
        return elegido.getTipo().nombreLegible;
    }

    public int getRecursosAcumulados() { return recursosAcumulados; }
    public void sumarPuntosRecurso(int pts) { recursosAcumulados += pts; }
    public int getBajasTotales() { return bajasTotales; }
    public void incrementarBajas() { bajasTotales++; }
}
