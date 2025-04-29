import tkinter as tk
from tkinter import Toplevel, Frame, StringVar, Label, Entry, Button, messagebox


def add_goto(actions, update_list, tela, *, initial=None):
    """
    Janela customizada para definir destino de GOTO e label do bloco.
    """
    win = Toplevel(tela)
    win.withdraw()
    win.transient(tela)
    win.title("Adicionar GOTO")
    win.resizable(False, False)

    # --- Campo editável para label do bloco -----------------------
    Label(win, text="Nome do bloco:").grid(
        row=0, column=0, sticky="w", padx=5, pady=5
    )
    name_var = StringVar(value=initial.get("name", "") if initial else "")
    Entry(win, textvariable=name_var, width=30).grid(
        row=0, column=1, padx=5, pady=5
    )

    # --- Campo para destino GOTO -----------------------------------
    Label(win, text="Ir para qual Label:").grid(
        row=1, column=0, sticky="w", padx=5, pady=5
    )
    label_var = StringVar(value=initial.get("label", "") if initial else "")
    Entry(win, textvariable=label_var, width=30).grid(
        row=1, column=1, padx=5, pady=5
    )

    # --- Função de confirmação -------------------------------------
    def _confirm():
        destino = label_var.get().strip()
        if not destino:
            messagebox.showwarning("Campo vazio", "Digite o nome da Label de destino.")
            return
        ac = {"type": "goto", "label": destino}
        nome = name_var.get().strip()
        if nome:
            ac["name"] = nome
        actions.append(ac)
        if callable(update_list):
            update_list()
        win.destroy()

    # --- Botões OK / Cancelar --------------------------------------
    btn_frame = Frame(win)
    btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
    Button(btn_frame, text="OK", width=10, command=_confirm).pack(side="left", padx=5)
    Button(btn_frame, text="Cancelar", width=10, command=win.destroy).pack(side="left")

    # --- Centralizar, foco e atalhos --------------------------------
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
