"""Popup con transparencia real por pixel (UpdateLayeredWindow + Pillow)."""
import ctypes
import math
import tkinter as tk
from ctypes import wintypes

from PIL import Image, ImageDraw, ImageFont

from . import config
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


def _work_area():
    r = wintypes.RECT()
    user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)  # SPI_GETWORKAREA
    return r.left, r.top, r.right, r.bottom


class Popup:
    BG, FG, DIM, TRACK = "#141518", "#f5f5f7", "#8d9099", "#2c2e34"
    W, H, MARGIN = 144, 46, 20  # tamano base en px a 96 dpi y escala 1.0
    FADE_STEP, FADE_MS = 0.12, 12

    def __init__(self, root):
        self.root = root
        self.win = None
        self.hide_job = None
        self.fade_job = None
        self.alpha = 0.0
        self.pos = (0, 0)
        self.size = (1, 1)
        self.gdi = None
        self.dpi = root.winfo_fpixels("1i") / 96.0

    # ---------- dibujo ----------
    def _render(self, w, h, k, pct, state, color, lang):
        S = 4  # supersampling para antialiasing
        img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        dr.rounded_rectangle((0, 0, w * S - 1, h * S - 1), radius=h * S // 2, fill=self.BG)
        # anillo de progreso (PIL dibuja el trazo hacia dentro del recuadro)
        d, lw = 24 * k * S, max(2, round(3 * k)) * S
        x0, y0 = 12 * k * S, (h * S - d) / 2
        box = (x0, y0, x0 + d, y0 + d)
        dr.ellipse(box, outline=self.TRACK, width=int(lw))
        cx, cy, r = x0 + d / 2, y0 + d / 2, d / 2 - lw / 2
        if pct > 0:
            end = -90 + 359.9 * min(pct, 100) / 100
            dr.arc(box, start=-90, end=end, fill=color, width=int(lw))
            for ang in (-90, end):  # extremos redondeados
                px, py = cx + r * math.cos(math.radians(ang)), cy + r * math.sin(math.radians(ang))
                dr.ellipse((px - lw / 2, py - lw / 2, px + lw / 2, py + lw / 2), fill=color)
        if state == "charging":
            u = k * S * 0.8
            bolt = [(1.5, -6), (-3.5, 1), (-0.5, 1), (-1.5, 6), (3.5, -1), (0.5, -1)]
            dr.polygon([(cx + x * u, cy + y * u) for x, y in bolt], fill=color)
        semibold = _font(("seguisb.ttf", "segoeui.ttf"), round(19 * k * S))
        regular = _font(("segoeui.ttf",), round(10.5 * k * S))
        label = tr(lang, {"charging": "charging", "full": "full"}.get(state, "device"))
        dr.text((46 * k * S, h * S * 0.34), f"{pct}%", font=semibold, fill=self.FG, anchor="lm")
        dr.text((46 * k * S, h * S * 0.76), label, font=regular, fill=self.DIM, anchor="lm")
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

    def _position(self, w, h, margin, corner):
        left, top, right, bottom = _work_area()
        vert, horiz = corner.split("-")
        x = {"left": left + margin, "right": right - w - margin,
             "center": (left + right - w) // 2}[horiz]
        y = top + margin if vert == "top" else bottom - h - margin
        return x, y

    # ---------- API ----------
    def show(self, pct, state, cfg=None):
        cfg = cfg or config.load()
        k = self.dpi * cfg["scale"]
        w, h = round(self.W * k), round(self.H * k)
        if self.win is None:
            self._create()
        color = "#34c759" if pct > 30 else ("#ffd60a" if pct > 15 else "#ff453a")
        lang = config.resolve_language(cfg)
        self._set_bitmap(self._render(w, h, k, pct, state, color, lang))
        self.pos = self._position(w, h, round(self.MARGIN * k), cfg["corner"])
        self.win.geometry(f"{w}x{h}+{self.pos[0]}+{self.pos[1]}")
        self.win.deiconify()
        self.win.update_idletasks()
        self._apply(self.alpha)
        self._fade(cfg["opacity"])
        if self.hide_job:
            self.root.after_cancel(self.hide_job)
        self.hide_job = self.root.after(int(cfg["duration"] * 1000), self._hide)
