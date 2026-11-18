# The Walking Bowmasters - Edición POO Modular (Lógica de Programación II)

Videojuego 2D Side-Scroller a 60 FPS en **Java Swing / AWT (`Graphics2D`)** que combina la mecánica balística parabólica de *Bowmasters* con la ambientación post-apocalíptica de *The Walking Dead*, diseñado e implementado aplicando explícitamente todos los pilares de la **Programación Orientada a Objetos (POO)**.

## Estructura Modular por Paquetes

```text
ProyectoLogicaDeProgramacion/
├── WalkingBowmastersPOO.java          # Ventana Swing, bucle 60 FPS, Menú interactivo con cursor y HUD
├── util/
│   └── ConstantesJuego.java           # Resolución lógica (1280x720), gravedad y utilidades
├── audio/
│   └── GestorSonido.java              # Sintetizador PCM procedural (javax.sound.sampled)
├── interfaces/
│   ├── Renderizable.java              # Contrato gráfico 2D
│   ├── Atacable.java                  # Contrato de salud y daño
│   └── ModoJuego.java                 # Contrato de modos de juego
├── efectos/
│   ├── Particula.java                 # Chispas, fuego, humo y sangre
│   ├── OndaExpansiva.java             # Onda expansiva AoE
│   └── TextoFlotante.java             # Textos flotantes de daño, críticos y botín
├── escenario/
│   ├── ObstaculoTerreno.java          # Autobús volcado y coche destruido para el duelo 1v1
│   └── EscenarioApocaliptico.java     # Fondo crepuscular con Parallax y cenizas
├── armas/
│   ├── Arma.java                      # Clase abstracta base del arsenal
│   ├── RifleAsalto.java               # Ráfaga rápida x3 con poca caída gravitacional
│   ├── LanzaGranadas.java             # Arco parabólico pesado y daño en área (AoE)
│   ├── Revolver.java                  # Disparo único de alta precisión y crítico
│   └── EspadaKatana.java              # Corte letal cuerpo a cuerpo o arrojadiza
├── inventario/
│   ├── TipoSuministro.java            # Tipos: BOTIQUIN, CAJA_MUNICION, RACION
│   ├── Suministro.java                # Recurso independiente (Agregación Débil)
│   └── Inventario.java                # Almacén compartido entre modos y combatientes
├── entidades/
│   ├── EntidadJuego.java              # Clase abstracta raíz de entidades físicas
│   ├── TipoProyectil.java             # Enum de proyectiles
│   ├── Proyectil.java                 # Física balística con viento y estela
│   ├── Combatiente.java               # Padre de personajes + sobrecarga calcularDano(...)
│   ├── Superviviente.java             # Jugador principal (Modo 1 y Campo de Tiro)
│   ├── Zombie.java                    # Base abstracta de infectados
│   ├── ZombieCaminante.java           # Caminante lento
│   ├── ZombieCorredor.java            # Corredor rápido
│   ├── ZombieBlindado.java            # Tanque con casco antidisturbios y armadura
│   ├── SaqueadorRival.java            # Enemigo humano hostil
│   └── Batallon.java                  # Composición Fuerte (*-- MiembroEscuadron interno)
└── modos/
    ├── BaseModoJuego.java             # Seguimiento del cursor y disparo con tecla X (5% / 100%)
    ├── ModoSupervivenciaHordas.java   # Modo 1: Oleadas procedurales en barricada
    ├── ModoDueloBatallones.java       # Modo 2: Duelo táctico por turnos 1v1 con viento e IA
    └── ModoArmeriaCampoTiro.java      # Modo 3: Gestión del Inventario y Campo de Tiro
```

## Compilación y Ejecución

```powershell
javac -encoding UTF-8 WalkingBowmastersPOO.java util/*.java audio/*.java interfaces/*.java efectos/*.java escenario/*.java armas/*.java inventario/*.java entidades/*.java modos/*.java
java WalkingBowmastersPOO
```

## Controles Principales

- **Menú y Navegación:** Selecciona cualquier modo pasando el **cursor del ratón** y haciendo clic (o con flechas `↑`/`↓` + `ENTER`, teclas `1`/`2`/`3` o pestañas superiores `F1`/`F2`/`F3`).
- **Disparo estilo Bowmasters:** Clic izquierdo + arrastrar para definir ángulo y potencia + soltar.
- **Disparo con Tecla `X` (5% y 100%):**
  - Apunta con el **cursor** y pulsa `X` para disparar al porcentaje activo (`5%` o `100%`).
  - Alterna entre `5%` y `100%` en la barra superior (`[X: 5%]` / `[X: 100%]`) o con la tecla `C`.
  - Mantén presionada `X` para cargar progresivamente desde `5%` hasta `100%` y suelta para disparar; `Shift + X` fuerza `5%`.
- **Armas y Suministros:** Teclas `1`-`4` (armas), `ESPACIO` (corte cuerpo a cuerpo con Katana), `Q`/`E`/`R` (Botiquín, Caja de Munición, Ración), `M` (silenciar/activar sonido).
