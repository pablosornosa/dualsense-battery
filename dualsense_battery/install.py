"""Instalacion por usuario: sin administrador, sin registro, sin tareas programadas.

- Version .exe: copia el exe a %LOCALAPPDATA%\\Programs\\DualSenseBattery.
- Version codigo fuente: los accesos directos apuntan a pythonw + main.py donde esta.
En ambos casos crea un acceso directo en Inicio (arranca con Windows) y otro en el menu Inicio.
"""
import ctypes
import os
import shutil
import subprocess
import sys

from . import config

APP_NAME = config.APP_NAME
MUTEX_NAME = "Local\\DualSenseBatteryPopup"
LNK_STARTUP = "DualSense Battery.lnk"
LNK_MENU = "DualSense Battery - Settings.lnk"
NO_WINDOW = 0x08000000
DETACHED = 0x00000008


def frozen():
    return getattr(sys, "frozen", False)


def install_dir():
    return os.path.join(os.environ["LOCALAPPDATA"], "Programs", APP_NAME)


def programs_dir():
    return os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs")


def startup_dir():
    return os.path.join(programs_dir(), "Startup")


def installed_exe():
    return os.path.join(install_dir(), "DualSenseBattery.exe")


def _source_command():
    py = sys.executable
    pyw = os.path.join(os.path.dirname(py), "pythonw.exe")
    main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
    return (pyw if os.path.exists(pyw) else py), [main_py]


def command(extra=()):
    """Comando completo (lista) para lanzar la app con argumentos extra."""
    if frozen():
        exe = installed_exe() if os.path.exists(installed_exe()) else sys.executable
        return [exe, *extra]
    exe, args = _source_command()
    return [exe, *args, *extra]


def _powershell(script):
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                          capture_output=True, text=True, creationflags=NO_WINDOW)


def _q(s):
    return str(s).replace("'", "''")


def _make_shortcut(lnk_path, cmd, working_dir):
    target, args = cmd[0], " ".join(f'"{a}"' if " " in a else a for a in cmd[1:])
    script = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');"
              "$s.TargetPath='%s';$s.Arguments='%s';$s.WorkingDirectory='%s';"
              "$s.IconLocation='%s,0';$s.WindowStyle=7;$s.Save()"
              % (_q(lnk_path), _q(target), _q(args), _q(working_dir), _q(target)))
    r = _powershell(script)
    if r.returncode != 0 or not os.path.exists(lnk_path):
        raise RuntimeError(r.stderr.strip() or "No se pudo crear el acceso directo")


def is_installed():
    return os.path.exists(os.path.join(startup_dir(), LNK_STARTUP))


def is_running():
    handle = ctypes.windll.kernel32.OpenMutexW(0x00100000, False, MUTEX_NAME)  # SYNCHRONIZE
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    return False


def start_background():
    if is_running():
        return
    subprocess.Popen(command(["--run"]), creationflags=DETACHED | NO_WINDOW,
                     close_fds=True, cwd=os.path.dirname(command()[0]))


def stop_background():
    _powershell("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "
                "'(DualSenseBattery\\.exe|main\\.py).*--run' } | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")


def install():
    stop_background()
    if frozen():
        os.makedirs(install_dir(), exist_ok=True)
        if os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(installed_exe()):
            shutil.copy2(sys.executable, installed_exe())
        workdir = install_dir()
    else:
        workdir = os.path.dirname(command()[1]) if len(command()) > 1 else os.getcwd()
    os.makedirs(startup_dir(), exist_ok=True)
    _make_shortcut(os.path.join(startup_dir(), LNK_STARTUP), command(["--run"]), workdir)
    _make_shortcut(os.path.join(programs_dir(), LNK_MENU), command(), workdir)
    start_background()


def uninstall(remove_config=False):
    stop_background()
    for p in (os.path.join(startup_dir(), LNK_STARTUP), os.path.join(programs_dir(), LNK_MENU)):
        if os.path.exists(p):
            os.remove(p)
    if remove_config:
        shutil.rmtree(config.config_dir(), ignore_errors=True)
    if frozen() and os.path.isdir(install_dir()):
        here = os.path.normcase(os.path.dirname(os.path.abspath(sys.executable)))
        if here == os.path.normcase(install_dir()):
            # No se puede borrar el exe en uso: se borra unos segundos despues.
            subprocess.Popen(f'cmd /c ping -n 4 127.0.0.1 >nul & rmdir /s /q "{install_dir()}"',
                             creationflags=DETACHED | NO_WINDOW, close_fds=True)
        else:
            shutil.rmtree(install_dir(), ignore_errors=True)
