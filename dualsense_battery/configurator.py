"""Ventana de configuracion + instalador."""
import tkinter as tk
from tkinter import colorchooser, messagebox, ttk

from . import config, install, monitors
from .i18n import tr
from .popup import Popup

LANG_CODES = ("auto", "es", "en")
LANG_NAMES = {"es": "Español", "en": "English"}


class ValueSlider:
    """Slider con un campo numerico editable a la derecha (los dos estan sincronizados)."""

    def __init__(self, parent, row, label, lo, hi, value, factor=1.0, step=1.0,
                 unit="", decimals=0):
        self.lo, self.hi, self.factor, self.decimals = lo, hi, factor, decimals
        self.var = tk.DoubleVar(value=value)
        self.text = tk.StringVar()
        self.label = ttk.Label(parent, text=label)
        self.label.grid(row=row, column=0, sticky="w", pady=4)
        self.scale = ttk.Scale(parent, from_=lo, to=hi, variable=self.var, length=170,
                               command=self._from_scale)
        self.scale.grid(row=row, column=1, padx=8, sticky="ew")
        box = ttk.Frame(parent)
        box.grid(row=row, column=2, sticky="e")
        self.spin = ttk.Spinbox(box, from_=lo * factor, to=hi * factor, increment=step,
                                textvariable=self.text, width=7, justify="left",
                                command=self._from_text)
        self.spin.pack(side="left")
        self.unit = ttk.Label(box, text=unit, width=2)
        self.unit.pack(side="left")
        self.spin.bind("<Return>", self._from_text)
        self.spin.bind("<FocusOut>", self._from_text)
        self._show()

    def _fmt(self, shown):
        return f"{shown:.{self.decimals}f}"

    def _show(self):
        self.text.set(self._fmt(self.var.get() * self.factor))

    def _from_scale(self, _=None):
        self._show()

    def _from_text(self, _=None):
        try:
            shown = float(self.text.get().replace(",", "."))
        except ValueError:
            self._show()  # entrada invalida: se vuelve al valor actual
            return
        value = min(self.hi, max(self.lo, shown / self.factor))
        self.var.set(value)
        self._show()

    def get(self):
        self._from_text()
        return self.var.get()

    def enable(self, on):
        for w in (self.scale, self.spin):
            w.state(["!disabled" if on else "disabled"])


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
    def _combo(self, parent, row, label_key, codes, labels, current, on_change=None, width=26):
        """Combobox que guarda codigos internos y muestra etiquetas traducidas."""
        ttk.Label(parent, text=self.t(label_key)).grid(row=row, column=0, sticky="w", pady=4)
        var = tk.StringVar(value=labels[codes.index(current)] if current in codes else labels[0])
        cb = ttk.Combobox(parent, textvariable=var, values=labels, state="readonly", width=width)
        cb.grid(row=row, column=1, columnspan=2, sticky="e")
        if on_change:
            cb.bind("<<ComboboxSelected>>", lambda _e: on_change())
        return lambda: codes[labels.index(var.get())]

    def _swatch(self, parent, row, label_key, key, col=1, span=2):
        if label_key:
            ttk.Label(parent, text=self.t(label_key)).grid(row=row, column=0, sticky="w", pady=4)
        holder = {"value": self.cfg[key]}
        btn = tk.Button(parent, text=self.t("pick"), width=14, relief="groove")

        def paint():
            c = holder["value"]
            r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
            btn.config(bg=c, activebackground=c, fg="#000" if (r * 299 + g * 587 + b * 114) > 128000 else "#fff")

        def choose():
            rgb, hexval = colorchooser.askcolor(color=holder["value"], parent=self.root)
            if hexval:
                holder["value"] = hexval
                paint()
                self.preview()
        btn.config(command=choose)
        btn.grid(row=row, column=col, columnspan=span, sticky="e")
        paint()
        return btn, lambda: holder["value"]

    def _build(self):
        if self.frame is not None:
            self.frame.destroy()
        self.root.title(self.t("title"))
        f = self.frame = ttk.Frame(self.root, padding=14)
        f.pack()

        top = ttk.Frame(f)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text=self.t("language")).pack(side="left")
        names = [self.t("lang_auto") if c == "auto" else LANG_NAMES[c] for c in LANG_CODES]
        self.get_lang = self._combo_inline(top, LANG_CODES, names, self.cfg["language"],
                                           self._on_language)

        nb = ttk.Notebook(f)
        nb.pack(fill="x")
        look = ttk.Frame(nb, padding=12)
        when = ttk.Frame(nb, padding=12)
        system = ttk.Frame(nb, padding=12)
        nb.add(look, text=self.t("tab_look"))
        nb.add(when, text=self.t("tab_when"))
        nb.add(system, text=self.t("tab_system"))
        for tab in (look, when):
            tab.columnconfigure(1, weight=1)
        self._build_look(look)
        self._build_when(when)
        self._build_system(system)

        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(10, 0))
        ttk.Button(bar, text=self.t("preview"), command=self.preview).pack(side="left")
        ttk.Button(bar, text=self.t("preview_charging"),
                   command=lambda: self.preview("charging")).pack(side="left", padx=6)
        ttk.Button(bar, text=self.t("save"), command=self.save).pack(side="right")
        self.msg = ttk.Label(f, foreground="#2e7d32")
        self.msg.pack(anchor="w", pady=(6, 0))
        ttk.Label(f, text=self.t("hint"), foreground="#777").pack(anchor="w")
        self._refresh_status()

    def _combo_inline(self, parent, codes, labels, current, on_change):
        var = tk.StringVar(value=labels[codes.index(current)])
        cb = ttk.Combobox(parent, textvariable=var, values=labels, state="readonly", width=16)
        cb.pack(side="right")
        cb.bind("<<ComboboxSelected>>", lambda _e: on_change())
        return lambda: codes[labels.index(var.get())]

    def _build_look(self, p):
        c = self.cfg
        t = self.t
        self.get_style = self._combo(p, 0, "style", config.STYLES,
                                     [t(f"style_{s}") for s in config.STYLES], c["style"], self.preview)
        self.get_theme = self._combo(p, 1, "theme", config.THEMES,
                                     [t(f"theme_{s}") for s in config.THEMES], c["theme"], self.preview)
        self.get_color_mode = self._combo(p, 2, "color_mode", config.COLOR_MODES,
                                          [t("color_level"), t("color_accent")], c["color_mode"],
                                          self._on_color_mode)
        self.accent_btn, self.get_accent = self._swatch(p, 3, "accent", "accent")

        self.charge_var = tk.BooleanVar(value=c["charging_color_on"])
        self.charge_chk = ttk.Checkbutton(p, text=t("charging_color_on"), variable=self.charge_var,
                                          command=self._on_charge_color)
        self.charge_chk.grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        self.charge_btn, self.get_charge_color = self._swatch(p, 4, None, "charging_color",
                                                              col=2, span=1)

        self.get_corner = self._combo(p, 5, "corner", config.CORNERS,
                                      [t(x) for x in config.CORNERS], c["corner"], self.preview)
        mons = monitors.list_monitors()
        codes = ["primary"] + list(range(1, len(mons) + 1))
        labels = [t("monitor_primary")] + [
            f"{i}  ({m['size'][0]}×{m['size'][1]}{', ' + t('monitor_primary').lower() if m['primary'] else ''})"
            for i, m in enumerate(mons, 1)]
        self.get_monitor = self._combo(p, 6, "monitor", codes, labels,
                                       c["monitor"] if c["monitor"] in codes else "primary",
                                       self.preview)
        lo, hi = config.LIMITS["scale"]
        self.scale = ValueSlider(p, 7, t("size"), lo, hi, c["scale"], factor=100, step=5, unit="%")
        lo, hi = config.LIMITS["opacity"]
        self.opacity = ValueSlider(p, 8, t("opacity"), lo, hi, c["opacity"], factor=100, step=5, unit="%")
        self._on_color_mode(preview=False)
        self._on_charge_color(preview=False)

    def _build_when(self, p):
        c, t = self.cfg, self.t
        ttk.Label(p, text=t("when_intro")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        self.trigger_vars = {}
        for i, key in enumerate(config.TRIGGERS, 1):
            var = tk.BooleanVar(value=c[key])
            self.trigger_vars[key] = var
            ttk.Checkbutton(p, text=t(key), variable=var,
                            command=self._on_triggers).grid(row=i, column=0, columnspan=3, sticky="w", pady=2)
        lo, hi = config.LIMITS["low_threshold"]
        self.threshold = ValueSlider(p, 5, t("low_threshold"), lo, hi, c["low_threshold"],
                                     step=5, unit="%")
        lo, hi = config.LIMITS["duration"]
        self.duration = ValueSlider(p, 6, t("duration"), lo, hi, c["duration"], step=0.5,
                                    unit="s", decimals=1)
        self._on_triggers()

    def _build_system(self, p):
        self.status = ttk.Label(p)
        self.status.pack(anchor="w")
        btns = ttk.Frame(p)
        btns.pack(fill="x", pady=(8, 0))
        self.btn_install = ttk.Button(btns, command=self.do_install)
        self.btn_install.pack(side="left")
        self.btn_uninstall = ttk.Button(btns, text=self.t("uninstall"), command=self.do_uninstall)
        self.btn_uninstall.pack(side="left", padx=6)
        self.btn_toggle = ttk.Button(btns, command=self.do_toggle)
        self.btn_toggle.pack(side="right")

    # ---------- dependencias entre controles ----------
    def _on_color_mode(self, preview=True):
        self.accent_btn.config(state="normal" if self.get_color_mode() == "accent" else "disabled")
        if preview:
            self.preview()

    def _on_charge_color(self, preview=True):
        self.charge_btn.config(state="normal" if self.charge_var.get() else "disabled")
        if preview:
            self.preview("charging")

    def _on_triggers(self):
        self.threshold.enable(self.trigger_vars["on_low"].get())

    # ---------- acciones ----------
    def _collect(self):
        cfg = dict(self.cfg)
        cfg.update(
            style=self.get_style(), theme=self.get_theme(), color_mode=self.get_color_mode(),
            accent=self.get_accent(), charging_color_on=self.charge_var.get(),
            charging_color=self.get_charge_color(), corner=self.get_corner(),
            monitor=self.get_monitor(), scale=round(self.scale.get(), 2),
            opacity=round(self.opacity.get(), 2),
            duration=round(self.duration.get() * 2) / 2,
            low_threshold=round(self.threshold.get()),
        )
        for key, var in self.trigger_vars.items():
            cfg[key] = var.get()
        return config.sanitize(cfg)

    def _on_language(self):
        cfg = self._collect()
        cfg["language"] = self.get_lang()
        self.cfg = config.sanitize(cfg)
        config.save(self.cfg)
        self._build()

    def preview(self, state="discharging"):
        self.popup.show(73, state, self._collect())

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
