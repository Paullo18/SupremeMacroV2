# ===== arquivo: gui/macro_status.py =====
import tkinter as tk
from tkinter import ttk
import threading
import core.executar as exec_mod


class MacroStatusWindow:
    """
    Exibe o progresso de todas as threads de uma macro.

    Parâmetros
    ----------
    master : tk.Tk | tk.Toplevel
    on_close : callable | None
        Callback disparado quando a janela é destruída.
    thread_names : list[str] | None
        Lista de nomes de thread conhecidos *antes* da execução.
        (Ex.: ['Thread Principal', 'ChecaSinal', 'AtualizaChart' ...])
    """
    def __init__(self, master, on_close, thread_names=None):
        self.on_close = on_close
        self.win = tk.Toplevel(master)
        self.win.title("Status da Macro")
        self.win.geometry("420x300")
        self.win.attributes("-topmost", True)
        # --- contêiner principal
        self.container = tk.Frame(self.win)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)

        # mapas auxiliares
        self._threads: dict[str, tuple[tk.Widget, ttk.Progressbar, tk.Label]] = {}
        self._stop_events: dict[str, threading.Event | None] = {}
        self._threads_ever_created = False

        # cria widgets para nomes já conhecidos
        if thread_names:
            for nm in thread_names:
                self._make_thread_widgets(nm)

        # botões de controle geral
        bf = tk.Frame(self.win)
        bf.pack(fill="x", padx=10, pady=(0, 10))
        self.pause_btn = tk.Button(
            bf, text="Pausar Todas", width=12, command=self.toggle_pause_all
        )
        self.pause_btn.pack(side="left", padx=5)
        tk.Button(bf, text="Stop Todas", width=12, command=self.stop_all
                  ).pack(side="right", padx=5)

        # timers
        self.win.after(500, self._auto_close_check)
        self.win.after(500, self._cleanup_threads)

    # ---------- movimentação da janela ----------
    def _start_move(self, e):
        self._drag_x, self._drag_y = e.x, e.y

    def _on_move(self, e):
        dx, dy = e.x - self._drag_x, e.y - self._drag_y
        self.win.geometry(f"+{self.win.winfo_x() + dx}+{self.win.winfo_y() + dy}")

    # ---------- criação de widgets por thread ----------
    def _make_thread_widgets(self, name: str):
        if not self.win.winfo_exists():
            return
        if name in self._threads:        # já existe, não recria
            return

        frame = tk.LabelFrame(self.container, text=name, padx=5, pady=5)
        frame.pack(fill="x", padx=5, pady=(0, 8))

        pb = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
        pb.pack(fill="x", expand=True)

        lbl = tk.Label(
            frame, text="Último bloco: —", anchor="w",
            justify="left", font=("Segoe UI", 9)
        )
        lbl.pack(fill="x")

        tk.Button(
            frame, text="Stop", command=lambda: self._stop_thread(name)
        ).pack(anchor="e", pady=(5, 0))

        self._threads[name] = (frame, pb, lbl)
        self._stop_events.setdefault(name, None)
        self._threads_ever_created = True  # já tem algo na tela

        # ---------- API extra: pré-criar threads ----------
    def preload_threads(self, names: list[str]):
        """
        Cria (se ainda não existirem) os quadros de todas as threads indicadas.
        Pode ser chamado antes mesmo de a execução começar.
        """
        for n in names:
            self._make_thread_widgets(n)

    # ---------- API pública usada pela execução ----------
    def register_stop_event(self, name: str, event: threading.Event):
        self._stop_events[name] = event

    def update_progress(self, name: str, step: int, total: int):
        if not self.win.winfo_exists():
            return
        if name not in self._threads:
            self._make_thread_widgets(name)

        _, pb, _ = self._threads[name]
        try:
            pb["maximum"] = total
            pb["value"] = step
        except tk.TclError:
            pct = int((step / total) * 100) if total else 100
            pb["value"] = pct
        self.win.update_idletasks()

    def update_block(self, name: str, text: str):
        if not self.win.winfo_exists():
            return
        if name not in self._threads:
            self._make_thread_widgets(name)

        _, _, lbl = self._threads[name]
        lbl.config(text=f"Último bloco: {text}")
        self.win.update_idletasks()

    # ---------- ações dos botões ----------
    def _stop_thread(self, name: str):
        evt = self._stop_events.get(name)
        if evt:
            evt.set()

    def toggle_pause_all(self):
        exec_mod.macro_pausar = not exec_mod.macro_pausar
        self.pause_btn.config(
            text="Retomar Todas" if exec_mod.macro_pausar else "Pausar Todas"
        )

    def stop_all(self):
        exec_mod.macro_parar = True
        for evt in self._stop_events.values():
            if evt:
                evt.set()
        try:
            self.win.destroy()
        finally:
            if self.on_close:
                self.on_close()

    # ---------- manutenção / encerramento ----------
    def _cleanup_threads(self):
        """
        Mantém o loop vivo para eventual uso futuro,
        mas **não** remove mais widgets de threads encerradas.
        """
        if self.win.winfo_exists():
            self.win.after(500, self._cleanup_threads)

    def _auto_close_check(self):
        # fecha só se já mostrou algo E não existirem mais threads vivas
        if self._threads_ever_created and not any(
            t.name.startswith("Thread") for t in threading.enumerate()
        ):
            try:
                self.win.destroy()
            finally:
                if self.on_close:
                    self.on_close()
            return
        self.win.after(500, self._auto_close_check)
