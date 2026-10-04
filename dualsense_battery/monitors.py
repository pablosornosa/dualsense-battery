"""Lista de monitores (area de trabajo y DPI de cada uno)."""
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

_ENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, ctypes.c_void_p, ctypes.c_void_p,
                               ctypes.POINTER(wintypes.RECT), ctypes.c_void_p)
user32.EnumDisplayMonitors.argtypes = [ctypes.c_void_p, ctypes.c_void_p, _ENUMPROC, ctypes.c_void_p]
user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]


class _MonitorInfo(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


def _dpi(hmon):
    try:
        x, y = wintypes.UINT(), wintypes.UINT()
        ctypes.windll.shcore.GetDpiForMonitor(ctypes.c_void_p(hmon), 0, ctypes.byref(x), ctypes.byref(y))
        return x.value / 96.0
    except Exception:
        return 1.0


def list_monitors():
    """[{'work': (l,t,r,b), 'size': (w,h), 'primary': bool, 'dpi': float}], de izquierda a derecha."""
    found = []

    def cb(hmon, _hdc, _rect, _lparam):
        info = _MonitorInfo()
        info.cbSize = ctypes.sizeof(info)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            m, w = info.rcMonitor, info.rcWork
            found.append({"work": (w.left, w.top, w.right, w.bottom),
                          "origin": (m.left, m.top),
                          "size": (m.right - m.left, m.bottom - m.top),
                          "primary": bool(info.dwFlags & 1),
                          "dpi": _dpi(hmon)})
        return True

    user32.EnumDisplayMonitors(None, None, _ENUMPROC(cb), None)
    found.sort(key=lambda d: d["origin"])
    return found


def pick(monitor_setting):
    """Monitor elegido en la config ('primary' o indice 1..N); si no existe, el principal."""
    mons = list_monitors()
    if not mons:
        return {"work": (0, 0, 1920, 1080), "origin": (0, 0), "size": (1920, 1080),
                "primary": True, "dpi": 1.0}
    if monitor_setting != "primary" and 1 <= int(monitor_setting) <= len(mons):
        return mons[int(monitor_setting) - 1]
    return next((m for m in mons if m["primary"]), mons[0])
