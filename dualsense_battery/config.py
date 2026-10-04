"""Carga y guarda la configuracion (%APPDATA%\\DualSenseBattery\\config.json)."""
import ctypes
import json
import os

APP_NAME = "DualSenseBattery"

CORNERS = ("top-right", "top-left", "top-center",
           "bottom-right", "bottom-left", "bottom-center")

DEFAULTS = {
    "language": "auto",       # auto | es | en
    "corner": "top-right",
    "scale": 1.25,            # tamano del popup
    "duration": 3.0,          # segundos en pantalla
    "opacity": 0.96,
}

LIMITS = {"scale": (0.75, 2.5), "duration": (1.0, 10.0), "opacity": (0.4, 1.0)}


def config_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME)


def config_path():
    return os.path.join(config_dir(), "config.json")


def sanitize(cfg):
    out = dict(DEFAULTS)
    out.update({k: v for k, v in cfg.items() if k in DEFAULTS})
    if out["corner"] not in CORNERS:
        out["corner"] = DEFAULTS["corner"]
    if out["language"] not in ("auto", "es", "en"):
        out["language"] = "auto"
    for key, (lo, hi) in LIMITS.items():
        try:
            out[key] = min(hi, max(lo, float(out[key])))
        except (TypeError, ValueError):
            out[key] = DEFAULTS[key]
    return out


def load():
    try:
        with open(config_path(), encoding="utf-8") as f:
            return sanitize(json.load(f))
    except (OSError, ValueError):
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
