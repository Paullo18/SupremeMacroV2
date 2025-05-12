import os
import tkinter as tk
from tkinter import Toplevel, Label, Entry, Button, filedialog, messagebox


def add_run_macro(actions, update_list, tela, initial=None):
    """
    Diálogo para configurar o bloco "Run Macro".
    - actions: lista onde vamos armazenar {'type':'run_macro', 'path':...}
    - update_list: callback para atualizar o bloco após seleção
    - tela: janela pai
    - initial: ação anterior (pode conter 'path')
    """
    # janela modal
    win = Toplevel(tela)
    win.title("Configurar Run Macro")
    win.grab_set()

    # caminho selecionado
    selected_path = initial.get('path') if initial else None

    # label e entry para exibir caminho
    Label(win, text="Arquivo da Macro:").grid(row=0, column=0, padx=10, pady=10)
    path_var = tk.StringVar(value=selected_path or "")
    entry = Entry(win, textvariable=path_var, width=40)
    entry.grid(row=0, column=1, padx=10)

    def on_select():
        path = filedialog.askopenfilename(
            parent=win,
            title="Selecione uma macro (.json)",
            filetypes=[("JSON", "*.json")],
            initialdir=os.path.abspath("Macros")
        )
        if path:
            path_var.set(path)

    def on_open():
        path = path_var.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showerror("Erro", "Arquivo inválido ou não selecionado.")
            return
        # libera grab e oculta janela de configuração
        win.grab_release()
        win.withdraw()
        # Abre uma nova janela do editor para esta macro
        from main import FlowchartApp
        new_root = Toplevel(tela)
        new_root.transient(tela)
        new_root.lift()
        new_root.focus_force()
        # Inicia o editor na nova janela
        app = FlowchartApp(new_root)
        app._acao_carregar(path)

        # Função para restaurar a janela de configuração quando fechar o editor
        def on_child_close():
            new_root.destroy()
            win.deiconify()
            win.grab_set()
        new_root.protocol("WM_DELETE_WINDOW", on_child_close)

    def on_ok():
        path = path_var.get().strip()
        if not path:
            messagebox.showerror("Erro", "Selecione um arquivo antes de confirmar.")
            return
        ac = {'type': 'run_macro', 'path': path}
        # grava na lista de actions (para undo/refazer)
        actions.clear()
        actions.append(ac)
        update_list()
        win.destroy()

    # botões
    btn_select = Button(win, text="Selecionar…", command=on_select)
    btn_select.grid(row=1, column=0, pady=10)
    btn_open = Button(win, text="Abrir Macro", command=on_open)
    btn_open.grid(row=1, column=1)
    btn_ok = Button(win, text="OK", command=on_ok)
    btn_ok.grid(row=2, column=0, columnspan=2, pady=10)

    win.transient(tela)
    # centraliza a janela no meio da janela principal
    win.update_idletasks()
    x = tela.winfo_rootx() + (tela.winfo_width() // 2) - (win.winfo_width() // 2)
    y = tela.winfo_rooty() + (tela.winfo_height() // 2) - (win.winfo_height() // 2)
    win.geometry(f"+{x}+{y}")
    win.wait_window()