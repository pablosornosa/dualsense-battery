"""Punto de entrada: modo segundo plano (--run) o configurador (por defecto)."""
import ctypes
import queue
import sys
import threading
import tkinter as tk

from . import config, install
from .triggers import should_show
from .popup import Popup, enable_dpi_awareness

HELP = """DualSense Battery
  (sin argumentos)  abre el configurador / instalador
  --run             popup en segundo plano al pulsar el boton PS
  --test            muestra un popup de prueba y sale
  --install         instala (arranque con Windows) sin interfaz
  --uninstall       desinstala sin interfaz
"""

_mutex = None  # se mantiene vivo mientras dure el proceso


def _single_instance():
    global _mutex
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, install.MUTEX_NAME)
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def run_background(test=False):
    from .reader import reader

    if not test and not _single_instance():
        return
    root = tk.Tk()
    root.withdraw()
    popup = Popup(root)
    events = queue.Queue()

    if test:
        events.put(("test", 70, "discharging"))
        root.after(4500, root.destroy)
    else:
        threading.Thread(target=reader, args=(events,), daemon=True).start()

    last = None

    def poll():
        nonlocal last
        try:
            while True:
                kind, pct, state = events.get_nowait()
                cfg = config.load()  # se relee: los cambios se aplican sin reiniciar
                if kind == "test" or should_show(kind, pct, state, last, cfg):
                    popup.show(pct, state, cfg)
                last = (pct, state)
        except queue.Empty:
            pass
        root.after(50, poll)

    poll()
    root.mainloop()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    enable_dpi_awareness()
    if "--run" in argv:
        run_background()
    elif "--test" in argv:
        run_background(test=True)
    elif "--install" in argv:
        install.install()
    elif "--uninstall" in argv:
        install.uninstall()
    elif "--help" in argv or "-h" in argv:
        print(HELP)
    else:
        from .configurator import Configurator
        Configurator().run()
