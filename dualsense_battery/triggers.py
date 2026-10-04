"""Decide si un evento del mando debe mostrar el popup (logica pura, sin UI)."""


def should_show(kind, pct, state, last, cfg):
    """
    kind:  "ps" (boton PS), "connect" (primer informe tras conectar) o "change" (cambio de bateria).
    last:  (pct, state) anterior conocido, o None.
    """
    if kind == "ps":
        return cfg["on_ps"]
    if kind == "connect":
        return cfg["on_connect"]
    if kind == "change" and last is not None:
        last_pct, last_state = last
        if cfg["on_charge"] and state != last_state and state in ("charging", "full"):
            return True
        if (cfg["on_low"] and state == "discharging" and pct < last_pct
                and pct <= cfg["low_threshold"]):
            return True
    return False
