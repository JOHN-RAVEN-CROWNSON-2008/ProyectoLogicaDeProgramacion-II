package modos;

import armas.EspadaKatana;
import audio.GestorSonido;
import efectos.TextoFlotante;
import entidades.*;
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
 * [POO - ABSTRACCION (Implementa ModoJuego via BaseModoJuego)]
 * MODO 1: Supervivencia de Hordas Aleatorias (Defensa Activa).
 */
public class ModoSupervivenciaHordas extends BaseModoJuego {
    private Superviviente jugador;
    private final List<Zombie> zombies = new ArrayList<Zombie>();
    private final List<SaqueadorRival> saqueadores = new ArrayList<SaqueadorRival>();
    private final List<Suministro> drops = new ArrayList<Suministro>();

    private int oleada = 1;
    private int zombiesPorGenerar = 0;
    private int zombiesEliminados = 0;
    private double timerSpawn = 0.8;
    private double pausaEntreOleadas = 0.0;
    private int vidaBarricada = 200;
    private final int vidaBarricadaMax = 200;
    private boolean juegoTerminado = false;

    public ModoSupervivenciaHordas(Inventario inventario, EscenarioApocaliptico escenario) {
        super(inventario, escenario);
    }

    @Override
    public String getNombreModo() {
        return "MODO 1: HORDAS ZOMBIE";
    }

    @Override
    public void iniciarModo() {
        camaraX = 0;
        proyectiles.clear();
        particulas.clear();
        ondas.clear();
        textos.clear();
        zombies.clear();
        saqueadores.clear();
        drops.clear();
        oleada = 1;
        zombiesEliminados = 0;
        vidaBarricada = vidaBarricadaMax;
        juegoTerminado = false;
        arrastrando = false;
        cargandoTeclaX = false;

        jugador = new Superviviente("Rick (Superviviente)", 140, ConstantesJuego.Y_SUELO, inventario);
        iniciarOleada(1);
    }

    private void iniciarOleada(int num) {
        this.oleada = num;
        this.zombiesPorGenerar = 4 + num * 2;
        this.timerSpawn = 0.9;
        if (num >= 2 && num % 2 == 0) {
            double posTiro = 860 + rng.nextDouble() * 190;
            saqueadores.add(new SaqueadorRival("Saqueador Hostil", 1320, ConstantesJuego.Y_SUELO, posTiro));
        }
        textos.add(new TextoFlotante(640, 210, "OLEADA " + oleada + " INICIADA", new Color(255, 195, 80), 26));
    }

    private void generarZombieAleatorio() {
        double sx = 1315 + rng.nextDouble() * 45;
        double sy = ConstantesJuego.Y_SUELO;
        int bonus = (oleada - 1) * 12;
        double roll = rng.nextDouble();
        Zombie z;
        if (oleada >= 2 && roll < 0.24) {
            z = new ZombieBlindado(sx, sy, bonus * 2);
        } else if (roll < 0.54) {
            z = new ZombieCorredor(sx, sy, bonus);
        } else {
            z = new ZombieCaminante(sx, sy, 0.92 + rng.nextDouble() * 0.20, bonus);
        }
        z.setObjetivoX(218);
        zombies.add(z);
    }

    @Override
    public void actualizarLogica(double dt) {
        actualizarEfectos(dt);
        if (juegoTerminado) return;

        if (!arrastrando && cursorEnArena) {
            double xBoca = jugador.getX() + 24;
            double yBoca = jugador.getY() - 56;
            jugador.setAnguloApuntado(calcularAnguloHaciaCursor(xBoca, yBoca, -18, 84));
        }
        jugador.actualizar(dt);

        if (zombiesPorGenerar > 0) {
            timerSpawn -= dt;
            if (timerSpawn <= 0) {
                generarZombieAleatorio();
                zombiesPorGenerar--;
                timerSpawn = Math.max(0.75, 2.3 - oleada * 0.16) + rng.nextDouble() * 0.7;
            }
        } else if (zombies.isEmpty() && saqueadores.isEmpty()) {
            if (pausaEntreOleadas <= 0) {
                pausaEntreOleadas = 2.6;
                GestorSonido.reproducirSuministro();
                textos.add(new TextoFlotante(640, 190, "\u00a1OLEADA SUPERADA!", new Color(110, 235, 130), 24));
                vidaBarricada = Math.min(vidaBarricadaMax, vidaBarricada + 35);
            } else {
                pausaEntreOleadas -= dt;
                if (pausaEntreOleadas <= 0) {
                    iniciarOleada(oleada + 1);
                }
            }
        }

        Iterator<SaqueadorRival> isaq = saqueadores.iterator();
        while (isaq.hasNext()) {
            SaqueadorRival s = isaq.next();
            s.actualizar(dt);
            Proyectil disparoEnemigo = s.recogerDisparoPendiente();
            if (disparoEnemigo != null) {
                GestorSonido.reproducirDisparoRevolver();
                proyectiles.add(disparoEnemigo);
            }
            if (!s.estaVivo()) isaq.remove();
        }

        Iterator<Suministro> idrop = drops.iterator();
        while (idrop.hasNext()) {
            Suministro s = idrop.next();
            s.actualizarDrop(dt);
            if (s.getTiempoFlotando() > 3.2 || !s.isEnSuelo()) {
                recolectarSuministro(s);
                idrop.remove();
            }
        }

        Iterator<Zombie> iz = zombies.iterator();
        while (iz.hasNext()) {
            Zombie z = iz.next();
            z.setObjetivoX(vidaBarricada > 0 ? 222 : 172);
            z.actualizar(dt);
            if (z.listoParaGolpear(dt)) {
                GestorSonido.reproducirImpacto();
                if (vidaBarricada > 0) {
                    vidaBarricada = Math.max(0, vidaBarricada - z.getDanoAtaque());
                    generarImpacto(212, ConstantesJuego.Y_SUELO - 35, new Color(175, 140, 95), 7);
                    textos.add(new TextoFlotante(212, ConstantesJuego.Y_SUELO - 80,
                            "-" + z.getDanoAtaque() + " Barricada", new Color(255, 150, 75), 14));
                } else {
                    jugador.recibirDano(z.getDanoAtaque());
                    intensidadShake = 8.0;
                    generarImpacto(jugador.getX(), jugador.getY() - 50, new Color(220, 40, 40), 10);
                    textos.add(new TextoFlotante(jugador.getX(), jugador.getY() - 105,
                            "-" + z.getDanoAtaque() + " HP", new Color(255, 70, 70), 17));
                    if (!jugador.estaVivo()) {
                        juegoTerminado = true;
                        GestorSonido.reproducirDerrota();
                        textos.add(new TextoFlotante(640, 220, "\u00a1HAS CAIDO ANTE LA HORDA!", new Color(255, 65, 65), 28));
                    }
                }
            }
            if (!z.estaVivo()) iz.remove();
        }

        Iterator<Proyectil> ipr = proyectiles.iterator();
        while (ipr.hasNext()) {
            Proyectil p = ipr.next();
            p.actualizarConViento(dt, 0.0);
            if (!p.estaYaLanzado()) continue;

            boolean impacto = false;
            if (p.getY() >= ConstantesJuego.Y_SUELO) {
                p.setPosicion(p.getX(), ConstantesJuego.Y_SUELO - 2);
                impacto = true;
            } else if (p.getX() > 1360 || p.getX() < -40 || p.getY() < -350) {
                ipr.remove();
                continue;
            } else if (!p.isFaccionJugador()) {
                if (vidaBarricada > 0 && Math.abs(p.getX() - 200) <= 22 && p.getY() >= ConstantesJuego.Y_SUELO - 60) {
                    impacto = true;
                    vidaBarricada = Math.max(0, vidaBarricada - p.getDano());
                    GestorSonido.reproducirImpacto();
                    generarImpacto(p.getX(), p.getY(), new Color(175, 140, 95), 8);
                    textos.add(new TextoFlotante(205, ConstantesJuego.Y_SUELO - 85,
                            "-" + p.getDano() + " Barricada", new Color(255, 150, 75), 14));
                } else if (Math.abs(p.getX() - jugador.getX()) <= 24 && p.getY() >= jugador.getY() - 95) {
                    impacto = true;
                    int danoNeto = jugador.calcularDano(p.getDano());
                    jugador.recibirDano(danoNeto);
                    intensidadShake = 7.0;
                    GestorSonido.reproducirImpacto();
                    generarImpacto(p.getX(), p.getY(), new Color(210, 35, 35), 10);
                    textos.add(new TextoFlotante(jugador.getX(), jugador.getY() - 105,
                            "-" + danoNeto + " HP", new Color(255, 70, 70), 17));
                    if (!jugador.estaVivo()) {
                        juegoTerminado = true;
                        GestorSonido.reproducirDerrota();
                        textos.add(new TextoFlotante(640, 220, "\u00a1HAS CAIDO ANTE LA HORDA!", new Color(255, 65, 65), 28));
                    }
                }
            } else {
                for (Zombie z : zombies) {
                    if (!z.estaVivo()) continue;
                    double zx = z.getX();
                    double zy = z.getY();
                    double zw = z.getAnchoVisual() * 0.65;
                    double zh = z.getAlturaVisual();
                    if (Math.abs(p.getX() - zx) <= zw && p.getY() >= zy - zh && p.getY() <= zy) {
                        impacto = true;
                        if (p.getTipo() != TipoProyectil.GRANADA) {
                            boolean headshot = p.getY() < (zy - zh * 0.68);
                            double mult = headshot ? p.getMultiplicadorCritico() : 1.0;
                            int danoFinal = z.calcularDano(p.getDano(), mult, p.isIgnoraArmadura());
                            z.recibirDano(danoFinal);
                            GestorSonido.reproducirImpacto();
                            generarImpacto(p.getX(), p.getY(), new Color(185, 25, 25), headshot ? 16 : 9);
                            textos.add(new TextoFlotante(zx, zy - zh - 10,
                                    (headshot ? "\u00a1CR\u00cdTICO! -" : "-") + danoFinal + " HP",
                                    headshot ? new Color(255, 225, 70) : new Color(255, 110, 95),
                                    headshot ? 17 : 14));
                            if (!z.estaVivo()) alMorirZombie(z);
                        }
                        break;
                    }
                }
                if (!impacto) {
                    for (SaqueadorRival sr : saqueadores) {
                        if (!sr.estaVivo()) continue;
                        if (Math.abs(p.getX() - sr.getX()) <= 24 && p.getY() >= sr.getY() - 92 && p.getY() <= sr.getY()) {
                            impacto = true;
                            if (p.getTipo() != TipoProyectil.GRANADA) {
                                boolean headshot = p.getY() < (sr.getY() - 68);
                                int danoFinal = sr.calcularDano(p.getDano(), headshot ? p.getMultiplicadorCritico() : 1.0, p.isIgnoraArmadura());
                                sr.recibirDano(danoFinal);
                                GestorSonido.reproducirImpacto();
                                generarImpacto(p.getX(), p.getY(), new Color(185, 25, 25), 11);
                                textos.add(new TextoFlotante(sr.getX(), sr.getY() - 108,
                                        (headshot ? "\u00a1CR\u00cdTICO! -" : "-") + danoFinal + " HP",
                                        headshot ? new Color(255, 225, 70) : new Color(255, 110, 95), 16));
                                if (!sr.estaVivo()) {
                                    inventario.incrementarBajas();
                                    inventario.sumarPuntosRecurso(50);
                                    drops.add(new Suministro(TipoSuministro.CAJA_MUNICION, 1, sr.getX(), ConstantesJuego.Y_SUELO));
                                }
                            }
                            break;
                        }
                    }
                }
            }

            if (impacto) {
                if (p.getTipo() == TipoProyectil.GRANADA) {
                    generarExplosion(p.getX(), p.getY(), p.getRadioExplosion());
                    for (Zombie z : zombies) {
                        if (!z.estaVivo()) continue;
                        double dist = Math.hypot(z.getX() - p.getX(), (z.getY() - 40) - p.getY());
                        if (dist <= p.getRadioExplosion()) {
                            double factorDist = 1.0 - (dist / p.getRadioExplosion()) * 0.45;
                            int danoAoE = z.calcularDano((int) (p.getDano() * factorDist), 1.0, p.isIgnoraArmadura());
                            z.recibirDano(danoAoE);
                            textos.add(new TextoFlotante(z.getX(), z.getY() - 85, "-" + danoAoE + " HP",
                                    new Color(255, 165, 65), 16));
                            if (!z.estaVivo()) alMorirZombie(z);
                        }
                    }
                    for (SaqueadorRival sr : saqueadores) {
                        if (!sr.estaVivo()) continue;
                        double dist = Math.hypot(sr.getX() - p.getX(), (sr.getY() - 45) - p.getY());
                        if (dist <= p.getRadioExplosion()) {
                            double factorDist = 1.0 - (dist / p.getRadioExplosion()) * 0.45;
                            int danoAoE = sr.calcularDano((int) (p.getDano() * factorDist), 1.0, p.isIgnoraArmadura());
                            sr.recibirDano(danoAoE);
                            textos.add(new TextoFlotante(sr.getX(), sr.getY() - 108, "-" + danoAoE + " HP",
                                    new Color(255, 165, 65), 16));
                            if (!sr.estaVivo()) {
                                inventario.incrementarBajas();
                                inventario.sumarPuntosRecurso(50);
                                drops.add(new Suministro(TipoSuministro.CAJA_MUNICION, 1, sr.getX(), ConstantesJuego.Y_SUELO));
                            }
                        }
                    }
                } else if (p.getY() >= ConstantesJuego.Y_SUELO - 3) {
                    generarImpacto(p.getX(), ConstantesJuego.Y_SUELO - 2, new Color(165, 160, 145), 6);
                }
                ipr.remove();
            }
        }
    }

    private void alMorirZombie(Zombie z) {
        zombiesEliminados++;
        inventario.incrementarBajas();
        inventario.sumarPuntosRecurso(25);
        generarImpacto(z.getX(), z.getY() - 40, new Color(150, 20, 20), 18);

        if (rng.nextDouble() < 0.42) {
            double r = rng.nextDouble();
            TipoSuministro tipo = (r < 0.48) ? TipoSuministro.CAJA_MUNICION
                    : (r < 0.80 ? TipoSuministro.BOTIQUIN : TipoSuministro.RACION);
            drops.add(new Suministro(tipo, 1, z.getX(), ConstantesJuego.Y_SUELO));
        }
    }

    private void recolectarSuministro(Suministro s) {
        if (!s.isEnSuelo()) return;
        s.marcarRecogido();
        inventario.agregarSuministro(s.getTipo(), 1);
        GestorSonido.reproducirSuministro();
        textos.add(new TextoFlotante(jugador.getX(), jugador.getY() - 120,
                "+" + s.getTipo().nombreLegible, s.getTipo().color, 15));
    }

    private boolean intentarCorteKatanaCuerpoACuerpo() {
        if (!(jugador.getArmaActual() instanceof EspadaKatana)) return false;
        EspadaKatana katana = (EspadaKatana) jugador.getArmaActual();
        if (!katana.puedeCortarCuerpoACuerpo()) return false;

        boolean hayCercano = false;
        for (Zombie z : zombies) {
            if (z.estaVivo() && z.getX() - jugador.getX() <= 210) {
                hayCercano = true;
                break;
            }
        }
        if (!hayCercano) {
            for (SaqueadorRival sr : saqueadores) {
                if (sr.estaVivo() && sr.getX() - jugador.getX() <= 210) {
                    hayCercano = true;
                    break;
                }
            }
        }
        if (!hayCercano) return false;

        katana.registrarCorteCuerpoACuerpo();
        jugador.activarAnimacionKatana();
        GestorSonido.reproducirCorteKatana();
        intensidadShake = 7.0;
        for (Zombie z : zombies) {
            if (z.estaVivo() && z.getX() - jugador.getX() <= 220) {
                int danoCorte = z.calcularDano(katana.getDanoBase(), 1.65, true);
                z.recibirDano(danoCorte);
                generarImpacto(z.getX(), z.getY() - 48, new Color(165, 240, 255), 14);
                generarImpacto(z.getX(), z.getY() - 48, new Color(190, 25, 25), 10);
                textos.add(new TextoFlotante(z.getX(), z.getY() - 95,
                        "\u00a1CORTE! -" + danoCorte, new Color(135, 240, 255), 18));
                if (!z.estaVivo()) alMorirZombie(z);
            }
        }
        for (SaqueadorRival sr : saqueadores) {
            if (sr.estaVivo() && sr.getX() - jugador.getX() <= 220) {
                int danoCorte = sr.calcularDano(katana.getDanoBase(), 1.65, true);
                sr.recibirDano(danoCorte);
                generarImpacto(sr.getX(), sr.getY() - 48, new Color(165, 240, 255), 14);
                textos.add(new TextoFlotante(sr.getX(), sr.getY() - 108,
                        "\u00a1CORTE! -" + danoCorte, new Color(135, 240, 255), 18));
            }
        }
        return true;
    }

    private void ejecutarDisparo(double angulo, double potencia) {
        List<Proyectil> nuevos = jugador.disparar(angulo, potencia);
        if (nuevos.isEmpty() && jugador.getArmaActual().getMunicion() == 0) {
            textos.add(new TextoFlotante(jugador.getX(), jugador.getY() - 125,
                    "\u00a1Sin municion! Usa [E] o [4] Katana", new Color(255, 110, 90), 15));
        } else if (!nuevos.isEmpty()) {
            reproducirSonidoArma(jugador.getArmaActual());
            proyectiles.addAll(nuevos);
            generarImpacto(jugador.getX() + 26 * Math.cos(angulo),
                    jugador.getY() - 56 - 26 * Math.sin(angulo),
                    new Color(255, 220, 120), 6);
        }
    }

    @Override
    protected void dispararConTeclaX(double potencia) {
        if (juegoTerminado || jugador == null) return;
        if (intentarCorteKatanaCuerpoACuerpo()) return;
        double xBoca = jugador.getX() + 24;
        double yBoca = jugador.getY() - 56;
        double ang = calcularAnguloHaciaCursor(xBoca, yBoca, -18, 84);
        ejecutarDisparo(ang, potencia);
        textos.add(new TextoFlotante(jugador.getX() + 20, jugador.getY() - 140,
                "Disparo [X] " + (int) Math.round(potencia * 100) + "%", new Color(115, 225, 255), 13));
    }

    @Override
    public void dibujarEscena(Graphics2D g) {
        escenario.dibujarFondo(g, 0, ConstantesJuego.ANCHO_VIRTUAL);
        escenario.dibujarSueloMundo(g, ConstantesJuego.ANCHO_VIRTUAL);

        dibujarBarricada(g);

        for (Suministro s : drops) s.renderizarDrop(g);
        jugador.renderizar(g);
        for (Zombie z : zombies) z.renderizar(g);
        for (SaqueadorRival sr : saqueadores) sr.renderizar(g);
        for (Proyectil p : proyectiles) p.renderizar(g);

        if (!juegoTerminado) {
            double xBoca = jugador.getX() + 24 * Math.cos(jugador.getAnguloApuntado());
            double yBoca = (jugador.getY() - 56) - 24 * Math.sin(jugador.getAnguloApuntado());
            if (arrastrando) {
                double[] vec = calcularVectorDisparo(-18, 84);
                jugador.setAnguloApuntado(vec[0]);
                dibujarGuiaParabolica(g, xBoca, yBoca, vec[0], vec[1], jugador.getArmaActual(), 0.0, false);
            } else if (cursorEnArena) {
                double ang = calcularAnguloHaciaCursor(jugador.getX() + 24, jugador.getY() - 56, -18, 84);
                double pot = cargandoTeclaX && tiempoCargaX >= 0.18 ? potenciaCargaX : getPotenciaPresetX();
                dibujarGuiaParabolica(g, xBoca, yBoca, ang, pot, jugador.getArmaActual(), 0.0, true);
            }
            dibujarBarraCargaX(g, jugador.getX(), jugador.getY());
            dibujarMiraCursor(g);
        }

        dibujarEfectos(g);

        g.setFont(new Font("SansSerif", Font.BOLD, 13));
        g.setColor(new Color(240, 220, 170));
        g.drawString("Oleada: " + oleada + " | Enemigos: " + (zombies.size() + zombiesPorGenerar + saqueadores.size())
                + " | Bajas: " + zombiesEliminados, 24, 80);

        if (juegoTerminado) dibujarOverlayFin(g);
    }

    private void dibujarBarricada(Graphics2D g) {
        int bx = 185;
        int ys = ConstantesJuego.Y_SUELO;
        if (vidaBarricada <= 0) {
            g.setColor(new Color(75, 55, 38));
            g.fillRect(bx, ys - 10, 36, 10);
            return;
        }
        g.setColor(new Color(92, 64, 42));
        g.fillRoundRect(bx, ys - 56, 14, 56, 3, 3);
        g.fillRoundRect(bx + 16, ys - 48, 12, 48, 3, 3);
        g.setColor(new Color(125, 112, 84));
        g.fillRoundRect(bx + 10, ys - 24, 24, 12, 6, 6);
        g.fillRoundRect(bx + 12, ys - 12, 26, 12, 6, 6);
        g.setColor(new Color(175, 180, 188));
        g.drawLine(bx + 2, ys - 54, bx + 34, ys - 42);
        g.drawLine(bx + 34, ys - 52, bx + 2, ys - 38);

        double pct = ConstantesJuego.limitar((double) vidaBarricada / vidaBarricadaMax, 0.0, 1.0);
        int barX = bx - 6;
        int barY = ys - 72;
        g.setFont(new Font("SansSerif", Font.BOLD, 11));
        g.setColor(new Color(235, 235, 240));
        g.drawString("Barricada", barX - 2, barY - 5);
        g.setColor(new Color(20, 22, 26, 220));
        g.fillRoundRect(barX - 2, barY - 2, 52, 9, 4, 4);
        g.setColor(Combatiente.colorInterpoladoSalud(pct));
        g.fillRoundRect(barX, barY, (int) Math.round(48 * pct), 5, 3, 3);
    }

    private void dibujarOverlayFin(Graphics2D g) {
        g.setColor(new Color(10, 10, 14, 185));
        g.fillRect(0, 0, ConstantesJuego.ANCHO_VIRTUAL, ConstantesJuego.ALTO_VIRTUAL);
        g.setColor(new Color(235, 70, 70));
        g.setFont(new Font("SansSerif", Font.BOLD, 44));
        String t = "SUPERVIVIENTE CAIDO";
        int w = g.getFontMetrics().stringWidth(t);
        g.drawString(t, 640 - w / 2, 270);

        g.setColor(Color.WHITE);
        g.setFont(new Font("SansSerif", Font.PLAIN, 20));
        String sub = "Oleada alcanzada: " + oleada + "   |   Enemigos abatidos: " + zombiesEliminados;
        int sw = g.getFontMetrics().stringWidth(sub);
        g.drawString(sub, 640 - sw / 2, 320);

        g.setColor(new Color(55, 130, 75));
        g.fillRoundRect(510, 360, 260, 48, 12, 12);
        g.setColor(Color.WHITE);
        g.setFont(new Font("SansSerif", Font.BOLD, 17));
        g.drawString("REINTENTAR [ENTER]", 552, 390);
    }

    @Override
    public void alPresionarRaton(double xVirtual, double yVirtual) {
        if (juegoTerminado) {
            if (xVirtual >= 510 && xVirtual <= 770 && yVirtual >= 360 && yVirtual <= 408) {
                GestorSonido.reproducirClickMenu();
                iniciarModo();
            }
            return;
        }
        for (Suministro s : drops) {
            if (s.isEnSuelo() && Math.hypot(xVirtual - s.getX(), yVirtual - (s.getY() - 16)) < 32) {
                recolectarSuministro(s);
                return;
            }
        }
        if (intentarCorteKatanaCuerpoACuerpo()) return;

        arrastrando = true;
        dragStartX = xVirtual;
        dragStartY = yVirtual;
        dragActualX = xVirtual;
        dragActualY = yVirtual;
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
        if (!arrastrando || juegoTerminado) return;
        arrastrando = false;
        double[] vec = calcularVectorDisparo(-18, 84);
        ejecutarDisparo(vec[0], vec[1]);
    }

    @Override
    public void alPresionarTecla(int keyCode, boolean shiftDown) {
        if (juegoTerminado) {
            if (keyCode == KeyEvent.VK_ENTER) iniciarModo();
            return;
        }
        if (keyCode == KeyEvent.VK_1) equiparArmaDesdeHud(0);
        else if (keyCode == KeyEvent.VK_2) equiparArmaDesdeHud(1);
        else if (keyCode == KeyEvent.VK_3) equiparArmaDesdeHud(2);
        else if (keyCode == KeyEvent.VK_4) equiparArmaDesdeHud(3);
        else if (keyCode == KeyEvent.VK_SPACE) intentarCorteKatanaCuerpoACuerpo();
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
        if (jugador != null) {
            jugador.equiparArmaPorIndice(indice);
            GestorSonido.reproducirClickMenu();
        }
    }

    @Override
    public void usarSuministroDesdeHud(TipoSuministro tipo) {
        if (juegoTerminado || jugador == null) return;
        if (!inventario.usarSuministro(tipo)) {
            textos.add(new TextoFlotante(jugador.getX(), jugador.getY() - 125,
                    "Sin " + tipo.nombreLegible, new Color(200, 200, 200), 14));
            return;
        }
        GestorSonido.reproducirSuministro();
        if (tipo == TipoSuministro.BOTIQUIN) {
            jugador.curar(TipoSuministro.BOTIQUIN.valor);
            textos.add(new TextoFlotante(jugador.getX(), jugador.getY() - 125,
                    "+" + TipoSuministro.BOTIQUIN.valor + " HP", new Color(115, 235, 130), 17));
        } else if (tipo == TipoSuministro.CAJA_MUNICION) {
            inventario.recargarTodasLasArmas();
            textos.add(new TextoFlotante(jugador.getX(), jugador.getY() - 125,
                    "+MUNICION RECARGADA", new Color(255, 210, 80), 16));
        } else {
            jugador.curar(TipoSuministro.RACION.valor);
            jugador.agregarEscudoRacion(8);
            textos.add(new TextoFlotante(jugador.getX(), jugador.getY() - 125,
                    "+25 HP & RESISTENCIA", new Color(110, 225, 165), 16));
        }
    }

    public Superviviente getJugador() { return jugador; }
}
