"""Ventana de configuracion + instalador."""
import tkinter as tk
from tkinter import messagebox, ttk

from . import config, install
from .i18n import tr
from .popup import Popup

LANGS = (("auto", "lang_auto"), ("es", None), ("en", None))
LANG_NAMES = {"es": "Español", "en": "English"}


class Configurator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.resizable(False, False)
        self.cfg = config.load()
        self.popup = Popup(self.root)
        self.frame = None
        self._build()
        self._tick()

    @property
    def lang(self):
        return config.resolve_language(self.cfg)

    def t(self, key):
        return tr(self.lang, key)

    # ---------- interfaz ----------
    def _build(self):
        if self.frame is not None:
            self.frame.destroy()
        self.root.title(self.t("title"))
        f = self.frame = ttk.Frame(self.root, padding=16)
        f.pack()

        # idioma
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text=self.t("language")).pack(side="left")
        self.lang_labels = [self.t("lang_auto") if c == "auto" else LANG_NAMES[c] for c, _ in LANGS]
        self.lang_var = tk.StringVar(value=self.lang_labels[[c for c, _ in LANGS].index(self.cfg["language"])])
        cb = ttk.Combobox(top, textvariable=self.lang_var, values=self.lang_labels,
                          state="readonly", width=14)
        cb.pack(side="right")
        cb.bind("<<ComboboxSelected>>", self._on_language)

        # aspecto
        look = ttk.LabelFrame(f, text=self.t("section_look"), padding=12)
        look.pack(fill="x", pady=(12, 0))
        look.columnconfigure(1, weight=1)

        ttk.Label(look, text=self.t("corner")).grid(row=0, column=0, sticky="w", pady=4)
        self.corner_labels = [self.t(c) for c in config.CORNERS]
        self.corner_var = tk.StringVar(value=self.t(self.cfg["corner"]))
        ttk.Combobox(look, textvariable=self.corner_var, values=self.corner_labels,
                     state="readonly", width=22).grid(row=0, column=1, columnspan=2, sticky="e")

        self.scale = self._slider(look, 1, "size", "scale", lambda v: f"{round(v * 100)}%")
        self.duration = self._slider(look, 2, "duration", "duration",
                                     lambda v: f"{v:.1f} {self.t('seconds')}")
        self.opacity = self._slider(look, 3, "opacity", "opacity", lambda v: f"{round(v * 100)}%")

        row = ttk.Frame(look)
        row.grid(row=4, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(row, text=self.t("preview"), command=self.preview).pack(side="left", padx=4)
        ttk.Button(row, text=self.t("save"), command=self.save).pack(side="left")
        self.msg = ttk.Label(look, foreground="#2e7d32")
        self.msg.grid(row=5, column=0, columnspan=3, sticky="w", pady=(6, 0))

        # sistema
        sysf = ttk.LabelFrame(f, text=self.t("section_system"), padding=12)
        sysf.pack(fill="x", pady=(12, 0))
        self.status = ttk.Label(sysf)
        self.status.pack(anchor="w")
        btns = ttk.Frame(sysf)
        btns.pack(fill="x", pady=(8, 0))
        self.btn_install = ttk.Button(btns, command=self.do_install)
        self.btn_install.pack(side="left")
        self.btn_uninstall = ttk.Button(btns, text=self.t("uninstall"), command=self.do_uninstall)
        self.btn_uninstall.pack(side="left", padx=6)
        self.btn_toggle = ttk.Button(btns, command=self.do_toggle)
        self.btn_toggle.pack(side="right")
        ttk.Label(f, text=self.t("hint"), foreground="#777").pack(anchor="w", pady=(10, 0))
        self._refresh_status()

    def _slider(self, parent, row, label_key, cfg_key, fmt):
        lo, hi = config.LIMITS[cfg_key]
        var = tk.DoubleVar(value=self.cfg[cfg_key])
        ttk.Label(parent, text=self.t(label_key)).grid(row=row, column=0, sticky="w", pady=4)
        out = ttk.Label(parent, width=7, anchor="e")
        out.grid(row=row, column=2, sticky="e")

        def update(_=None):
            out.config(text=fmt(var.get()))
        ttk.Scale(parent, from_=lo, to=hi, variable=var, length=170,
                  command=update).grid(row=row, column=1, padx=8, sticky="ew")
        update()
        return var

    # ---------- acciones ----------
    def _collect(self):
        cfg = dict(self.cfg)
        cfg["corner"] = config.CORNERS[self.corner_labels.index(self.corner_var.get())]
        cfg["scale"] = round(self.scale.get(), 2)
        cfg["duration"] = round(self.duration.get() * 2) / 2
        cfg["opacity"] = round(self.opacity.get(), 2)
        return config.sanitize(cfg)

    def _on_language(self, _):
        cfg = self._collect()
        cfg["language"] = LANGS[self.lang_labels.index(self.lang_var.get())][0]
        self.cfg = cfg
        config.save(cfg)
        self._build()

    def preview(self):
        self.popup.show(73, "discharging", self._collect())

    def save(self):
        self.cfg = self._collect()
        try:
            config.save(self.cfg)
            self.msg.config(text=self.t("saved"))
            self.preview()
        except OSError as e:
            messagebox.showerror(self.t("error"), str(e))

    def do_install(self):
        try:
            install.install()
            messagebox.showinfo(self.t("title"), self.t("install_done"))
        except Exception as e:
            messagebox.showerror(self.t("error"), str(e))
        self._refresh_status()

    def do_uninstall(self):
        remove_cfg = messagebox.askyesno(self.t("title"), self.t("uninstall_cfg"))
        try:
            install.uninstall(remove_config=remove_cfg)
            messagebox.showinfo(self.t("title"), self.t("uninstall_done"))
        except Exception as e:
            messagebox.showerror(self.t("error"), str(e))
        self._refresh_status()

    def do_toggle(self):
        if install.is_running():
            install.stop_background()
        else:
            install.start_background()
        self.root.after(800, self._refresh_status)

    def _refresh_status(self):
        installed, running = install.is_installed(), install.is_running()
        self.status.config(text=f"{self.t('installed' if installed else 'not_installed')}"
                                f" - {self.t('running' if running else 'stopped')}")
        self.btn_install.config(text=self.t("update" if installed else "install"))
        self.btn_uninstall.state(["!disabled" if installed else "disabled"])
        self.btn_toggle.config(text=self.t("stop" if running else "start"))

    def _tick(self):
        self._refresh_status()
        self.root.after(2000, self._tick)

    def run(self):
        self.root.mainloop()
