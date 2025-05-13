import tkinter as tk
from tkinter import ttk
import threading
import core.executar as exec_mod


class MacroStatusWindow:
    """
    Exibe o progresso de todas as threads de uma macro em duas colunas.

    Parâmetros
    ----------
    master : tk.Tk | tk.Toplevel
    on_close : callable | None
        Callback disparado quando a janela é destruída.
    thread_names : list[str] | None
        Lista de nomes de thread conhecidos *antes* da execução.
    """
    def __init__(self, master, on_close, thread_names=None):
        self.on_close = on_close
        self.win = tk.Toplevel(master)
        self.win.title("Status da Macro")
        self.win.geometry("620x400")
        self.win.attributes("-topmost", True)

        # --- contêiner principal em grid para duas colunas
        self.container = tk.Frame(self.win)
        self.container.pack(fill="both", expand=True, padx=10, pady=10)
        self.container.columnconfigure(0, weight=1)
        self.container.columnconfigure(1, weight=1)

        # armazenamento interno
        self._threads: dict[str, tuple[tk.Widget, ttk.Progressbar, tk.Label]] = {}
        self._stop_events: dict[str, threading.Event | None] = {}
        self._toggle_buttons: dict[str, tk.Button] = {}
        self._restart_callbacks: dict[str, callable] = {}
        self._threads_ever_created = False

        # pré-criar threads conhecidas
        if thread_names:
            for nm in thread_names:
                self._make_thread_widgets(nm)

        # botões gerais
        bf = tk.Frame(self.win)
        bf.pack(fill="x", padx=10, pady=(0, 10))
        self.pause_btn = tk.Button(
            bf, text="Pausar Todas", width=12, command=self.toggle_pause_all
        )
        self.pause_btn.pack(side="left", padx=5)
        tk.Button(bf, text="Stop Todas", width=12, command=self.stop_all).pack(side="right", padx=5)

        # ciclos de manutenção
        self.win.after(500, self._auto_close_check)
        self.win.after(500, self._cleanup_threads)

    def preload_threads(self, names: list[str]):
        """
        Cria (se ainda não existirem) os quadros para cada thread em 'names'.
        """
        for name in names:
            self._make_thread_widgets(name)

    # ---------- criação de widgets em duas colunas ----------
    def _make_thread_widgets(self, name: str):
        if not self.win.winfo_exists() or name in self._threads:
            return

        index = len(self._threads)
        row = index // 2
        col = index % 2

        frame = tk.LabelFrame(self.container, text=name, padx=5, pady=5)
        frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=(0, 8))
        self.container.rowconfigure(row, weight=0)

        pb = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
        pb.pack(fill="x", expand=True)

        lbl = tk.Label(
            frame, text="Último bloco: —", anchor="w",
            justify="left", font=("Segoe UI", 9)
        )
        lbl.pack(fill="x")

        # botão toggle Stop/Play
        btn = tk.Button(
            frame, text="Stop", width=6,
            command=lambda n=name: self._on_toggle_thread(n)
        )
        btn.pack(anchor="e", pady=(5, 0))

        # armazenar referências
        self._threads[name] = (frame, pb, lbl)
        self._toggle_buttons[name] = btn
        self._stop_events.setdefault(name, None)
        self._threads_ever_created = True

    # ---------- para registrar restart callbacks ----------
    def register_restart_callback(self, name: str, callback: callable):
        """
        Registra uma função que será chamada quando o usuário clicar em Play.
        assinatura callback(name: str, new_stop_event: threading.Event)
        """
        self._restart_callbacks[name] = callback

    # ---------- tratamento de Stop/Play por thread ----------
    def _on_toggle_thread(self, name: str):
        btn = self._toggle_buttons.get(name)
        evt = self._stop_events.get(name)
        if not btn:
            return

        if btn["text"] == "Stop":
            # parar thread
            if evt:
                evt.set()
            btn.config(text="Play")
        else:
            # restart thread
            new_evt = threading.Event()
            self._stop_events[name] = new_evt
            cb = self._restart_callbacks.get(name)
            if cb:
                cb(name, new_evt)
            btn.config(text="Stop")

    # ---------- API para execução ----------
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

    # ---------- ações dos botões gerais ----------
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
    # ---------- manutenção / encerramento ----------
    def _cleanup_threads(self):
        """Mantém a lista interna livre de widgets órfãos se a thread for encerrada."""
        if self.win.winfo_exists():
            # reagenda a si mesmo a cada 500 ms
            self.win.after(500, self._cleanup_threads)

    def _auto_close_check(self):
        # Enquanto houver ao menos um stop_event não setado → janela fica.
        if any(evt and not evt.is_set() for evt in self._stop_events.values()):
            self.win.after(500, self._auto_close_check)
        else:
            try:
                self.win.destroy()
            finally:
                if self.on_close:
                    self.on_close()
