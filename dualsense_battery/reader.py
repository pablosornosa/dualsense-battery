"""Lectura del DualSense por HID (USB y Bluetooth)."""
import time

SONY_VID = 0x054C
PIDS = (0x0CE6, 0x0DF2)  # DualSense, DualSense Edge


def parse_report(data):
    """Devuelve (ps_pressed, porcentaje, estado) o None si el informe no sirve."""
    if not data:
        return None
    rid = data[0]
    if rid == 0x01 and len(data) >= 54:      # USB
        ps_idx, st_idx = 10, 53
    elif rid == 0x31 and len(data) >= 55:    # Bluetooth (informe completo)
        ps_idx, st_idx = 11, 54
    else:
        return None
    ps = bool(data[ps_idx] & 0x01)
    status = data[st_idx]
    level = status & 0x0F
    charge = (status >> 4) & 0x0F
    if charge == 0x2:
        return ps, 100, "full"
    pct = min(level * 10 + 5, 100)
    return ps, pct, "charging" if charge == 0x1 else "discharging"


def reader(events):
    """Hilo lector: pone en `events` tuplas (tipo, pct, estado).

    tipo: "connect" (primer informe tras conectar), "ps" (boton PS pulsado)
          o "change" (cambio de porcentaje o de estado de carga).
    """
    import hid  # import perezoso: el configurador no lo necesita

    while True:
        info = next((d for p in PIDS for d in hid.enumerate(SONY_VID, p)), None)
        if not info:
            time.sleep(2)
            continue
        dev = hid.device()
        last_ps, last = False, None
        try:
            dev.open_path(info["path"])
            dev.set_nonblocking(False)
            # Por Bluetooth el mando manda un informe reducido hasta que se lee
            # el feature report 0x05; despues pasa al informe completo 0x31.
            try:
                dev.get_feature_report(0x05, 64)
            except Exception:
                pass
            while True:
                parsed = parse_report(dev.read(78, 1000))
                if not parsed:
                    continue
                ps, pct, state = parsed
                if last is None:
                    events.put(("connect", pct, state))
                elif (pct, state) != last:
                    events.put(("change", pct, state))
                last = (pct, state)
                if ps and not last_ps:
                    events.put(("ps", pct, state))
                last_ps = ps
        except Exception:
            pass  # mando desconectado o error: reintentar
        finally:
            try:
                dev.close()
            except Exception:
                pass
        time.sleep(1)
