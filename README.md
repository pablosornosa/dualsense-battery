# DualSense Battery Popup

**ES** · Al pulsar el botón **PS** del DualSense en Windows, aparece un popup con el porcentaje de batería, como en la PlayStation.
**EN** · Press the **PS** button on your DualSense on Windows and a small popup shows the battery level, like on a PlayStation.

<p align="center"><img src="assets/icon.png" width="96" alt="icon"></p>

## Características / Features

- Funciona por **USB y Bluetooth** (DualSense y DualSense Edge) / Works over **USB and Bluetooth**.
- Popup minimalista con anillo de progreso, transparencia real y fundido suave / Minimal popup with progress ring, true transparency and fade.
- Indica si está **cargando** o **completa** / Shows charging and full states.
- **4 estilos** (anillo, barra, batería, mínimo) y **tema** oscuro, claro o igual que Windows / 4 styles and dark, light or system theme.
- Color según el nivel (verde / amarillo / rojo) o **color fijo**; color propio **mientras carga** con un rayo ⚡ / Level-based or fixed color, plus a distinct charging color and bolt.
- **Cuándo mostrarlo:** al pulsar PS, al conectar el mando, al empezar/terminar de cargar o al bajar de un umbral de batería baja / Choose when it appears: PS press, connect, charge start/finish, low battery.
- Elige **esquina** y **monitor**; tamaño, duración y opacidad con slider **o escribiendo el valor** / Corner, monitor, and size/duration/opacity via slider or typed value.
- Idioma es/en / Spanish and English UI.
- Un solo `.exe`: configurador + instalador + programa en segundo plano / A single `.exe`: settings + installer + background app.
- Instalación **por usuario**, sin administrador, sin registro ni tareas programadas / Per-user install, no admin, no registry, no scheduled tasks.
- No roba el foco y los clics lo atraviesan, así que no molesta en los juegos en ventana / Never takes focus; clicks pass through.

## Instalación / Install

### Opción A — `.exe` (recomendada)

1. Descarga `DualSenseBattery.exe` desde [Releases](../../releases) / Download it from Releases.
2. Ábrelo, ajusta lo que quieras y pulsa **Instalar / Install**.
   Se copia a `%LOCALAPPDATA%\Programs\DualSenseBattery`, arranca con Windows y se inicia ya.

> Windows SmartScreen puede avisar porque el `.exe` no está firmado. / SmartScreen may warn because the exe is unsigned.

### Opción B — desde el código / From source

```powershell
git clone https://github.com/pablosornosa/dualsense-battery.git
cd dualsense-battery
python -m pip install -r requirements.txt
python main.py            # abre el configurador / opens the settings window
```

Pulsa **Instalar** en el configurador y los accesos directos apuntarán a `pythonw main.py` en esa carpeta (no la muevas después).

### Desinstalar / Uninstall

Botón **Desinstalar** en el configurador (también existe `DualSenseBattery.exe --uninstall`).

## Uso / Usage

Conecta el mando y pulsa el botón PS. Línea de comandos:

| Argumento | Acción |
|---|---|
| *(ninguno)* | Configurador / instalador |
| `--run` | Popup en segundo plano (lo que arranca con Windows) |
| `--test` | Muestra un popup de prueba |
| `--install` / `--uninstall` | Instala / desinstala sin interfaz |

La configuración se guarda en `%APPDATA%\DualSenseBattery\config.json` y se aplica al siguiente popup, sin reiniciar.

## Tests

```powershell
python -m unittest discover -s tests
```

## Compilar el exe / Build

```powershell
./build.ps1        # genera dist\DualSenseBattery.exe con PyInstaller
```

Al subir una etiqueta `v*`, el workflow de `.github/workflows/build.yml` compila el exe y lo adjunta al release.

## Cómo funciona / How it works

- Lee el mando directamente por HID (`hidapi`). El informe de entrada contiene el botón PS y el nivel de batería (0–10 → saltos del 10 %, igual que la PS5).
- Por Bluetooth, el mando envía un informe reducido hasta que se lee el *feature report* `0x05`; la app lo hace al conectar para recibir el informe completo `0x31`.
- El popup es una ventana de Windows con *layered window* (`UpdateLayeredWindow`) dibujada con Pillow, lo que da bordes suaves y transparencia por píxel.
- Una sola instancia: un *mutex* evita lanzar dos copias.

## Limitaciones / Limitations

- Solo **Windows 10/11**.
- Si **Steam Input**, **DS4Windows** u otra app acapara el mando, el botón PS puede llegar con retraso o no llegar. / If another app exclusively grabs the controller, the PS button may not reach this app.
- El porcentaje avanza en saltos del 10 %. / Battery is reported in 10 % steps.
- En juegos a **pantalla completa exclusiva** el popup puede quedar oculto; usa modo ventana o sin bordes. / May be hidden over exclusive fullscreen games.
- Solo usa el monitor principal. / Primary monitor only.
- Con el Python de la **Microsoft Store**, instala desde el `.exe` o ejecuta el código desde una carpeta normal (no dentro de `AppData`).

## Licencia / License

[MIT](LICENSE): puedes usarlo, modificarlo y redistribuirlo libremente; las contribuciones vía fork + pull request son bienvenidas. / Free to use, modify and redistribute; forks and pull requests welcome.

*No afiliado a Sony. "PlayStation" y "DualSense" son marcas de Sony Interactive Entertainment. / Not affiliated with Sony.*
