package modos;

import armas.Arma;
import audio.GestorSonido;
import efectos.TextoFlotante;
import entidades.Proyectil;
import entidades.Superviviente;
import entidades.TipoProyectil;
import escenario.EscenarioApocaliptico;
import inventario.Inventario;
import inventario.Suministro;
import inventario.TipoSuministro;
import util.ConstantesJuego;
import java.awt.*;
import java.awt.event.KeyEvent;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

/**
 * [POO - ABSTRACCION (Implementa ModoJuego) + AGREGACION DEBIL (Inventario)]
 * MODO 3: Armeria, Gestion de Recursos y Campo de Tiro Interactivo.
 * Permite administrar el Inventario compartido y probar todas las armas
 * con el raton o con la tecla X al 5% y al 100% contra blancos calibrados.
 */
public class ModoArmeriaCampoTiro extends BaseModoJuego {
    private static final class BlancoPractica {
        final double x;
        final String etiqueta;
        int hp = 120;
        final int hpMax = 120;
        double timerRespawn = 0;

        BlancoPractica(double x, String etiqueta) {
            this.x = x;
            this.etiqueta = etiqueta;
        }
    }

    private Superviviente tirador;
    private final List<BlancoPractica> blancos = new ArrayList<BlancoPractica>();

    private final Rectangle btnRecargar = new Rectangle(925, 250, 315, 38);
    private final Rectangle btnComprarBotiquin = new Rectangle(925, 300, 152, 34);
    private final Rectangle btnComprarMunicion = new Rectangle(1088, 300, 152, 34);
    private final Rectangle btnComprarRacion = new Rectangle(925, 342, 315, 34);

    public ModoArmeriaCampoTiro(Inventario inventario, EscenarioApocaliptico escenario) {
        super(inventario, escenario);
    }

    @Override
    public String getNombreModo() {
        return "MODO 3: ARMERIA Y CAMPO DE TIRO";
    }

    @Override
    public void iniciarModo() {
        camaraX = 0;
        proyectiles.clear();
        particulas.clear();
        ondas.clear();
        textos.clear();
        blancos.clear();
        arrastrando = false;
        cargandoTeclaX = false;

        tirador = new Superviviente("Campo de Tiro", 135, ConstantesJuego.Y_SUELO, inventario);
        blancos.add(new BlancoPractica(315, "Blanco 5%"));
        blancos.add(new BlancoPractica(620, "Blanco Medio"));
        blancos.add(new BlancoPractica(980, "Blanco 100%"));
    }

    @Override
    public void actualizarLogica(double dt) {
        actualizarEfectos(dt);
        if (!arrastrando && cursorEnArena) {
            tirador.setAnguloApuntado(calcularAnguloHaciaCursor(tirador.getX() + 24, tirador.getY() - 56, -15, 84));
        }
        tirador.actualizar(dt);

        for (BlancoPractica b : blancos) {
            if (b.hp <= 0) {
                b.timerRespawn -= dt;
                if (b.timerRespawn <= 0) b.hp = b.hpMax;
            }
        }

        Iterator<Proyectil> it = proyectiles.iterator();
        while (it.hasNext()) {
            Proyectil p = it.next();
            p.actualizarConViento(dt, 0.0);
            if (!p.estaYaLanzado()) continue;

            boolean impacto = false;
            if (p.getY() >= ConstantesJuego.Y_SUELO) {
                p.setPosicion(p.getX(), ConstantesJuego.Y_SUELO - 2);
                impacto = true;
            } else if (p.getX() > 1320 || p.getX() < -40 || p.getY() < -450) {
                it.remove();
                continue;
            } else {
                for (BlancoPractica b : blancos) {
                    if (b.hp > 0 && Math.abs(p.getX() - b.x) <= 24
                            && p.getY() >= ConstantesJuego.Y_SUELO - 92 && p.getY() <= ConstantesJuego.Y_SUELO) {
                        impacto = true;
                        if (p.getTipo() != TipoProyectil.GRANADA) {
                            b.hp = Math.max(0, b.hp - p.getDano());
                            if (b.hp == 0) b.timerRespawn = 1.8;
                            GestorSonido.reproducirImpacto();
                            generarImpacto(p.getX(), p.getY(), new Color(255, 200, 90), 10);
                            textos.add(new TextoFlotante(b.x, ConstantesJuego.Y_SUELO - 108,
                                    "-" + p.getDano() + " (" + b.etiqueta + ")", new Color(255, 215, 95), 14));
                        }
                        break;
                    }
                }
            }

            if (impacto) {
                if (p.getTipo() == TipoProyectil.GRANADA) {
                    generarExplosion(p.getX(), p.getY(), p.getRadioExplosion());
                    for (BlancoPractica b : blancos) {
                        if (b.hp > 0 && Math.hypot(b.x - p.getX(), (ConstantesJuego.Y_SUELO - 45) - p.getY()) <= p.getRadioExplosion()) {
                            b.hp = Math.max(0, b.hp - p.getDano());
                            if (b.hp == 0) b.timerRespawn = 1.8;
                            textos.add(new TextoFlotante(b.x, ConstantesJuego.Y_SUELO - 108,
                                    "-" + p.getDano() + " AoE", new Color(255, 155, 65), 15));
                        }
                    }
                } else if (p.getY() >= ConstantesJuego.Y_SUELO - 3) {
                    GestorSonido.reproducirImpacto();
                    generarImpacto(p.getX(), ConstantesJuego.Y_SUELO - 2, new Color(165, 160, 145), 6);
                }
                it.remove();
            }
        }
    }

    private void ejecutarDisparoPractica(double angulo, double potencia) {
        List<Proyectil> lista = tirador.disparar(angulo, potencia);
        if (lista.isEmpty() && tirador.getArmaActual().getMunicion() == 0) {
            textos.add(new TextoFlotante(tirador.getX() + 40, tirador.getY() - 130,
                    "\u00a1Sin municion! Pulsa [E] o usa el panel de Armeria", new Color(255, 120, 95), 14));
            return;
        }
        if (!lista.isEmpty()) {
            reproducirSonidoArma(tirador.getArmaActual());
            proyectiles.addAll(lista);
        }
    }

    @Override
    protected void dispararConTeclaX(double potencia) {
        double xBoca = tirador.getX() + 24;
        double yBoca = tirador.getY() - 56;
        double ang = calcularAnguloHaciaCursor(xBoca, yBoca, -15, 84);
        ejecutarDisparoPractica(ang, potencia);
        textos.add(new TextoFlotante(tirador.getX() + 30, tirador.getY() - 140,
                "Prueba [X]: " + (int) Math.round(potencia * 100) + "%", new Color(115, 225, 255), 13));
    }

    @Override
    public void dibujarEscena(Graphics2D g) {
        escenario.dibujarFondo(g, 0, ConstantesJuego.ANCHO_VIRTUAL);
        escenario.dibujarSueloMundo(g, ConstantesJuego.ANCHO_VIRTUAL);

        for (BlancoPractica b : blancos) {
            dibujarBlanco(g, b);
        }
        tirador.renderizar(g);
        for (Proyectil p : proyectiles) p.renderizar(g);

        double xBoca = tirador.getX() + 24 * Math.cos(tirador.getAnguloApuntado());
        double yBoca = (tirador.getY() - 56) - 24 * Math.sin(tirador.getAnguloApuntado());
        if (arrastrando) {
            double[] vec = calcularVectorDisparo(-15, 84);
            tirador.setAnguloApuntado(vec[0]);
            dibujarGuiaParabolica(g, xBoca, yBoca, vec[0], vec[1], tirador.getArmaActual(), 0.0, false);
        } else if (cursorEnArena && cursorVirtualX < 900) {
            double ang = calcularAnguloHaciaCursor(tirador.getX() + 24, tirador.getY() - 56, -15, 84);
            double pot = cargandoTeclaX && tiempoCargaX >= 0.18 ? potenciaCargaX : getPotenciaPresetX();
            dibujarGuiaParabolica(g, xBoca, yBoca, ang, pot, tirador.getArmaActual(), 0.0, true);
        }
        dibujarBarraCargaX(g, tirador.getX(), tirador.getY());
        if (cursorVirtualX < 900) dibujarMiraCursor(g);

        dibujarEfectos(g);
        dibujarPanelArmeriaLateral(g);
    }

    private void dibujarBlanco(Graphics2D g, BlancoPractica b) {
        int ys = ConstantesJuego.Y_SUELO;
        g.setColor(new Color(95, 70, 48));
        g.fillRect((int) b.x - 4, ys - 50, 8, 50);

        if (b.hp <= 0) {
            g.setFont(new Font("SansSerif", Font.BOLD, 11));
            g.setColor(new Color(220, 220, 220));
            g.drawString("Reponiendo...", (int) b.x - 32, ys - 60);
            return;
        }
        g.setColor(new Color(235, 235, 235));
        g.fillOval((int) b.x - 22, ys - 90, 44, 44);
        g.setColor(new Color(215, 55, 55));
        g.fillOval((int) b.x - 15, ys - 83, 30, 30);
        g.setColor(Color.WHITE);
        g.fillOval((int) b.x - 8, ys - 76, 16, 16);
        g.setColor(new Color(215, 55, 55));
        g.fillOval((int) b.x - 3, ys - 71, 6, 6);

        g.setFont(new Font("SansSerif", Font.BOLD, 11));
        g.setColor(new Color(255, 225, 130));
        g.drawString(b.etiqueta + " (" + b.hp + ")", (int) b.x - 36, ys - 98);
    }

    private void dibujarPanelArmeriaLateral(Graphics2D g) {
        g.setColor(new Color(18, 22, 30, 228));
        g.fillRoundRect(910, 72, 345, 320, 14, 14);
        g.setColor(new Color(95, 115, 140));
        g.drawRoundRect(910, 72, 345, 320, 14, 14);

        g.setFont(new Font("SansSerif", Font.BOLD, 15));
        g.setColor(new Color(240, 200, 100));
        g.drawString("ARMERIA COMPARTIDA (AGREGACION)", 925, 97);

        List<Arma> armas = inventario.getArmas();
        for (int i = 0; i < armas.size(); i++) {
            Arma a = armas.get(i);
            int ay = 114 + i * 32;
            g.setFont(new Font("SansSerif", Font.BOLD, 12));
            g.setColor(a == tirador.getArmaActual() ? a.getColorAcento() : Color.WHITE);
            String muni = a.esInfinita() ? "Infinita" : (a.getMunicion() + "/" + a.getMunicionMaxima());
            g.drawString("[" + (i + 1) + "] " + a.getNombre() + "  (" + muni + ")", 925, ay + 12);
            g.setFont(new Font("SansSerif", Font.PLAIN, 11));
            g.setColor(new Color(175, 185, 200));
            g.drawString("Dano: " + a.getDanoBase() + " | " + a.getDescripcionCorta(), 925, ay + 25);
        }

        boolean tieneCaja = inventario.getCantidadSuministro(TipoSuministro.CAJA_MUNICION) > 0;
        dibujarBotonPanel(g, btnRecargar,
                tieneCaja ? "Usar 1 Caja: Recargar Todas" : "Sin Cajas (Compra abajo)",
                tieneCaja ? new Color(65, 120, 78) : new Color(60, 64, 72));
        dibujarBotonPanel(g, btnComprarBotiquin, "+Botiquin (30)", new Color(165, 60, 60));
        dibujarBotonPanel(g, btnComprarMunicion, "+Municion (30)", new Color(165, 125, 45));
        dibujarBotonPanel(g, btnComprarRacion, "+Comprar Racion de Campana (25 Botin)", new Color(58, 128, 92));

        // Instruccion de campo de tiro
        g.setColor(new Color(20, 24, 32, 205));
        g.fillRoundRect(25, 72, 540, 48, 10, 10);
        g.setFont(new Font("SansSerif", Font.BOLD, 12));
        g.setColor(new Color(130, 225, 255));
        g.drawString("CAMPO DE TIRO: Apunta con el cursor y pulsa [X] (5% o 100%) o arrastra para probar armas.", 38, 92);
        g.setColor(new Color(220, 225, 235));
        g.setFont(new Font("SansSerif", Font.PLAIN, 11));
        g.drawString("Los cambios de municion y botiquines persisten en el Modo 1 y Modo 2 (Agregacion Debil).", 38, 110);
    }

    private void dibujarBotonPanel(Graphics2D g, Rectangle r, String txt, Color bg) {
        boolean hover = cursorVirtualX >= r.x && cursorVirtualX <= r.x + r.width
                && cursorVirtualY >= r.y && cursorVirtualY <= r.y + r.height;
        g.setColor(hover ? bg.brighter() : bg);
        g.fillRoundRect(r.x, r.y, r.width, r.height, 8, 8);
        g.setColor(new Color(255, 255, 255, hover ? 200 : 90));
        g.drawRoundRect(r.x, r.y, r.width, r.height, 8, 8);
        g.setFont(new Font("SansSerif", Font.BOLD, 12));
        g.setColor(Color.WHITE);
        FontMetrics fm = g.getFontMetrics();
        g.drawString(txt, r.x + (r.width - fm.stringWidth(txt)) / 2, r.y + r.height / 2 + 4);
    }

    @Override
    public void alPresionarRaton(double xVirtual, double yVirtual) {
        if (btnRecargar.contains(xVirtual, yVirtual)) {
            usarSuministroDesdeHud(TipoSuministro.CAJA_MUNICION);
            return;
        }
        if (btnComprarBotiquin.contains(xVirtual, yVirtual)) {
            comprar(TipoSuministro.BOTIQUIN, 30);
            return;
        }
        if (btnComprarMunicion.contains(xVirtual, yVirtual)) {
            comprar(TipoSuministro.CAJA_MUNICION, 30);
            return;
        }
        if (btnComprarRacion.contains(xVirtual, yVirtual)) {
            comprar(TipoSuministro.RACION, 25);
            return;
        }

        if (xVirtual < 900) {
            arrastrando = true;
            dragStartX = xVirtual;
            dragStartY = yVirtual;
            dragActualX = xVirtual;
            dragActualY = yVirtual;
        }
    }

    private void comprar(TipoSuministro tipo, int costo) {
        if (inventario.comprarSuministroConBotin(tipo, costo)) {
            GestorSonido.reproducirSuministro();
            textos.add(new TextoFlotante(720, 220, "+1 " + tipo.nombreLegible, tipo.color, 16));
        } else {
            textos.add(new TextoFlotante(720, 220, "Botin insuficiente (" + costo + ")", new Color(255, 95, 95), 15));
        }
    }

    @Override
    public void alArrastrarRaton(double xVirtual, double yVirtual) {
        cursorVirtualX = xVirtual;
        cursorVirtualY = yVirtual;
        if (!arrastrando) return;
        dragActualX = xVirtual;
        dragActualY = yVirtual;
    }

    @Override
    public void alSoltarRaton(double xVirtual, double yVirtual) {
        if (!arrastrando) return;
        arrastrando = false;
        double[] vec = calcularVectorDisparo(-15, 84);
        ejecutarDisparoPractica(vec[0], vec[1]);
    }

    @Override
    public void alPresionarTecla(int keyCode, boolean shiftDown) {
        if (keyCode == KeyEvent.VK_1) equiparArmaDesdeHud(0);
        else if (keyCode == KeyEvent.VK_2) equiparArmaDesdeHud(1);
        else if (keyCode == KeyEvent.VK_3) equiparArmaDesdeHud(2);
        else if (keyCode == KeyEvent.VK_4) equiparArmaDesdeHud(3);
        else if (keyCode == KeyEvent.VK_Q) usarSuministroDesdeHud(TipoSuministro.BOTIQUIN);
        else if (keyCode == KeyEvent.VK_E) usarSuministroDesdeHud(TipoSuministro.CAJA_MUNICION);
        else if (keyCode == KeyEvent.VK_R) usarSuministroDesdeHud(TipoSuministro.RACION);
        else if (keyCode == KeyEvent.VK_C) alternarPotenciaX();
        else if (keyCode == KeyEvent.VK_X && !cargandoTeclaX) {
            cargandoTeclaX = true;
            tiempoCargaX = 0.0;
            potenciaCargaX = 0.05;
        }
    }

    @Override
    public void equiparArmaDesdeHud(int indice) {
        if (tirador != null) {
            tirador.equiparArmaPorIndice(indice);
            GestorSonido.reproducirClickMenu();
        }
    }

    @Override
    public void usarSuministroDesdeHud(TipoSuministro tipo) {
        if (!inventario.usarSuministro(tipo)) {
            textos.add(new TextoFlotante(tirador.getX() + 40, tirador.getY() - 125,
                    "Sin " + tipo.nombreLegible, new Color(200, 200, 200), 14));
            return;
        }
        GestorSonido.reproducirSuministro();
        if (tipo == TipoSuministro.CAJA_MUNICION) {
            inventario.recargarTodasLasArmas();
            textos.add(new TextoFlotante(tirador.getX() + 40, tirador.getY() - 125,
                    "+MUNICION RECARGADA", new Color(255, 210, 80), 16));
        } else {
            tirador.curar(tipo.valor);
            textos.add(new TextoFlotante(tirador.getX() + 40, tirador.getY() - 125,
                    "+" + tipo.valor + " HP (" + tipo.nombreLegible + ")", tipo.color, 16));
        }
    }

    public Superviviente getTirador() { return tirador; }
}
