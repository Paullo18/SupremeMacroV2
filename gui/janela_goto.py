import tkinter as tk
from tkinter import Toplevel, Frame, StringVar, Label, Button, ttk
from core import show_warning

def add_goto(actions, update_list, tela, *, initial=None, labels_existentes=None):
    """
    Janela customizada para definir destino de GOTO usando lista de Labels existentes.
    """
    win = Toplevel(tela)
    win.withdraw()
    win.transient(tela)
    win.title("Adicionar GOTO")
    win.resizable(False, False)
    win.grab_set()
    win.focus_force()

    if labels_existentes is None:
        labels_existentes = []

    # --- Campo editável para nome do bloco (normal) ---
    Label(win, text="Nome do bloco:").grid(
        row=0, column=0, sticky="w", padx=5, pady=5
    )
    name_var = StringVar(value=initial.get("name", "") if initial else "")
    tk.Entry(win, textvariable=name_var, width=30).grid(
        row=0, column=1, padx=5, pady=5
    )

    # --- Campo de destino GOTO agora como Combobox ---
    Label(win, text="Ir para qual Label:").grid(
        row=1, column=0, sticky="w", padx=5, pady=5
    )
    label_var = StringVar(value=initial.get("label", "") if initial else "")
    combobox = ttk.Combobox(win, textvariable=label_var, values=labels_existentes, state="readonly", width=28)
    combobox.grid(row=1, column=1, padx=5, pady=5)

    if labels_existentes:
        destino_inicial = initial.get('label', '') if initial else ''
        if destino_inicial in labels_existentes:
            combobox.set(destino_inicial)  # seleciona a label anterior se existir
        else:
            combobox.current(0)  # senão, seleciona a primeira

    # --- Função de confirmação ---
    def _confirm():
        destino = label_var.get().strip()
        if not destino:
            show_warning("Campo vazio", "Escolha a Label de destino.")
            return
        ac = {"type": "goto", "label": destino}
        nome = name_var.get().strip()
        if nome:
            ac["name"] = nome
        actions.append(ac)
        if callable(update_list):
            update_list()
        win.destroy()

    # --- Botões OK / Cancelar ---
    btn_frame = Frame(win)
    btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
    Button(btn_frame, text="OK", width=10, command=_confirm).pack(side="left", padx=5)
    Button(btn_frame, text="Cancelar", width=10, command=win.destroy).pack(side="left")

    # --- Centralizar, foco e atalhos ---
    win.update_idletasks()
    px, py = tela.winfo_rootx(), tela.winfo_rooty()
    pw, ph = tela.winfo_width(), tela.winfo_height()
    w, h = win.winfo_width(), win.winfo_height()
    x = px + (pw - w) // 2
    y = py + (ph - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")
    win.deiconify()
    win.focus_force()
    win.bind("<Escape>", lambda e: win.destroy())
    win.bind("<Return>", lambda e: _confirm())
