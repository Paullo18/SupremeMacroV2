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
        self.win.geometry("360x260+50+50")
        self.win.attributes("-topmost", True)
        self.win.attributes("-toolwindow", True)

        self._idle_counter = 0
        self.win.after(100, self._auto_close_check)

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

        # inicia limpeza periódica de threads (intervalo curto para remoção quase em tempo real)
        self.win.after(50, self._cleanup_threads)

        # botões gerais
        btn_frame = tk.Frame(self.win)
        btn_frame.pack(fill="x", pady=(0,5))
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
        # sem threads vivas → fecha imediatamente
        if not self._threads:
            self.on_close()
            return
        # se existir loop que reabre threads, considere deixar este recurso desligado
        self.win.after(500, self._auto_close_check)

    def _start_move(self, e):
        self._drag_x = e.x; self._drag_y = e.y
    def _on_move(self, e):
        dx = e.x - self._drag_x; dy = e.y - self._drag_y
        x = self.win.winfo_x() + dx; y = self.win.winfo_y() + dy
        self.win.geometry(f"+{x}+{y}")

    def _make_thread_widgets(self, name):
        frame = tk.LabelFrame(self.container, text=name, padx=5, pady=5)
        frame.pack(fill="x", pady=5)
        pb = ttk.Progressbar(frame, length=200, mode="determinate")
        pb.pack(side="left", padx=(0,10))
        lbl = tk.Label(frame, text="Último bloco: —")
        lbl.pack(side="left")
        stop_btn = tk.Button(frame, text="Stop", command=lambda: self._stop_thread(name))
        stop_btn.pack(side="right", padx=5)
        self._threads[name] = (frame, pb, lbl)
        self._stop_events.setdefault(name, None)

    def register_stop_event(self, name, event):
        self._stop_events[name] = event

    def _stop_thread(self, name):
        evt = self._stop_events.get(name)
        if evt:
            evt.set()

    def update_progress(self, name, step, total):
        # filtra apenas threads de execução (_run_branch)
        if '_run_branch' not in name:
            return
        if name not in self._threads:
            self._make_thread_widgets(name)
        _, pb, _ = self._threads[name]
        pct = int(step/total*100)
        pb['value'] = pct
        self.win.update_idletasks()

    def update_block(self, name, text):
        # filtra apenas threads de execução (_run_branch)
        if '_run_branch' not in name:
            return
        if name not in self._threads:
            self._make_thread_widgets(name)
        _, _, lbl = self._threads[name]
        lbl.config(text=text)
        self.win.update_idletasks()

    def toggle_pause_all(self):
        exec_mod.macro_pausar = not exec_mod.macro_pausar
        if exec_mod.macro_pausar:
            self.pause_btn.config(text="Retomar Todas")
        else:
            self.pause_btn.config(text="Pausar Todas")

    def stop_all(self):
        exec_mod.macro_parar = True
        self.win.destroy()
        self.on_close()

    def _cleanup_threads(self):
        ativa = {t.name for t in threading.enumerate()}
        for name, (frame, _, _) in list(self._threads.items()):
            if name not in ativa:
                frame.destroy()
                del self._threads[name]
                if name in self._stop_events:
                    del self._stop_events[name]
        # agenda próxima limpeza com intervalo curto
        self.win.after(50, self._cleanup_threads)

