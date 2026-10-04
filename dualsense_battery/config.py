"""Carga y guarda la configuracion (%APPDATA%\\DualSenseBattery\\config.json)."""
import ctypes
import json
import os
import re

APP_NAME = "DualSenseBattery"

CORNERS = ("top-right", "top-left", "top-center",
           "bottom-right", "bottom-left", "bottom-center")
STYLES = ("ring", "bar", "battery", "minimal")
THEMES = ("dark", "light", "system")
COLOR_MODES = ("level", "accent")
TRIGGERS = ("on_ps", "on_connect", "on_charge", "on_low")

DEFAULTS = {
    "language": "auto",          # auto | es | en
    "style": "ring",
    "theme": "dark",
    "color_mode": "level",       # level = verde/amarillo/rojo segun bateria | accent = color fijo
    "accent": "#34c759",
    "charging_color_on": True,   # color distinto mientras carga
    "charging_color": "#0a84ff",
    "corner": "top-right",
    "monitor": "primary",        # "primary" o numero de monitor (1, 2, ...)
    "scale": 1.25,
    "duration": 3.0,             # segundos en pantalla
    "opacity": 0.96,
    "on_ps": True,               # al pulsar el boton PS
    "on_connect": False,         # al conectar el mando
    "on_charge": False,          # al empezar a cargar / completar la carga
    "on_low": False,             # al bajar del umbral de bateria baja
    "low_threshold": 20,
}

LIMITS = {"scale": (0.75, 2.5), "duration": (1.0, 10.0), "opacity": (0.4, 1.0),
          "low_threshold": (5, 50)}

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def config_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME)


def config_path():
    return os.path.join(config_dir(), "config.json")


def _choice(value, allowed, default):
    return value if value in allowed else default


def sanitize(cfg):
    out = dict(DEFAULTS)
    out.update({k: v for k, v in cfg.items() if k in DEFAULTS})
    out["language"] = _choice(out["language"], ("auto", "es", "en"), DEFAULTS["language"])
    out["corner"] = _choice(out["corner"], CORNERS, DEFAULTS["corner"])
    out["style"] = _choice(out["style"], STYLES, DEFAULTS["style"])
    out["theme"] = _choice(out["theme"], THEMES, DEFAULTS["theme"])
    out["color_mode"] = _choice(out["color_mode"], COLOR_MODES, DEFAULTS["color_mode"])
    for key in ("accent", "charging_color"):
        if not (isinstance(out[key], str) and _HEX.match(out[key])):
            out[key] = DEFAULTS[key]
    for key, (lo, hi) in LIMITS.items():
        try:
            out[key] = min(hi, max(lo, float(out[key])))
        except (TypeError, ValueError):
            out[key] = DEFAULTS[key]
    out["low_threshold"] = int(round(out["low_threshold"]))
    mon = out["monitor"]
    if mon != "primary":
        try:
            mon = int(mon)
        except (TypeError, ValueError):
            mon = 0
        out["monitor"] = mon if mon >= 1 else "primary"
    for key in ("charging_color_on",) + TRIGGERS:
        out[key] = bool(out[key])
    if not any(out[k] for k in TRIGGERS):  # sin disparadores el popup no saldria nunca
        out["on_ps"] = True
    return out


def load():
    try:
        with open(config_path(), encoding="utf-8") as f:
            return sanitize(json.load(f))
    except (OSError, ValueError, AttributeError):
        return dict(DEFAULTS)


def save(cfg):
    os.makedirs(config_dir(), exist_ok=True)
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(sanitize(cfg), f, indent=2)


def resolve_language(cfg):
    lang = cfg.get("language", "auto")
    if lang in ("es", "en"):
        return lang
    try:
        buf = ctypes.create_unicode_buffer(85)
        ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85)
        return "es" if buf.value.lower().startswith("es") else "en"
    except Exception:
        return "en"
