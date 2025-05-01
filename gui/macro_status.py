# ===== arquivo: gui/macro_status.py =====
import tkinter as tk
from tkinter import ttk
import threading
import core.executar as exec_mod

class MacroStatusWindow:
    def __init__(self, master, on_close):
        self.on_close = on_close
        # janela flutuante sempre-à-frente
        self.win = tk.Toplevel(master)
        self.win.title("Status da Macro")
        self.win.geometry("420x300")
        self.win.resizable(False, False)  # impede redimensionamento
        self.win.attributes("-topmost", True)
        self.win.attributes("-toolwindow", True)

        # permitir arrastar
        self.win.bind("<ButtonPress-1>", self._start_move)
        self.win.bind("<B1-Motion>",    self._on_move)

        # container para barras e labels
        self.container = tk.Frame(self.win)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)

        # mapa thread_name → (frame, progressbar, label)
        self._threads = {}
        # mapa thread_name → stop_event
        self._stop_events = {}
        # só fecha após ter exibido ao menos um widget
        self._threads_ever_created = False

        # inicia limpeza periódica de threads
        self.win.after(500, self._cleanup_threads)
        # inicia check de auto-close
        self.win.after(500, self._auto_close_check)

        # botões gerais
        btn_frame = tk.Frame(self.win)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.pause_btn = tk.Button(
            btn_frame, text="Pausar Todas", width=12,
            command=self.toggle_pause_all
        )
        self.pause_btn.pack(side="left", padx=5)
        tk.Button(
            btn_frame, text="Stop Todas", width=12,
            command=self.stop_all
        ).pack(side="right", padx=5)

    def _auto_close_check(self):
        # só fecha se já tiver mostrado algo e não houver mais threads
        if self._threads_ever_created and not self._threads and not any(
            t.name.startswith("Thread") for t in threading.enumerate()
        ):
            try:
                self.win.destroy()
            except:
                pass
            if self.on_close:
                self.on_close()
            return
        self.win.after(500, self._auto_close_check)

    def _start_move(self, e):
        self._drag_x = e.x; self._drag_y = e.y

    def _on_move(self, e):
        dx = e.x - self._drag_x; dy = e.y - self._drag_y
        x = self.win.winfo_x() + dx; y = self.win.winfo_y() + dy
        self.win.geometry(f"+{x}+{y}")

    def _make_thread_widgets(self, name):
        # ignora se a janela já foi fechada
        if not self.win.winfo_exists():
            return
        if name in self._threads:
            return

        frame = tk.LabelFrame(self.container, text=name, padx=5, pady=5)
        frame.pack(fill="x", padx=5, pady=(0, 8))
        pb = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
        pb.pack(fill="x", expand=True)
        lbl = tk.Label(frame, text="Último bloco: —", anchor="w", justify="left", font=("Segoe UI", 9))
        lbl.pack(fill="x")
        stop_btn = tk.Button(frame, text="Stop",
                             command=lambda: self._stop_thread(name))
        stop_btn.pack(anchor="e", pady=(5, 0))

        self._threads[name] = (frame, pb, lbl)
        self._stop_events.setdefault(name, None)
        self._threads_ever_created = True

    def register_stop_event(self, name, event):
        self._stop_events[name] = event

    def _stop_thread(self, name):
        evt = self._stop_events.get(name)
        if evt:
            evt.set()

    def update_progress(self, name, step, total):
        # ignora callbacks após janela fechada
        if not self.win.winfo_exists():
            return
        if name not in self._threads:
            self._make_thread_widgets(name)
        frame, pb, lbl = self._threads[name]
        # define máximo e valor atual
        try:
            pb["maximum"] = total
            pb["value"]   = step
        except:
            # fallback para porcentagem
            pct = int((step/total)*100) if total else 100
            pb["value"] = pct
        # força redraw completo
        self.win.update()

    def update_block(self, name, text):
        if not self.win.winfo_exists():
            return
        if name not in self._threads:
            self._make_thread_widgets(name)
        frame, pb, lbl = self._threads[name]
        lbl.config(text=f"Último bloco: {text}")
        self.win.update()

    def toggle_pause_all(self):
        exec_mod.macro_pausar = not exec_mod.macro_pausar
        if exec_mod.macro_pausar:
            self.pause_btn.config(text="Retomar Todas")
        else:
            self.pause_btn.config(text="Pausar Todas")

    def stop_all(self):
        exec_mod.macro_parar = True
        # sinaliza stop para todas as threads registradas
        for evt in self._stop_events.values():
            if evt:
                evt.set()
        try:
            self.win.destroy()
        except:
            pass
        if self.on_close:
            self.on_close()

    def _cleanup_threads(self):
        # ignora se a janela já foi fechada
        if not self.win.winfo_exists():
            return
        ativa = {t.name for t in threading.enumerate()}
        for name, (frame, pb, lbl) in list(self._threads.items()):
            # ignora entradas sem nome para evitar erro de NoneType
            if name is None:
                continue
            # considera o widget inativo se nenhum thread vivo corresponder ao prefixo
            if not any(tname.startswith(name) for tname in ativa):
                frame.destroy()
                del self._threads[name]
                self._stop_events.pop(name, None)
        self.win.after(500, self._cleanup_threads)
