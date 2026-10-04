"""Popup con transparencia real por pixel (UpdateLayeredWindow + Pillow)."""
import ctypes
import math
import tkinter as tk
from ctypes import wintypes

from PIL import Image, ImageDraw, ImageFont

from . import config, monitors
from .i18n import tr

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.GetDC.restype = ctypes.c_void_p
user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.GetAncestor.restype = ctypes.c_void_p
user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
user32.UpdateLayeredWindow.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                       wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
gdi32.CreateDIBSection.restype = ctypes.c_void_p
gdi32.CreateDIBSection.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT,
                                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD]
gdi32.SelectObject.restype = ctypes.c_void_p
gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
gdi32.DeleteDC.argtypes = [ctypes.c_void_p]


def enable_dpi_awareness():
    """Llamar antes de crear cualquier ventana Tk (evita imagen escalada y borrosa)."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


class _BitmapInfoHeader(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class _Blend(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]


def _font(names, px):
    for n in names:
        try:
            return ImageFont.truetype(n, px)
        except OSError:
            pass
    return ImageFont.load_default()


THEME_COLORS = {
    "dark": {"bg": "#141518", "fg": "#f5f5f7", "dim": "#8d9099", "track": "#2c2e34"},
    "light": {"bg": "#f5f5f7", "fg": "#141518", "dim": "#6b6f78", "track": "#d8dbe0"},
}
STYLE_SIZE = {"ring": (144, 46), "bar": (176, 56), "battery": (150, 46), "minimal": (100, 38)}
BOLT = [(1.5, -6), (-3.5, 1), (-0.5, 1), (-1.5, 6), (3.5, -1), (0.5, -1)]


def resolve_theme(name):
    if name == "system":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            return "light" if winreg.QueryValueEx(key, "AppsUseLightTheme")[0] else "dark"
        except OSError:
            return "dark"
    return name if name in THEME_COLORS else "dark"


def accent_color(cfg, pct, state):
    """Color del indicador: especial al cargar, fijo si se eligio, o segun el nivel."""
    if state == "charging" and cfg["charging_color_on"]:
        return cfg["charging_color"]
    if cfg["color_mode"] == "accent":
        return cfg["accent"]
    return "#34c759" if pct > 30 else ("#ffd60a" if pct > 15 else "#ff453a")


class Popup:
    MARGIN = 20  # px a 96 dpi y escala 1.0
    FADE_STEP, FADE_MS = 0.12, 12
    S = 4  # supersampling para antialiasing

    def __init__(self, root):
        self.root = root
        self.win = None
        self.hide_job = None
        self.fade_job = None
        self.alpha = 0.0
        self.pos = (0, 0)
        self.size = (1, 1)
        self.gdi = None

    # ---------- dibujo ----------
    def _bolt(self, dr, cx, cy, u, fill, halo=None):
        if halo:  # contorno para que se vea sobre cualquier fondo
            dr.polygon([(cx + x * u * 1.35, cy + y * u * 1.35) for x, y in BOLT], fill=halo)
        dr.polygon([(cx + x * u, cy + y * u) for x, y in BOLT], fill=fill)

    def _render(self, cfg, pct, state, k):
        S, style = self.S, cfg["style"]
        pal = THEME_COLORS[resolve_theme(cfg["theme"])]
        color = accent_color(cfg, pct, state)
        lang = config.resolve_language(cfg)
        bw, bh = STYLE_SIZE[style]
        w, h = round(bw * k), round(bh * k)
        K = k * S  # 1 px base -> K px en el lienzo ampliado
        W, H = w * S, h * S
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        radius = 16 * K if style == "bar" else H // 2
        dr.rounded_rectangle((0, 0, W - 1, H - 1), radius=radius, fill=pal["bg"])
        semibold = _font(("seguisb.ttf", "segoeui.ttf"), round((17 if style == "minimal" else 19) * K))
        regular = _font(("segoeui.ttf",), round(10.5 * K))
        label = tr(lang, {"charging": "charging", "full": "full"}.get(state, "device"))
        text = f"{pct}%"
        charging = state == "charging"

        if style == "ring":
            d, lw = 24 * K, max(2, round(3 * k)) * S
            x0, y0 = 12 * K, (H - d) / 2
            box = (x0, y0, x0 + d, y0 + d)
            dr.ellipse(box, outline=pal["track"], width=int(lw))
            cx, cy, r = x0 + d / 2, y0 + d / 2, d / 2 - lw / 2
            if pct > 0:
                end = -90 + 359.9 * min(pct, 100) / 100
                dr.arc(box, start=-90, end=end, fill=color, width=int(lw))
                for ang in (-90, end):  # extremos redondeados
                    px, py = cx + r * math.cos(math.radians(ang)), cy + r * math.sin(math.radians(ang))
                    dr.ellipse((px - lw / 2, py - lw / 2, px + lw / 2, py + lw / 2), fill=color)
            if charging:
                self._bolt(dr, cx, cy, K * 0.8, color)
            dr.text((46 * K, H * 0.34), text, font=semibold, fill=pal["fg"], anchor="lm")
            dr.text((46 * K, H * 0.76), label, font=regular, fill=pal["dim"], anchor="lm")

        elif style == "battery":
            bx, bwid, bhgt = 14 * K, 32 * K, 18 * K
            by = (H - bhgt) / 2
            dr.rounded_rectangle((bx, by, bx + bwid, by + bhgt), radius=4 * K,
                                 outline=pal["dim"], width=int(2 * K))
            dr.rounded_rectangle((bx + bwid + 1 * K, H / 2 - 4 * K, bx + bwid + 4 * K, H / 2 + 4 * K),
                                 radius=1 * K, fill=pal["dim"])
            ix0, iy0, ix1, iy1 = bx + 3.5 * K, by + 3.5 * K, bx + bwid - 3.5 * K, by + bhgt - 3.5 * K
            fw = (ix1 - ix0) * min(pct, 100) / 100
            if fw > 0:
                dr.rounded_rectangle((ix0, iy0, ix0 + max(fw, 4 * K), iy1), radius=2 * K, fill=color)
            if charging:
                self._bolt(dr, bx + bwid / 2, H / 2, K * 0.7, pal["fg"], halo=pal["bg"])
            dr.text((60 * K, H * 0.34), text, font=semibold, fill=pal["fg"], anchor="lm")
            dr.text((60 * K, H * 0.76), label, font=regular, fill=pal["dim"], anchor="lm")

        elif style == "bar":
            dr.text((16 * K, H * 0.32), text, font=semibold, fill=pal["fg"], anchor="lm")
            if charging:
                self._bolt(dr, 16 * K + dr.textlength(text, font=semibold) + 12 * K, H * 0.32,
                           K * 1.0, color)
            dr.text((W - 16 * K, H * 0.32), label, font=regular, fill=pal["dim"], anchor="rm")
            x0, x1, y0 = 16 * K, W - 16 * K, H * 0.64
            dr.rounded_rectangle((x0, y0, x1, y0 + 8 * K), radius=4 * K, fill=pal["track"])
            if pct > 0:
                fx = x0 + max((x1 - x0) * min(pct, 100) / 100, 8 * K)
                dr.rounded_rectangle((x0, y0, fx, y0 + 8 * K), radius=4 * K, fill=color)

        else:  # minimal
            if charging:
                self._bolt(dr, 18 * K, H / 2, K * 1.1, color)
            else:
                dr.ellipse((13 * K, H / 2 - 5 * K, 23 * K, H / 2 + 5 * K), fill=color)
            dr.text((34 * K, H / 2), text, font=semibold, fill=pal["fg"], anchor="lm")

        return img.resize((w, h), Image.LANCZOS)

    # ---------- ventana en capas ----------
    def _release(self):
        if self.gdi:
            memdc, hbm, old = self.gdi
            gdi32.SelectObject(memdc, old)
            gdi32.DeleteObject(hbm)
            gdi32.DeleteDC(memdc)
            self.gdi = None

    def _set_bitmap(self, img):
        self._release()
        w, h = img.size
        r, g, b, a = img.convert("RGBa").split()  # premultiplicado, como pide Windows
        data = Image.merge("RGBA", (b, g, r, a)).tobytes()
        bmi = _BitmapInfoHeader(ctypes.sizeof(_BitmapInfoHeader), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        bits = ctypes.c_void_p()
        hbm = gdi32.CreateDIBSection(None, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        ctypes.memmove(bits, data, len(data))
        screen = user32.GetDC(None)
        memdc = gdi32.CreateCompatibleDC(screen)
        user32.ReleaseDC(None, screen)
        self.gdi = (memdc, hbm, gdi32.SelectObject(memdc, hbm))
        self.size = (w, h)

    def _apply(self, alpha):
        self.alpha = alpha
        if not self.gdi:
            return
        pt = wintypes.POINT(*self.pos)
        sz = wintypes.SIZE(*self.size)
        src = wintypes.POINT(0, 0)
        blend = _Blend(0, 0, max(0, min(255, round(alpha * 255))), 1)  # AC_SRC_ALPHA
        user32.UpdateLayeredWindow(self.hwnd, None, ctypes.byref(pt), ctypes.byref(sz),
                                   self.gdi[0], ctypes.byref(src), 0, ctypes.byref(blend), 2)

    def _fade(self, target, done=None):
        if self.fade_job:
            self.root.after_cancel(self.fade_job)

        def step():
            a = self.alpha
            a = min(target, a + self.FADE_STEP) if target > a else max(target, a - self.FADE_STEP)
            self._apply(a)
            if a != target:
                self.fade_job = self.root.after(self.FADE_MS, step)
            else:
                self.fade_job = None
                if done:
                    done()
        step()

    def _hide(self):
        self.hide_job = None
        self._fade(0.0, self.win.withdraw)

    def _create(self):
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.geometry("1x1+0+0")
        self.win.update_idletasks()
        self.hwnd = user32.GetAncestor(self.win.winfo_id(), 2) or self.win.winfo_id()
        ex = user32.GetWindowLongPtrW(self.hwnd, -20)
        # layered | toolwindow | noactivate | transparent (los clics lo atraviesan)
        user32.SetWindowLongPtrW(self.hwnd, -20, ex | 0x80000 | 0x80 | 0x08000000 | 0x20)

    def _position(self, mon, w, h, margin, corner):
        left, top, right, bottom = mon["work"]
        vert, horiz = corner.split("-")
        x = {"left": left + margin, "right": right - w - margin,
             "center": (left + right - w) // 2}[horiz]
        y = top + margin if vert == "top" else bottom - h - margin
        return x, y

    # ---------- API ----------
    def show(self, pct, state, cfg=None):
        cfg = cfg or config.load()
        mon = monitors.pick(cfg["monitor"])
        k = mon["dpi"] * cfg["scale"]
        if self.win is None:
            self._create()
        img = self._render(cfg, pct, state, k)
        self._set_bitmap(img)
        w, h = img.size
        self.pos = self._position(mon, w, h, round(self.MARGIN * k), cfg["corner"])
        self.win.geometry(f"{w}x{h}+{self.pos[0]}+{self.pos[1]}")
        self.win.deiconify()
        self.win.update_idletasks()
        self._apply(self.alpha)
        self._fade(cfg["opacity"])
        if self.hide_job:
            self.root.after_cancel(self.hide_job)
        self.hide_job = self.root.after(int(cfg["duration"] * 1000), self._hide)
