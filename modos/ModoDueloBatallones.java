package modos;

import armas.Arma;
import audio.GestorSonido;
import efectos.TextoFlotante;
import entidades.*;
import escenario.EscenarioApocaliptico;
import escenario.ObstaculoTerreno;
import inventario.Inventario;
import inventario.TipoSuministro;
import util.ConstantesJuego;
import java.awt.*;
import java.awt.event.KeyEvent;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

/**
 * [POO - ABSTRACCION (Implementa ModoJuego) + COMPOSICION FUERTE (Batallon)]
 * MODO 2: Duelo Tactico por Turnos 1v1 (Batallon vs Batallon - Estilo Bowmasters).
 */
public class ModoDueloBatallones extends BaseModoJuego {
    public enum FaseTurno {
        TURNO_JUGADOR,
        PROYECTIL_EN_VUELO,
        PAUSA_IMPACTO,
        TURNO_IA,
        FIN_DUELO
    }

    public static final int ANCHO_MUNDO_DUELO = 1860;

    private Batallon batallonJugador;
    private Batallon batallonEnemigo;
    private final List<ObstaculoTerreno> obstaculos = new ArrayList<ObstaculoTerreno>();

    private FaseTurno fase = FaseTurno.TURNO_JUGADOR;
    private boolean ultimoDisparoFueJugador = true;
    private double vientoActual = 0.0;
    private double camaraObjetivoX = 0.0;
    private double timerFase = 0.0;
    private int turnoIA = 0;
    private String ganadorTexto = "";
    private boolean paneoManualIzq = false;
    private boolean paneoManualDer = false;
    private boolean botinProcesadoEnTurno = false;

    public ModoDueloBatallones(Inventario inventario, EscenarioApocaliptico escenario) {
        super(inventario, escenario);
    }

    @Override
    public String getNombreModo() {
        return "MODO 2: DUELO 1v1 DE BATALLONES";
    }

    @Override
    public void iniciarModo() {
        proyectiles.clear();
        particulas.clear();
        ondas.clear();
        textos.clear();
        obstaculos.clear();

        batallonJugador = new Batallon("Batallon Aliado", 210, ConstantesJuego.Y_SUELO,
                320, 8, true, inventario);
        Inventario invRival = new Inventario();
        batallonEnemigo = new Batallon("Batallon Saqueador", 1620, ConstantesJuego.Y_SUELO,
                320, 8, false, invRival);

        obstaculos.add(new ObstaculoTerreno(780, ConstantesJuego.Y_SUELO, 185, 118, "AUTOBUS"));
        obstaculos.add(new ObstaculoTerreno(1175, ConstantesJuego.Y_SUELO, 130, 74, "COCHE"));

        camaraX = 0;
        camaraObjetivoX = 0;
        turnoIA = 0;
        botinProcesadoEnTurno = false;
        cargandoTeclaX = false;
        paneoManualIzq = false;
        paneoManualDer = false;
        fase = FaseTurno.TURNO_JUGADOR;
        sortearViento();
        textos.add(new TextoFlotante(370, 230, "\u00a1TU TURNO! ARRASTRA O PULSA [X]", new Color(255, 220, 100), 20));
    }

    private void sortearViento() {
        vientoActual = (rng.nextDouble() * 2.0 - 1.0) * 125.0;
    }

    @Override
    public void actualizarLogica(double dt) {
        actualizarEfectos(dt);
        batallonJugador.actualizar(dt);
        batallonEnemigo.actualizar(dt);

        if (fase == FaseTurno.TURNO_JUGADOR) {
            if (!arrastrando && cursorEnArena) {
                batallonJugador.setAnguloApuntado(
                        calcularAnguloHaciaCursor(batallonJugador.getX() + 32, batallonJugador.getY() - 56, 8, 82));
            }
            if (paneoManualIzq) camaraObjetivoX -= 620 * dt;
            if (paneoManualDer) camaraObjetivoX += 620 * dt;
            camaraObjetivoX = limitarCamara(camaraObjetivoX);
        } else if (fase == FaseTurno.PROYECTIL_EN_VUELO) {
            actualizarProyectilesDuelo(dt);
        } else if (fase == FaseTurno.PAUSA_IMPACTO) {
            timerFase -= dt;
            if (timerFase <= 0) {
                avanzarSiguienteTurno();
            }
        } else if (fase == FaseTurno.TURNO_IA) {
            camaraObjetivoX = limitarCamara(batallonEnemigo.getX() - 920);
            timerFase -= dt;
            if (timerFase <= 0) {
                ejecutarDisparoIA();
            }
        }

        camaraX += (camaraObjetivoX - camaraX) * Math.min(1.0, dt * 6.5);
        camaraX = limitarCamara(camaraX);
    }

    private double limitarCamara(double cx) {
        return ConstantesJuego.limitar(cx, 0.0, ANCHO_MUNDO_DUELO - ConstantesJuego.ANCHO_VIRTUAL);
    }

    private void actualizarProyectilesDuelo(double dt) {
        Proyectil lider = null;
        for (Proyectil p : proyectiles) {
            if (p.estaActivo() && p.estaYaLanzado()) {
                lider = p;
                break;
            }
        }
        if (lider != null) {
            camaraObjetivoX = limitarCamara(lider.getX() - ConstantesJuego.ANCHO_VIRTUAL * 0.45);
        }

        Iterator<Proyectil> it = proyectiles.iterator();
        while (it.hasNext()) {
            Proyectil p = it.next();
            p.actualizarConViento(dt, vientoActual);
            if (!p.estaYaLanzado()) continue;

            boolean impacto = false;
            Batallon objetivoDirecto = null;

            if (p.getX() < -120 || p.getX() > ANCHO_MUNDO_DUELO + 120 || p.getY() < -900) {
                it.remove();
                continue;
            }
            if (p.getY() >= ConstantesJuego.Y_SUELO) {
                p.setPosicion(p.getX(), ConstantesJuego.Y_SUELO - 2);
                impacto = true;
            }

            if (!impacto) {
                for (ObstaculoTerreno obs : obstaculos) {
                    if (obs.colisiona(p.getX(), p.getY())) {
                        impacto = true;
                        GestorSonido.reproducirImpacto();
                        generarImpacto(p.getX(), p.getY(), new Color(180, 145, 95), 12);
                        break;
                    }
                }
            }

            if (!impacto) {
                Batallon blanco = p.isFaccionJugador() ? batallonEnemigo : batallonJugador;
                if (blanco.estaVivo()
                        && Math.abs(p.getX() - blanco.getX()) <= 78
                        && p.getY() >= blanco.getY() - 95
                        && p.getY() <= blanco.getY()) {
                    impacto = true;
                    objetivoDirecto = blanco;
                }
            }

            if (impacto) {
                resolverImpactoDuelo(p, objetivoDirecto);
                it.remove();
            }
        }

        if (proyectiles.isEmpty()) {
            fase = FaseTurno.PAUSA_IMPACTO;
            timerFase = 1.05;
        }
    }

    private void resolverImpactoDuelo(Proyectil p, Batallon objetivoDirecto) {
        if (p.getTipo() == TipoProyectil.GRANADA) {
            generarExplosion(p.getX(), p.getY(), p.getRadioExplosion());
            aplicarDanoAreaBatallon(batallonEnemigo, p);
            aplicarDanoAreaBatallon(batallonJugador, p);
        } else if (objetivoDirecto != null) {
            boolean crit = rng.nextDouble() < 0.25;
            double mult = crit ? p.getMultiplicadorCritico() : 1.0;
            int dano = objetivoDirecto.calcularDano(p.getDano(), mult, p.isIgnoraArmadura());
            aplicarDanoYBotin(objetivoDirecto, dano, crit, p.getX(), p.getY());
        } else {
            GestorSonido.reproducirImpacto();
            generarImpacto(p.getX(), p.getY(), new Color(165, 160, 140), 8);
        }
    }

    private void aplicarDanoAreaBatallon(Batallon b, Proyectil p) {
        if (!b.estaVivo()) return;
        double dist = Math.hypot(b.getX() - p.getX(), (b.getY() - 45) - p.getY());
        if (dist <= p.getRadioExplosion() + 45) {
            double factor = ConstantesJuego.limitar(1.0 - (dist / (p.getRadioExplosion() + 70)) * 0.45, 0.4, 1.0);
            int dano = b.calcularDano((int) (p.getDano() * factor), 1.0, p.isIgnoraArmadura());
            aplicarDanoYBotin(b, dano, false, b.getX(), b.getY() - 55);
        }
    }

    private void aplicarDanoYBotin(Batallon objetivo, int dano, boolean critico, double ix, double iy) {
        int vivosAntes = objetivo.getMiembrosVivos();
        objetivo.recibirDano(dano);
        int vivosDespues = objetivo.getMiembrosVivos();

        intensidadShake = Math.max(intensidadShake, 10.0);
        GestorSonido.reproducirImpacto();
        generarImpacto(ix, iy, new Color(210, 35, 35), 14);
        textos.add(new TextoFlotante(objetivo.getX(), objetivo.getY() - 135,
                (critico ? "\u00a1CR\u00cdTICO! -" : "-") + dano + " HP",
                critico ? new Color(255, 225, 70) : new Color(255, 95, 85), 20));

        if (vivosDespues < vivosAntes) {
            textos.add(new TextoFlotante(objetivo.getX(), objetivo.getY() - 165,
                    "\u00a1MIEMBRO ABATIDO!", new Color(255, 155, 65), 16));
        }

        if (!botinProcesadoEnTurno) {
            botinProcesadoEnTurno = true;
            if (objetivo.isEsJugador()) {
                String robado = inventario.robarSuministroAleatorio(rng);
                if (robado != null) {
                    textos.add(new TextoFlotante(objetivo.getX(), objetivo.getY() - 190,
                            "\u00a1RECURSOS ROBADOS! (-1 " + robado + ")", new Color(255, 75, 110), 15));
                }
            } else {
                inventario.sumarPuntosRecurso(40);
                if (rng.nextDouble() < 0.55) {
                    TipoSuministro botin = rng.nextBoolean() ? TipoSuministro.CAJA_MUNICION : TipoSuministro.BOTIQUIN;
                    inventario.agregarSuministro(botin, 1);
                    GestorSonido.reproducirSuministro();
                    textos.add(new TextoFlotante(objetivo.getX(), objetivo.getY() - 190,
                            "\u00a1BOT\u00cdN RECUPERADO! (+1 " + botin.nombreLegible + ")", new Color(110, 240, 145), 15));
                }
            }
        }
    }

    private void avanzarSiguienteTurno() {
        if (!batallonEnemigo.estaVivo()) {
            batallonEnemigo.destruirBatallon();
            inventario.sumarPuntosRecurso(200);
            inventario.incrementarBajas();
            ganadorTexto = "\u00a1VICTORIA DEL BATALLON ALIADO!";
            fase = FaseTurno.FIN_DUELO;
            GestorSonido.reproducirVictoria();
            camaraObjetivoX = limitarCamara(batallonEnemigo.getX() - 640);
            return;
        }
        if (!batallonJugador.estaVivo()) {
            batallonJugador.destruirBatallon();
            ganadorTexto = "DERROTA: LOS SAQUEADORES TOMARON TUS RECURSOS";
            fase = FaseTurno.FIN_DUELO;
            GestorSonido.reproducirDerrota();
            camaraObjetivoX = 0;
            return;
        }

        sortearViento();
        if (ultimoDisparoFueJugador) {
            fase = FaseTurno.TURNO_IA;
            timerFase = 1.0;
            camaraObjetivoX = limitarCamara(batallonEnemigo.getX() - 920);
        } else {
            fase = FaseTurno.TURNO_JUGADOR;
            camaraObjetivoX = 0;
            textos.add(new TextoFlotante(batallonJugador.getX() + 90, 260,
                    "\u00a1TU TURNO!", new Color(255, 220, 100), 22));
        }
    }

    private void ejecutarDisparoIA() {
        turnoIA++;
        int idxArma = rng.nextInt(3);
        Arma armaIA = batallonEnemigo.getInventario().getArma(idxArma);
        armaIA.recargar(10);
        batallonEnemigo.setArmaActual(armaIA);

        double xOrigen = batallonEnemigo.getX() - 32;
        double yOrigen = batallonEnemigo.getY() - 56;
        double mejorAngulo = Math.toRadians(136);
        double mejorPotencia = 0.78;
        double mejorErrorDist = Double.MAX_VALUE;

        for (int aDeg = 122; aDeg <= 152; aDeg += 3) {
            double ang = Math.toRadians(aDeg);
            for (double pot = 0.45; pot <= 1.0; pot += 0.04) {
                double distImpacto = simularTrayectoria(xOrigen, yOrigen, ang, pot, armaIA);
                double err = Math.abs(distImpacto - batallonJugador.getX());
                if (err < mejorErrorDist) {
                    mejorErrorDist = err;
                    mejorAngulo = ang;
                    mejorPotencia = pot;
                }
            }
        }

        double errorMaximo = Math.max(0.015, 0.14 - (turnoIA - 1) * 0.025);
        double anguloFinal = mejorAngulo + (rng.nextDouble() * 2.0 - 1.0) * errorMaximo * 0.7;
        double potenciaFinal = ConstantesJuego.limitar(
                mejorPotencia + (rng.nextDouble() * 2.0 - 1.0) * errorMaximo, 0.25, 1.0);

        List<Proyectil> disparos = batallonEnemigo.dispararEnUnisono(anguloFinal, potenciaFinal);
        reproducirSonidoArma(armaIA);
        proyectiles.addAll(disparos);
        generarImpacto(xOrigen, yOrigen, new Color(255, 200, 100), 8);
        botinProcesadoEnTurno = false;
        ultimoDisparoFueJugador = false;
        fase = FaseTurno.PROYECTIL_EN_VUELO;
    }

    private double simularTrayectoria(double x0, double y0, double angulo, double potencia, Arma arma) {
        double v0 = arma.calcularVelocidadInicial(potencia);
        double vx = v0 * Math.cos(angulo);
        double vy = -v0 * Math.sin(angulo);
        double gEff = ConstantesJuego.GRAVEDAD_BASE * arma.getFactorGravedad();
        double px = x0, py = y0;
        double dtSim = 0.02;

        for (int step = 0; step < 220; step++) {
            vx += vientoActual * dtSim;
            vy += gEff * dtSim;
            px += vx * dtSim;
            py += vy * dtSim;

            for (ObstaculoTerreno obs : obstaculos) {
                if (obs.colisiona(px, py)) return px;
            }
            if (py >= ConstantesJuego.Y_SUELO) return px;
        }
        return px;
    }

    private void ejecutarDisparoJugador(double angulo, double potencia) {
        Arma arma = batallonJugador.getArmaActual();
        if (arma == null || !arma.puedeDisparar()) {
            textos.add(new TextoFlotante(batallonJugador.getX() + 50, batallonJugador.getY() - 140,
                    "\u00a1Sin municion! Usa [E] o cambia a [4] Katana", new Color(255, 110, 85), 16));
            return;
        }
        List<Proyectil> disparos = batallonJugador.dispararEnUnisono(angulo, potencia);
        if (!disparos.isEmpty()) {
            reproducirSonidoArma(arma);
            proyectiles.addAll(disparos);
            generarImpacto(batallonJugador.getX() + 32, batallonJugador.getY() - 56,
                    new Color(255, 220, 120), 8);
            botinProcesadoEnTurno = false;
            ultimoDisparoFueJugador = true;
            fase = FaseTurno.PROYECTIL_EN_VUELO;
        }
    }

    @Override
    protected void dispararConTeclaX(double potencia) {
        if (fase != FaseTurno.TURNO_JUGADOR) return;
        camaraObjetivoX = 0;
        double xBoca = batallonJugador.getX() + 32;
        double yBoca = batallonJugador.getY() - 56;
        double ang = calcularAnguloHaciaCursor(xBoca, yBoca, 8, 82);
        ejecutarDisparoJugador(ang, potencia);
    }

    @Override
    public void dibujarEscena(Graphics2D g) {
        escenario.dibujarFondo(g, camaraX, ANCHO_MUNDO_DUELO);

        Graphics2D gw = (Graphics2D) g.create();
        gw.translate(-camaraX, 0);

        escenario.dibujarSueloMundo(gw, ANCHO_MUNDO_DUELO);
        for (ObstaculoTerreno obs : obstaculos) obs.renderizar(gw);

        batallonJugador.renderizar(gw);
        batallonEnemigo.renderizar(gw);

        for (Proyectil p : proyectiles) p.renderizar(gw);

        if (fase == FaseTurno.TURNO_JUGADOR) {
            double xBoca = batallonJugador.getX() + 32;
            double yBoca = batallonJugador.getY() - 56;
            if (arrastrando) {
                double[] vec = calcularVectorDisparo(8, 82);
                batallonJugador.setAnguloApuntado(vec[0]);
                dibujarGuiaParabolica(gw, xBoca, yBoca, vec[0], vec[1], batallonJugador.getArmaActual(), vientoActual, false);
            } else if (cursorEnArena) {
                double ang = calcularAnguloHaciaCursor(xBoca, yBoca, 8, 82);
                double pot = cargandoTeclaX && tiempoCargaX >= 0.18 ? potenciaCargaX : getPotenciaPresetX();
                dibujarGuiaParabolica(gw, xBoca, yBoca, ang, pot, batallonJugador.getArmaActual(), vientoActual, true);
            }
            dibujarBarraCargaX(gw, batallonJugador.getX(), batallonJugador.getY());
            dibujarMiraCursor(gw);
        }

        dibujarEfectos(gw);
        gw.dispose();

        dibujarHudDuelo(g);

        if (fase == FaseTurno.FIN_DUELO) dibujarOverlayFinDuelo(g);
    }

    private void dibujarHudDuelo(Graphics2D g) {
        g.setColor(new Color(18, 22, 28, 210));
        g.fillRoundRect(465, 68, 350, 44, 10, 10);
        g.setColor(new Color(95, 110, 130));
        g.drawRoundRect(465, 68, 350, 44, 10, 10);

        String turnoStr = (fase == FaseTurno.TURNO_IA) ? "TURNO: SAQUEADORES"
                : (fase == FaseTurno.PROYECTIL_EN_VUELO ? "PROYECTIL EN AIRE" : "TU TURNO (A/D paneo)");
        g.setFont(new Font("SansSerif", Font.BOLD, 12));
        g.setColor(new Color(235, 225, 175));
        g.drawString(turnoStr, 482, 85);

        double fuerzaViento = Math.abs(vientoActual) / 18.0;
        String dirStr = vientoActual >= 0 ? ">>>" : "<<<";
        g.setColor(new Color(130, 210, 255));
        g.drawString(String.format("Viento: %s %.1f m/s", dirStr, fuerzaViento), 648, 85);

        int cxViento = 640;
        g.setColor(new Color(45, 50, 58));
        g.fillRect(cxViento - 70, 94, 140, 6);
        int lenV = (int) ((vientoActual / 125.0) * 70.0);
        g.setColor(new Color(105, 200, 255));
        if (lenV >= 0) g.fillRect(cxViento, 94, lenV, 6);
        else g.fillRect(cxViento + lenV, 94, -lenV, 6);

        if (batallonEnemigo.estaVivo() && batallonEnemigo.getX() - camaraX > 1250) {
            g.setColor(new Color(235, 95, 85, 220));
            g.fillRoundRect(1080, 72, 180, 30, 8, 8);
            g.setColor(Color.WHITE);
            g.setFont(new Font("SansSerif", Font.BOLD, 12));
            g.drawString("Saqueadores (" + batallonEnemigo.getVida() + " HP) ->", 1092, 91);
        }
    }

    private void dibujarOverlayFinDuelo(Graphics2D g) {
        g.setColor(new Color(10, 10, 14, 185));
        g.fillRect(0, 0, ConstantesJuego.ANCHO_VIRTUAL, ConstantesJuego.ALTO_VIRTUAL);
        boolean victoria = batallonJugador.estaVivo();
        g.setColor(victoria ? new Color(105, 235, 140) : new Color(240, 75, 75));
        g.setFont(new Font("SansSerif", Font.BOLD, 34));
        int w = g.getFontMetrics().stringWidth(ganadorTexto);
        g.drawString(ganadorTexto, 640 - w / 2, 275);

        g.setColor(new Color(55, 130, 75));
        g.fillRoundRect(510, 325, 260, 48, 12, 12);
        g.setColor(Color.WHITE);
        g.setFont(new Font("SansSerif", Font.BOLD, 17));
        g.drawString("NUEVO DUELO [ENTER]", 544, 355);
    }

    @Override
    public void alPresionarRaton(double xVirtual, double yVirtual) {
        if (fase == FaseTurno.FIN_DUELO) {
            if (xVirtual >= 510 && xVirtual <= 770 && yVirtual >= 325 && yVirtual <= 373) {
                GestorSonido.reproducirClickMenu();
                iniciarModo();
            }
            return;
        }
        if (fase != FaseTurno.TURNO_JUGADOR) return;
        camaraObjetivoX = 0;
        arrastrando = true;
        dragStartX = xVirtual + camaraX;
        dragStartY = yVirtual;
        dragActualX = dragStartX;
        dragActualY = yVirtual;
    }

    @Override
    public void alArrastrarRaton(double xVirtual, double yVirtual) {
        cursorVirtualX = xVirtual;
        cursorVirtualY = yVirtual;
        if (!arrastrando) return;
        dragActualX = xVirtual + camaraX;
        dragActualY = yVirtual;
    }

    @Override
    public void alSoltarRaton(double xVirtual, double yVirtual) {
        if (!arrastrando || fase != FaseTurno.TURNO_JUGADOR) return;
        arrastrando = false;
        double[] vec = calcularVectorDisparo(8, 82);
        ejecutarDisparoJugador(vec[0], vec[1]);
    }

    @Override
    public void alPresionarTecla(int keyCode, boolean shiftDown) {
        if (fase == FaseTurno.FIN_DUELO) {
            if (keyCode == KeyEvent.VK_ENTER) iniciarModo();
            return;
        }
        if (keyCode == KeyEvent.VK_A || keyCode == KeyEvent.VK_LEFT) paneoManualIzq = true;
        if (keyCode == KeyEvent.VK_D || keyCode == KeyEvent.VK_RIGHT) paneoManualDer = true;

        if (fase != FaseTurno.TURNO_JUGADOR) return;
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
    public void alSoltarTecla(int keyCode, boolean shiftDown) {
        if (keyCode == KeyEvent.VK_A || keyCode == KeyEvent.VK_LEFT) paneoManualIzq = false;
        if (keyCode == KeyEvent.VK_D || keyCode == KeyEvent.VK_RIGHT) paneoManualDer = false;
        super.alSoltarTecla(keyCode, shiftDown);
    }

    @Override
    public void equiparArmaDesdeHud(int indice) {
        if (batallonJugador != null) {
            batallonJugador.setArmaActual(inventario.getArma(indice));
            GestorSonido.reproducirClickMenu();
        }
    }

    @Override
    public void usarSuministroDesdeHud(TipoSuministro tipo) {
        if (fase != FaseTurno.TURNO_JUGADOR) return;
        if (!inventario.usarSuministro(tipo)) {
            textos.add(new TextoFlotante(batallonJugador.getX() + 60, batallonJugador.getY() - 140,
                    "Sin " + tipo.nombreLegible, new Color(200, 200, 200), 14));
            return;
        }
        GestorSonido.reproducirSuministro();
        if (tipo == TipoSuministro.BOTIQUIN) {
            batallonJugador.curar(55);
            textos.add(new TextoFlotante(batallonJugador.getX() + 40, batallonJugador.getY() - 145,
                    "+55 HP AL BATALLON", new Color(110, 235, 130), 17));
        } else if (tipo == TipoSuministro.CAJA_MUNICION) {
            inventario.recargarTodasLasArmas();
            textos.add(new TextoFlotante(batallonJugador.getX() + 40, batallonJugador.getY() - 145,
                    "+MUNICION DEL BATALLON", new Color(255, 210, 80), 16));
        } else {
            batallonJugador.curar(35);
            textos.add(new TextoFlotante(batallonJugador.getX() + 40, batallonJugador.getY() - 145,
                    "+35 HP RACION", new Color(110, 225, 165), 16));
        }
    }

    public Batallon getBatallonJugador() { return batallonJugador; }
}
