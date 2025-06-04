# gui/telegram_command.py

import tkinter as tk
from tkinter import ttk
from core import show_warning

def add_telegram_command(actions, update_list, tela, listbox=None, *, initial=None):
    top = tk.Toplevel(tela)
    top.withdraw()
    top.transient(tela)
    top.title("Adicionar Remote Control")
    top.resizable(False, False)

    # Nome do bloco
    ttk.Label(top, text="Nome do bloco:").pack(anchor="w", padx=10, pady=(10, 0))
    name_var = tk.StringVar(value=(initial.get("name","") if initial else ""))
    ttk.Entry(top, textvariable=name_var, width=48).pack(fill="x", padx=10, pady=(0,10))

    # Comando esperado (já pré‑povoa com '/')
    ttk.Label(top, text="Comando esperado (ex: /continuar):")\
       .pack(anchor="w", padx=10, pady=(0,2))
    # monta valor inicial com '/' garantido
    initial_cmd = initial.get("command", "") if initial else ""
    if not initial_cmd.startswith("/"):
        initial_cmd = "/" + initial_cmd
    cmd_var = tk.StringVar(value=initial_cmd)
    ttk.Entry(top, textvariable=cmd_var, width=48).pack(fill="x", padx=10, pady=(0,10))

    # Botões
    btn_frame = ttk.Frame(top)
    ttk.Button(btn_frame, text="Cancelar", command=top.destroy)\
        .pack(side="left", padx=5)
    def confirmar():
        nome = name_var.get().strip()
        cmd  = cmd_var.get().strip()
        # garante que o comando comece com '/'
        if not cmd.startswith("/"):
            cmd = "/" + cmd
        if not nome:
            show_warning("Campo vazio", "Defina um nome para o bloco.")
            return
        if not cmd:
            show_warning("Campo vazio", "Defina o comando esperado.")
            return
        ac = {"type":"telegram_command", "name":nome, "command":cmd}
        if initial is not None:
            initial.clear()
            initial.update(ac)
        else:
            actions.append(ac)
        if callable(update_list):
            update_list()
        # atualiza preview na lista, se houver
        if listbox is not None:
            preview = f"RC: '{nome}' → {cmd}"
            sel = listbox.curselection() if initial else None
            if sel:
                idx = sel[0]
                listbox.delete(idx)
                listbox.insert(idx, preview)
            else:
                listbox.insert(tk.END, preview)
        top.destroy()

    ttk.Button(btn_frame, text="OK", command=confirmar).pack(side="left")
    btn_frame.pack(side="bottom", fill="x", padx=10, pady=(10,10))

    # — Bindings para Enter/Esc —
    # Enter deve confirmar
    top.bind("<Return>", lambda e: (confirmar() or "break"))
    # Esc deve cancelar
    top.bind("<Escape>", lambda e: (top.destroy()  or "break"))

    # Centraliza
    top.update_idletasks()
    x = tela.winfo_rootx() + (tela.winfo_width() - top.winfo_width())//2
    y = tela.winfo_rooty() + (tela.winfo_height() - top.winfo_height())//2
    top.geometry(f"+{x}+{y}")
    top.deiconify()
    top.focus_force()
