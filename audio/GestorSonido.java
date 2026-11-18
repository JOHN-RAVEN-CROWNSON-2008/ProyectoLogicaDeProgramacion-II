package audio;

import javax.sound.sampled.*;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Gestor de efectos de sonido procedurales (PCM 16-bit 44100 Hz) mediante javax.sound.sampled.
 * No requiere archivos .wav externos y se ejecuta de forma asincrona sin bloquear los 60 FPS.
 */
public final class GestorSonido {
    private static final float SAMPLE_RATE = 44100f;
    private static final AudioFormat FORMATO = new AudioFormat(SAMPLE_RATE, 16, 1, true, false);
    private static final Map<String, byte[]> CACHE = new HashMap<String, byte[]>();
    private static final AtomicInteger VOCES_ACTIVAS = new AtomicInteger(0);
    private static final int MAX_VOCES = 10;

    private static final ExecutorService POOL = Executors.newCachedThreadPool(new ThreadFactory() {
        @Override
        public Thread newThread(Runnable r) {
            Thread t = new Thread(r, "AudioFX-Worker");
            t.setDaemon(true);
            return t;
        }
    });

    private static volatile boolean sonidoActivo = true;

    static {
        inicializarEfectos();
    }

    private GestorSonido() {
    }

    private static void inicializarEfectos() {
        CACHE.put("hover", sintetizarBarrido(680, 920, 0.040, 0.14, false, 100));
        CACHE.put("click", sintetizarBarrido(520, 1080, 0.065, 0.22, false, 101));
        CACHE.put("disparo_rifle", sintetizarDisparo(0.11, 220, 75, 0.34, 0.65, 102));
        CACHE.put("disparo_revolver", sintetizarDisparo(0.18, 175, 52, 0.42, 0.58, 103));
        CACHE.put("lanzagranadas", sintetizarDisparo(0.17, 130, 48, 0.40, 0.22, 104));
        CACHE.put("explosion", sintetizarDisparo(0.46, 95, 28, 0.55, 0.80, 105));
        CACHE.put("katana", sintetizarBarrido(1350, 2900, 0.15, 0.28, true, 106));
        CACHE.put("impacto", sintetizarDisparo(0.085, 190, 68, 0.26, 0.45, 107));
        CACHE.put("suministro", sintetizarArpegio(new double[]{523.25, 659.25, 783.99}, 0.065, 0.24));
        CACHE.put("victoria", sintetizarArpegio(new double[]{523.25, 659.25, 783.99, 1046.50}, 0.11, 0.28));
        CACHE.put("derrota", sintetizarArpegio(new double[]{392.00, 329.63, 261.63, 196.00}, 0.13, 0.28));
    }

    private static byte[] sintetizarBarrido(double fIni, double fFin, double durSeg,
                                            double volumen, boolean metalico, long seed) {
        int n = Math.max(1, (int) (SAMPLE_RATE * durSeg));
        byte[] buf = new byte[n * 2];
        Random rng = new Random(seed);
        double fase = 0.0;
        double fase2 = 0.0;
        for (int i = 0; i < n; i++) {
            double t = (double) i / n;
            double freq = fIni + (fFin - fIni) * t;
            double env = Math.sin(Math.PI * Math.min(1.0, t * 8.0)) * (1.0 - t);
            fase += 2.0 * Math.PI * freq / SAMPLE_RATE;
            double val = Math.sin(fase);
            if (metalico) {
                fase2 += 2.0 * Math.PI * (freq * 2.41) / SAMPLE_RATE;
                val = 0.55 * val + 0.30 * Math.sin(fase2) + 0.15 * (rng.nextDouble() * 2.0 - 1.0);
            }
            short sample = (short) Math.max(-32767, Math.min(32767, val * env * volumen * 32767.0));
            buf[i * 2] = (byte) (sample & 0xFF);
            buf[i * 2 + 1] = (byte) ((sample >> 8) & 0xFF);
        }
        return buf;
    }

    private static byte[] sintetizarDisparo(double durSeg, double fIni, double fFin,
                                            double volumen, double pesoRuido, long seed) {
        int n = Math.max(1, (int) (SAMPLE_RATE * durSeg));
        byte[] buf = new byte[n * 2];
        Random rng = new Random(seed);
        double fase = 0.0;
        double filtro = 0.0;
        for (int i = 0; i < n; i++) {
            double t = (double) i / n;
            double env = Math.pow(1.0 - t, 1.9);
            double freq = fIni * Math.pow(Math.max(0.05, fFin / fIni), t);
            fase += 2.0 * Math.PI * freq / SAMPLE_RATE;
            double tono = Math.sin(fase);
            double ruido = rng.nextDouble() * 2.0 - 1.0;
            filtro = filtro * 0.45 + ruido * 0.55;
            double mezcla = tono * (1.0 - pesoRuido) + filtro * pesoRuido;
            short sample = (short) Math.max(-32767, Math.min(32767, mezcla * env * volumen * 32767.0));
            buf[i * 2] = (byte) (sample & 0xFF);
            buf[i * 2 + 1] = (byte) ((sample >> 8) & 0xFF);
        }
        return buf;
    }

    private static byte[] sintetizarArpegio(double[] notas, double durNotaSeg, double volumen) {
        int muestrasNota = Math.max(1, (int) (SAMPLE_RATE * durNotaSeg));
        int total = muestrasNota * notas.length;
        byte[] buf = new byte[total * 2];
        for (int idx = 0; idx < notas.length; idx++) {
            double freq = notas[idx];
            for (int i = 0; i < muestrasNota; i++) {
                double t = (double) i / muestrasNota;
                double env = Math.sin(Math.PI * Math.min(1.0, t * 5.0)) * (1.0 - t * 0.75);
                double val = Math.sin(2.0 * Math.PI * freq * (i / SAMPLE_RATE));
                int pos = (idx * muestrasNota + i) * 2;
                short sample = (short) Math.max(-32767, Math.min(32767, val * env * volumen * 32767.0));
                buf[pos] = (byte) (sample & 0xFF);
                buf[pos + 1] = (byte) ((sample >> 8) & 0xFF);
            }
        }
        return buf;
    }

    private static void reproducir(final String clave) {
        if (!sonidoActivo) return;
        final byte[] datos = CACHE.get(clave);
        if (datos == null) return;
        if (VOCES_ACTIVAS.get() >= MAX_VOCES) return;

        VOCES_ACTIVAS.incrementAndGet();
        POOL.submit(new Runnable() {
            @Override
            public void run() {
                SourceDataLine line = null;
                try {
                    DataLine.Info info = new DataLine.Info(SourceDataLine.class, FORMATO);
                    if (!AudioSystem.isLineSupported(info)) return;
                    line = (SourceDataLine) AudioSystem.getLine(info);
                    line.open(FORMATO, Math.min(datos.length, 8192));
                    line.start();
                    line.write(datos, 0, datos.length);
                    line.drain();
                } catch (Exception ignored) {
                    // Evita fallos en sistemas sin tarjeta de audio
                } finally {
                    if (line != null) {
                        try {
                            line.stop();
                            line.close();
                        } catch (Exception ignored) {
                        }
                    }
                    VOCES_ACTIVAS.decrementAndGet();
                }
            }
        });
    }

    public static void alternarSonido() {
        sonidoActivo = !sonidoActivo;
        if (sonidoActivo) reproducirClickMenu();
    }

    public static boolean isSonidoActivo() { return sonidoActivo; }
    public static void reproducirHoverMenu() { reproducir("hover"); }
    public static void reproducirClickMenu() { reproducir("click"); }
    public static void reproducirDisparoRifle() { reproducir("disparo_rifle"); }
    public static void reproducirDisparoRevolver() { reproducir("disparo_revolver"); }
    public static void reproducirLanzagranadas() { reproducir("lanzagranadas"); }
    public static void reproducirExplosion() { reproducir("explosion"); }
    public static void reproducirCorteKatana() { reproducir("katana"); }
    public static void reproducirImpacto() { reproducir("impacto"); }
    public static void reproducirSuministro() { reproducir("suministro"); }
    public static void reproducirVictoria() { reproducir("victoria"); }
    public static void reproducirDerrota() { reproducir("derrota"); }
}
