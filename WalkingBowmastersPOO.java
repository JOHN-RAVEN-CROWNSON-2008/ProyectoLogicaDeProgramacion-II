import armas.Arma;
import audio.GestorSonido;
import escenario.EscenarioApocaliptico;
import inventario.Inventario;
import inventario.TipoSuministro;
import modos.*;
import util.ConstantesJuego;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import java.awt.geom.Point2D;
import java.util.List;
import java.util.Random;

/**
 * ============================================================================
 * THE WALKING BOWMASTERS - EDICION POO MODULAR (LOGICA DE PROGRAMACION II)
 * ============================================================================
 * Motor principal Swing / Graphics2D (60 FPS) con navegacion por cursor,
 * efectos de sonido procedurales, disparo rapido con tecla X (5% y 100%)
 * y acceso directo a los 3 modos de juego.
 */
public class WalkingBowmastersPOO extends JPanel implements ActionListener {

    private enum EstadoPantalla {
        MENU_PRINCIPAL,
        JUGANDO_MODO_1,
        JUGANDO_MODO_2,
        JUGANDO_MODO_3
    }

    private EstadoPantalla estado = EstadoPantalla.MENU_PRINCIPAL;
    private final Inventario inventarioCompartido = new Inventario();
    private final EscenarioApocaliptico escenario = new EscenarioApocaliptico();
    private final ModoSupervivenciaHordas modoHordas;
    private final ModoDueloBatallones modoDuelo;
    private final ModoArmeriaCampoTiro modoArmeria;
    private BaseModoJuego modoActivo = null;

    private long ultimoNano = System.nanoTime();
    private final Random rng = new Random();

    // Estado de cursor para seleccion visual en menu y barra de navegacion
    private double cursorX = -1;
    private double cursorY = -1;
    private int opcionMenuSeleccionada = 0; // 0, 1, 2
    private int ultimoHoverMenu = -1;

    // Botones del Menu Principal
    private final Rectangle btnMenuModo1 = new Rectangle(380, 248, 520, 74);
    private final Rectangle btnMenuModo2 = new Rectangle(380, 336, 520, 74);
    private final Rectangle btnMenuModo3 = new Rectangle(380, 424, 520, 74);
    private final Rectangle btnMenuSonido = new Rectangle(1065, 22, 185, 38);

    // Barra superior de navegabilidad persistente
    private final Rectangle navMenu = new Rectangle(16, 11, 104, 36);
    private final Rectangle navModo1 = new Rectangle(130, 11, 152, 36);
    private final Rectangle navModo2 = new Rectangle(290, 11, 156, 36);
    private final Rectangle navModo3 = new Rectangle(454, 11, 152, 36);
    private final Rectangle navPot5 = new Rectangle(690, 11, 74, 36);
    private final Rectangle navPot100 = new Rectangle(770, 11, 84, 36);
    private final Rectangle navSonido = new Rectangle(872, 11, 116, 36);

    public WalkingBowmastersPOO() {
        setPreferredSize(new Dimension(ConstantesJuego.ANCHO_VIRTUAL, ConstantesJuego.ALTO_VIRTUAL));
        setBackground(Color.BLACK);
        setFocusable(true);
        setDoubleBuffered(true);

        modoHordas = new ModoSupervivenciaHordas(inventarioCompartido, escenario);
        modoDuelo = new ModoDueloBatallones(inventarioCompartido, escenario);
        modoArmeria = new ModoArmeriaCampoTiro(inventarioCompartido, escenario);

        configurarEntradas();
        Timer loop = new Timer(16, this);
        loop.start();
    }

    private Point2D.Double mapearAMundoVirtual(MouseEvent e) {
        int w = Math.max(1, getWidth());
        int h = Math.max(1, getHeight());
        double escala = Math.min((double) w / ConstantesJuego.ANCHO_VIRTUAL,
                (double) h / ConstantesJuego.ALTO_VIRTUAL);
        double offX = (w - ConstantesJuego.ANCHO_VIRTUAL * escala) / 2.0;
        double offY = (h - ConstantesJuego.ALTO_VIRTUAL * escala) / 2.0;
        double vx = (e.getX() - offX) / escala;
        double vy = (e.getY() - offY) / escala;
        return new Point2D.Double(vx, vy);
    }

    private void configurarEntradas() {
        MouseAdapter ma = new MouseAdapter() {
            @Override
            public void mouseMoved(MouseEvent e) {
                Point2D.Double pt = mapearAMundoVirtual(e);
                cursorX = pt.x;
                cursorY = pt.y;

                if (estado == EstadoPantalla.MENU_PRINCIPAL) {
                    int hover = detectarHoverMenu(pt.x, pt.y);
                    if (hover != -1 && hover != ultimoHoverMenu) {
                        opcionMenuSeleccionada = hover;
                        GestorSonido.reproducirHoverMenu();
                    }
                    ultimoHoverMenu = hover;
                    boolean mano = (hover != -1) || btnMenuSonido.contains(pt);
                    setCursor(Cursor.getPredefinedCursor(mano ? Cursor.HAND_CURSOR : Cursor.DEFAULT_CURSOR));
                } else if (modoActivo != null) {
                    modoActivo.alMoverRaton(pt.x, pt.y);
                    boolean sobreNav = navMenu.contains(pt) || navModo1.contains(pt) || navModo2.contains(pt)
                            || navModo3.contains(pt) || navPot5.contains(pt) || navPot100.contains(pt)
                            || navSonido.contains(pt) || pt.y >= 632;
                    setCursor(Cursor.getPredefinedCursor(sobreNav ? Cursor.HAND_CURSOR : Cursor.CROSSHAIR_CURSOR));
                }
            }

            @Override
            public void mousePressed(MouseEvent e) {
                requestFocusInWindow();
                Point2D.Double pt = mapearAMundoVirtual(e);
                cursorX = pt.x;
                cursorY = pt.y;

                if (estado == EstadoPantalla.MENU_PRINCIPAL) {
                    if (btnMenuModo1.contains(pt)) {
                        GestorSonido.reproducirClickMenu();
                        iniciarModo1();
                    } else if (btnMenuModo2.contains(pt)) {
                        GestorSonido.reproducirClickMenu();
                        iniciarModo2();
                    } else if (btnMenuModo3.contains(pt)) {
                        GestorSonido.reproducirClickMenu();
                        iniciarModo3();
                    } else if (btnMenuSonido.contains(pt)) {
                        GestorSonido.alternarSonido();
                    }
                    return;
                }

                if (manejarClicBarraSuperior(pt.x, pt.y)) return;
                if (manejarClicHudInferior(pt.x, pt.y)) return;
                if (modoActivo != null) {
                    modoActivo.alPresionarRaton(pt.x, pt.y);
                }
            }

            @Override
            public void mouseDragged(MouseEvent e) {
                Point2D.Double pt = mapearAMundoVirtual(e);
                cursorX = pt.x;
                cursorY = pt.y;
                if (modoActivo != null) {
                    modoActivo.alArrastrarRaton(pt.x, pt.y);
                }
            }

            @Override
            public void mouseReleased(MouseEvent e) {
                if (modoActivo != null) {
                    Point2D.Double pt = mapearAMundoVirtual(e);
                    modoActivo.alSoltarRaton(pt.x, pt.y);
                }
            }
        };
        addMouseListener(ma);
        addMouseMotionListener(ma);

        addKeyListener(new KeyAdapter() {
            @Override
            public void keyPressed(KeyEvent e) {
                int k = e.getKeyCode();
                if (k == KeyEvent.VK_M) {
                    GestorSonido.alternarSonido();
                    return;
                }
                if (k == KeyEvent.VK_F1) {
                    GestorSonido.reproducirClickMenu();
                    iniciarModo1();
                    return;
                }
                if (k == KeyEvent.VK_F2) {
                    GestorSonido.reproducirClickMenu();
                    iniciarModo2();
                    return;
                }
                if (k == KeyEvent.VK_F3) {
                    GestorSonido.reproducirClickMenu();
                    iniciarModo3();
                    return;
                }

                if (estado == EstadoPantalla.MENU_PRINCIPAL) {
                    if (k == KeyEvent.VK_1) {
                        GestorSonido.reproducirClickMenu();
                        iniciarModo1();
                    } else if (k == KeyEvent.VK_2) {
                        GestorSonido.reproducirClickMenu();
                        iniciarModo2();
                    } else if (k == KeyEvent.VK_3) {
                        GestorSonido.reproducirClickMenu();
                        iniciarModo3();
                    } else if (k == KeyEvent.VK_UP || k == KeyEvent.VK_W) {
                        opcionMenuSeleccionada = (opcionMenuSeleccionada + 2) % 3;
                        GestorSonido.reproducirHoverMenu();
                    } else if (k == KeyEvent.VK_DOWN || k == KeyEvent.VK_S) {
                        opcionMenuSeleccionada = (opcionMenuSeleccionada + 1) % 3;
                        GestorSonido.reproducirHoverMenu();
                    } else if (k == KeyEvent.VK_ENTER || k == KeyEvent.VK_SPACE) {
                        GestorSonido.reproducirClickMenu();
                        if (opcionMenuSeleccionada == 0) iniciarModo1();
                        else if (opcionMenuSeleccionada == 1) iniciarModo2();
                        else iniciarModo3();
                    }
                } else if (modoActivo != null) {
                    if (k == KeyEvent.VK_ESCAPE) {
                        GestorSonido.reproducirClickMenu();
                        volverAlMenu();
                        return;
                    }
                    modoActivo.alPresionarTecla(k, e.isShiftDown());
                }
            }

            @Override
            public void keyReleased(KeyEvent e) {
                if (modoActivo != null) {
                    modoActivo.alSoltarTecla(e.getKeyCode(), e.isShiftDown());
                }
            }
        });
    }

    private int detectarHoverMenu(double x, double y) {
        if (btnMenuModo1.contains(x, y)) return 0;
        if (btnMenuModo2.contains(x, y)) return 1;
        if (btnMenuModo3.contains(x, y)) return 2;
        return -1;
    }

    private void volverAlMenu() {
        estado = EstadoPantalla.MENU_PRINCIPAL;
        modoActivo = null;
        setCursor(Cursor.getDefaultCursor());
    }

    private void iniciarModo1() {
        sincronizarPresetX(modoHordas);
        modoActivo = modoHordas;
        modoHordas.iniciarModo();
        estado = EstadoPantalla.JUGANDO_MODO_1;
        setCursor(Cursor.getPredefinedCursor(Cursor.CROSSHAIR_CURSOR));
    }

    private void iniciarModo2() {
        sincronizarPresetX(modoDuelo);
        modoActivo = modoDuelo;
        modoDuelo.iniciarModo();
        estado = EstadoPantalla.JUGANDO_MODO_2;
        setCursor(Cursor.getPredefinedCursor(Cursor.CROSSHAIR_CURSOR));
    }

    private void iniciarModo3() {
        sincronizarPresetX(modoArmeria);
        modoActivo = modoArmeria;
        modoArmeria.iniciarModo();
        estado = EstadoPantalla.JUGANDO_MODO_3;
        setCursor(Cursor.getPredefinedCursor(Cursor.CROSSHAIR_CURSOR));
    }

    private void sincronizarPresetX(BaseModoJuego destino) {
        if (modoActivo != null && destino != null) {
            boolean al100 = modoActivo.isPotenciaXAl100();
            if (destino.isPotenciaXAl100() != al100) {
                destino.setPotenciaXAl100(al100);
            }
        }
    }

    private boolean manejarClicBarraSuperior(double vx, double vy) {
        if (vy > 58) return false;
        if (navMenu.contains(vx, vy)) {
            GestorSonido.reproducirClickMenu();
            volverAlMenu();
            return true;
        }
        if (navModo1.contains(vx, vy)) {
            GestorSonido.reproducirClickMenu();
            iniciarModo1();
            return true;
        }
        if (navModo2.contains(vx, vy)) {
            GestorSonido.reproducirClickMenu();
            iniciarModo2();
            return true;
        }
        if (navModo3.contains(vx, vy)) {
            GestorSonido.reproducirClickMenu();
            iniciarModo3();
            return true;
        }
        if (navPot5.contains(vx, vy) && modoActivo != null) {
            modoActivo.setPotenciaXAl100(false);
            return true;
        }
        if (navPot100.contains(vx, vy) && modoActivo != null) {
            modoActivo.setPotenciaXAl100(true);
            return true;
        }
        if (navSonido.contains(vx, vy)) {
            GestorSonido.alternarSonido();
            return true;
        }
        return false;
    }

    private boolean manejarClicHudInferior(double vx, double vy) {
        if (vy < 626 || vy > 712 || modoActivo == null) return false;
        for (int i = 0; i < 4; i++) {
            int bx = 24 + i * 200;
            if (vx >= bx && vx <= bx + 188) {
                modoActivo.equiparArmaDesdeHud(i);
                return true;
            }
        }
        TipoSuministro[] tipos = {TipoSuministro.BOTIQUIN, TipoSuministro.CAJA_MUNICION, TipoSuministro.RACION};
        for (int i = 0; i < 3; i++) {
            int sx = 845 + i * 140;
            if (vx >= sx && vx <= sx + 130) {
                modoActivo.usarSuministroDesdeHud(tipos[i]);
                return true;
            }
        }
        return false;
    }

    @Override
    public void actionPerformed(ActionEvent e) {
        long ahora = System.nanoTime();
        double dt = Math.min(0.05, (ahora - ultimoNano) / 1_000_000_000.0);
        ultimoNano = ahora;

        escenario.actualizar(dt);
        if (modoActivo != null) {
            modoActivo.actualizarLogica(dt);
        }
        repaint();
    }

    @Override
    protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        Graphics2D g2 = (Graphics2D) g.create();
        g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g2.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);

        int w = getWidth();
        int h = getHeight();
        double escala = Math.min((double) w / ConstantesJuego.ANCHO_VIRTUAL,
                (double) h / ConstantesJuego.ALTO_VIRTUAL);
        double offX = (w - ConstantesJuego.ANCHO_VIRTUAL * escala) / 2.0;
        double offY = (h - ConstantesJuego.ALTO_VIRTUAL * escala) / 2.0;

        g2.translate(offX, offY);
        g2.scale(escala, escala);
        g2.clipRect(0, 0, ConstantesJuego.ANCHO_VIRTUAL, ConstantesJuego.ALTO_VIRTUAL);

        if (estado == EstadoPantalla.MENU_PRINCIPAL) {
            dibujarMenuPrincipal(g2);
        } else if (modoActivo != null) {
            double shake = modoActivo.getIntensidadShake();
            double sx = (shake > 0) ? (rng.nextDouble() * 2 - 1) * shake : 0;
            double sy = (shake > 0) ? (rng.nextDouble() * 2 - 1) * shake : 0;
            g2.translate(sx, sy);
            modoActivo.dibujarEscena(g2);
            g2.translate(-sx, -sy);
            dibujarHudGlobal(g2);
        }

        g2.dispose();
    }

    private void dibujarMenuPrincipal(Graphics2D g) {
        escenario.dibujarFondo(g, 0, ConstantesJuego.ANCHO_VIRTUAL);
        escenario.dibujarSueloMundo(g, ConstantesJuego.ANCHO_VIRTUAL);

        g.setColor(new Color(12, 12, 18, 170));
        g.fillRect(0, 0, ConstantesJuego.ANCHO_VIRTUAL, ConstantesJuego.ALTO_VIRTUAL);

        // Boton Sonido en menu
        boolean hoverSfx = btnMenuSonido.contains(cursorX, cursorY);
        g.setColor(hoverSfx ? new Color(55, 68, 88) : new Color(28, 34, 46));
        g.fillRoundRect(btnMenuSonido.x, btnMenuSonido.y, btnMenuSonido.width, btnMenuSonido.height, 10, 10);
        g.setColor(GestorSonido.isSonidoActivo() ? new Color(95, 215, 135) : new Color(220, 90, 80));
        g.drawRoundRect(btnMenuSonido.x, btnMenuSonido.y, btnMenuSonido.width, btnMenuSonido.height, 10, 10);
        g.setFont(new Font("SansSerif", Font.BOLD, 13));
        g.setColor(Color.WHITE);
        g.drawString("SONIDO [M]: " + (GestorSonido.isSonidoActivo() ? "ACTIVADO" : "SILENCIO"),
                btnMenuSonido.x + 18, btnMenuSonido.y + 24);

        // Titulo
        g.setFont(new Font("SansSerif", Font.BOLD, 54));
        String titulo = "THE WALKING BOWMASTERS";
        int tw = g.getFontMetrics().stringWidth(titulo);
        g.setColor(new Color(0, 0, 0, 210));
        g.drawString(titulo, 643 - tw / 2, 128);
        g.setColor(new Color(235, 190, 95));
        g.drawString(titulo, 640 - tw / 2, 125);

        g.setFont(new Font("SansSerif", Font.BOLD, 17));
        String sub = "Edicion Modular POO - Selecciona un modo con el cursor o teclado";
        int sw = g.getFontMetrics().stringWidth(sub);
        g.setColor(new Color(205, 215, 230));
        g.drawString(sub, 640 - sw / 2, 166);

        dibujarTarjetaMenu(g, btnMenuModo1, 0, "[1] MODO 1: SUPERVIVENCIA DE HORDAS",
                "Defensa activa en barricada, oleadas procedurales, saqueadores y Katana",
                new Color(185, 62, 52));
        dibujarTarjetaMenu(g, btnMenuModo2, 1, "[2] MODO 2: DUELO 1v1 DE BATALLONES",
                "Composicion fuerte (Batallon *-- Escuadron), viento, camara dinamica e IA",
                new Color(54, 132, 178));
        dibujarTarjetaMenu(g, btnMenuModo3, 2, "[3] MODO 3: ARMERIA Y CAMPO DE TIRO",
                "Gestion del Inventario agregado, compras con botin y prueba de tiro 5% / 100%",
                new Color(75, 148, 92));

        // Leyenda inferior
        g.setColor(new Color(20, 22, 28, 215));
        g.fillRoundRect(205, 535, 870, 118, 12, 12);
        g.setColor(new Color(95, 105, 125));
        g.drawRoundRect(205, 535, 870, 118, 12, 12);
        g.setFont(new Font("SansSerif", Font.BOLD, 14));
        g.setColor(new Color(240, 200, 105));
        g.drawString("CONTROLES Y NAVEGACION MEJORADA:", 230, 562);
        g.setFont(new Font("SansSerif", Font.PLAIN, 13));
        g.setColor(new Color(225, 228, 235));
        g.drawString("\u2022 Menu con Cursor: Pasa el raton sobre cualquier modo y haz clic (o usa Flechas + ENTER / teclas 1, 2, 3).", 230, 586);
        g.drawString("\u2022 Disparo con Tecla [X]: Apunta con el cursor y pulsa [X] al 5% o 100% ([C] alterna 5%/100%, mantener [X] carga 5%->100%).", 230, 610);
        g.drawString("\u2022 Disparo Bowmasters: Arrastra y suelta el raton | [1-4]: Armas | [Q/E/R]: Suministros | [F1/F2/F3]: Cambiar de modo.", 230, 634);
    }

    private void dibujarTarjetaMenu(Graphics2D g, Rectangle r, int idx, String titulo, String desc, Color acento) {
        boolean seleccionado = (opcionMenuSeleccionada == idx);
        boolean hover = r.contains(cursorX, cursorY);

        int dx = (seleccionado || hover) ? -6 : 0;
        g.setColor((seleccionado || hover) ? new Color(38, 44, 58, 248) : new Color(22, 26, 34, 232));
        g.fillRoundRect(r.x + dx, r.y, r.width - dx * 2, r.height, 14, 14);

        g.setColor(acento);
        g.fillRoundRect(r.x + dx, r.y, 14, r.height, 8, 8);

        g.setColor((seleccionado || hover) ? new Color(255, 215, 105) : acento);
        g.setStroke(new BasicStroke((seleccionado || hover) ? 2.8f : 1.5f));
        g.drawRoundRect(r.x + dx, r.y, r.width - dx * 2, r.height, 14, 14);
        g.setStroke(new BasicStroke(1f));

        g.setFont(new Font("SansSerif", Font.BOLD, 19));
        g.setColor(Color.WHITE);
        String prefijo = (seleccionado || hover) ? "\u25ba " : "";
        g.drawString(prefijo + titulo, r.x + dx + 28, r.y + 32);

        g.setFont(new Font("SansSerif", Font.PLAIN, 13));
        g.setColor(new Color(195, 204, 218));
        g.drawString(desc, r.x + dx + 28, r.y + 55);

        if (seleccionado || hover) {
            g.setFont(new Font("SansSerif", Font.BOLD, 12));
            g.setColor(new Color(255, 220, 110));
            g.drawString("ENTRAR >", r.x + r.width - dx - 84, r.y + 32);
        }
    }

    private void dibujarHudGlobal(Graphics2D g) {
        // Barra superior persistente de navegabilidad
        g.setColor(new Color(12, 14, 20, 218));
        g.fillRect(0, 0, ConstantesJuego.ANCHO_VIRTUAL, 58);
        g.setColor(new Color(65, 72, 86));
        g.drawLine(0, 58, ConstantesJuego.ANCHO_VIRTUAL, 58);

        dibujarBotonNav(g, navMenu, "MENU [ESC]", false, new Color(145, 55, 50));
        dibujarBotonNav(g, navModo1, "MODO 1: HORDAS", estado == EstadoPantalla.JUGANDO_MODO_1, new Color(175, 65, 55));
        dibujarBotonNav(g, navModo2, "MODO 2: DUELO 1v1", estado == EstadoPantalla.JUGANDO_MODO_2, new Color(54, 125, 170));
        dibujarBotonNav(g, navModo3, "MODO 3: ARMERIA", estado == EstadoPantalla.JUGANDO_MODO_3, new Color(75, 145, 92));

        // Selector visual de Tecla X: 5% vs 100%
        g.setFont(new Font("SansSerif", Font.BOLD, 11));
        g.setColor(new Color(180, 215, 240));
        g.drawString("TECLA [X]:", 624, 33);

        boolean al100 = (modoActivo != null) && modoActivo.isPotenciaXAl100();
        dibujarBotonNav(g, navPot5, "X: 5%", !al100, new Color(65, 150, 175));
        dibujarBotonNav(g, navPot100, "X: 100%", al100, new Color(215, 115, 45));

        dibujarBotonNav(g, navSonido,
                "SFX: " + (GestorSonido.isSonidoActivo() ? "ON" : "OFF"),
                GestorSonido.isSonidoActivo(), new Color(72, 125, 95));

        g.setFont(new Font("SansSerif", Font.BOLD, 14));
        g.setColor(new Color(135, 225, 160));
        g.drawString("Botin: " + inventarioCompartido.getRecursosAcumulados(), 1090, 35);

        // Barra inferior (Armas y Suministros clicables)
        g.setColor(new Color(12, 14, 20, 228));
        g.fillRect(0, 622, ConstantesJuego.ANCHO_VIRTUAL, 98);
        g.setColor(new Color(65, 72, 86));
        g.drawLine(0, 622, ConstantesJuego.ANCHO_VIRTUAL, 622);

        Arma armada = null;
        if (modoActivo == modoHordas) armada = modoHordas.getJugador().getArmaActual();
        else if (modoActivo == modoDuelo) armada = modoDuelo.getBatallonJugador().getArmaActual();
        else if (modoActivo == modoArmeria) armada = modoArmeria.getTirador().getArmaActual();

        List<Arma> armas = inventarioCompartido.getArmas();
        for (int i = 0; i < armas.size(); i++) {
            Arma a = armas.get(i);
            boolean sel = (a == armada);
            int bx = 24 + i * 200;
            int by = 634;
            boolean hover = cursorX >= bx && cursorX <= bx + 188 && cursorY >= by && cursorY <= by + 72;

            g.setColor(sel ? new Color(46, 58, 76) : (hover ? new Color(34, 40, 52) : new Color(24, 28, 36)));
            g.fillRoundRect(bx, by, 188, 72, 10, 10);
            g.setColor(sel ? a.getColorAcento() : (hover ? Color.LIGHT_GRAY : new Color(75, 82, 95)));
            g.setStroke(new BasicStroke(sel ? 2.5f : 1f));
            g.drawRoundRect(bx, by, 188, 72, 10, 10);
            g.setStroke(new BasicStroke(1f));

            Graphics2D gi = (Graphics2D) g.create();
            gi.translate(bx + 26, by + 44);
            a.dibujarArmaEnMano(gi, 0.9);
            gi.dispose();

            g.setFont(new Font("SansSerif", Font.BOLD, 12));
            g.setColor(Color.WHITE);
            g.drawString("[" + (i + 1) + "] " + a.getNombre(), bx + 10, by + 18);

            g.setFont(new Font("SansSerif", Font.BOLD, 12));
            g.setColor(a.getMunicion() == 0 ? new Color(255, 95, 95) : new Color(210, 220, 235));
            String m = a.esInfinita() ? "Infinita" : ("Ammo: " + a.getMunicion());
            g.drawString(m, bx + 84, by + 56);
        }

        TipoSuministro[] tipos = {TipoSuministro.BOTIQUIN, TipoSuministro.CAJA_MUNICION, TipoSuministro.RACION};
        String[] teclas = {"[Q] Curar", "[E] Municion", "[R] Racion"};
        for (int i = 0; i < 3; i++) {
            int sx = 845 + i * 140;
            int sy = 634;
            int cant = inventarioCompartido.getCantidadSuministro(tipos[i]);
            boolean hover = cursorX >= sx && cursorX <= sx + 130 && cursorY >= sy && cursorY <= sy + 72;
            g.setColor(hover ? new Color(34, 40, 50) : new Color(24, 28, 36));
            g.fillRoundRect(sx, sy, 130, 72, 10, 10);
            g.setColor(cant > 0 ? tipos[i].color : new Color(65, 70, 80));
            g.drawRoundRect(sx, sy, 130, 72, 10, 10);

            g.setFont(new Font("SansSerif", Font.BOLD, 13));
            g.setColor(Color.WHITE);
            g.drawString(teclas[i], sx + 12, sy + 24);
            g.setFont(new Font("SansSerif", Font.BOLD, 16));
            g.setColor(cant > 0 ? tipos[i].color : new Color(130, 135, 145));
            g.drawString("x" + cant, sx + 14, sy + 52);
        }
    }

    private void dibujarBotonNav(Graphics2D g, Rectangle r, String texto, boolean activo, Color acento) {
        boolean hover = r.contains(cursorX, cursorY);
        Color fondo = activo ? acento : (hover ? new Color(46, 54, 68) : new Color(26, 30, 40));
        g.setColor(fondo);
        g.fillRoundRect(r.x, r.y, r.width, r.height, 8, 8);
        g.setColor(activo ? Color.WHITE : (hover ? acento.brighter() : new Color(80, 90, 108)));
        g.setStroke(new BasicStroke(activo ? 2f : 1f));
        g.drawRoundRect(r.x, r.y, r.width, r.height, 8, 8);
        g.setStroke(new BasicStroke(1f));

        g.setFont(new Font("SansSerif", Font.BOLD, 12));
        g.setColor(Color.WHITE);
        FontMetrics fm = g.getFontMetrics();
        int tx = r.x + (r.width - fm.stringWidth(texto)) / 2;
        int ty = r.y + (r.height + fm.getAscent()) / 2 - 2;
        g.drawString(texto, tx, ty);
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(new Runnable() {
            @Override
            public void run() {
                JFrame frame = new JFrame("The Walking Bowmasters - POO Modular Java 2D");
                frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
                WalkingBowmastersPOO juego = new WalkingBowmastersPOO();
                frame.setContentPane(juego);
                frame.pack();
                frame.setLocationRelativeTo(null);
                frame.setVisible(true);
                juego.requestFocusInWindow();
            }
        });
    }
}
