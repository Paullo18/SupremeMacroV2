# gui/janela_se_variavel.py

import tkinter as tk
from tkinter import ttk, Toplevel, Frame, Label, Entry, Button, StringVar
from core import show_warning

def add_se_variavel(actions, update_list, tela, *, var_names=None, initial=None):
    """
    Abre janela para editar os parâmetros de um bloco 'Se Variável':
      - var_name: escolhido a partir de dropdown (ttk.Combobox) de var_names.
      - operator: um dos '=', '!=', '<', '<=', '>', '>='.
      - compare_value: valor literal (Entry).

    actions: lista (buffer) onde será feito .append({ ... }).
    update_list: callback para redesenhar o bloco após confirmação.
    tela: janela pai (Tk root).
    var_names: lista de strings com nomes de variáveis existentes na macro.
    initial: dicionário opcional com chaves "var_name", "operator", "compare_value".
    """
    win = Toplevel(tela)
    win.withdraw()
    win.transient(tela)
    win.title("Editar 'Se Variável'")
    win.resizable(False, False)
    win.grab_set()
    win.focus_force()

    # --- Nome da variável (Combobox) ---
    Label(win, text="Nome da variável:").grid(
        row=0, column=0, sticky="w", padx=10, pady=(10, 2)
    )
    # Se var_names for None, transforma em lista vazia
    lista_vars = var_names if var_names is not None else []
    var_name_var = StringVar(value=(initial.get("var_name", "") if initial else ""))
    combo_vars = ttk.Combobox(win, textvariable=var_name_var, state="readonly", width=28)
    combo_vars["values"] = lista_vars
    combo_vars.grid(row=0, column=1, padx=10, pady=(10, 2))

    # --- Operador de comparação (Combobox) ---
    Label(win, text="Operador:").grid(row=1, column=0, sticky="w", padx=10, pady=(2, 2))
    op_var = StringVar(value=(initial.get("operator", "=") if initial else "="))
    combo_ops = ttk.Combobox(win, textvariable=op_var, state="readonly", width=5)
    combo_ops["values"] = ["=", "!=", "<", "<=", ">", ">="]
    combo_ops.grid(row=1, column=1, sticky="w", padx=10, pady=(2, 2))

    # --- Valor para comparar (Entry) ---
    Label(win, text="Comparar com:").grid(
        row=2, column=0, sticky="w", padx=10, pady=(2, 10)
    )
    cmp_var = StringVar(value=(initial.get("compare_value", "") if initial else ""))
    Entry(win, textvariable=cmp_var, width=30).grid(
        row=2, column=1, padx=10, pady=(2, 10)
    )

    # --- Botões OK / Cancelar ---
    btn_frame = Frame(win)
    btn_frame.grid(row=3, column=0, columnspan=2, pady=(0, 10))

    def _confirm():
        vn = var_name_var.get().strip()
        op = op_var.get().strip()
        cv = cmp_var.get().strip()

        if not vn:
            show_warning("Aviso", "O nome da variável não pode ficar vazio.")
            return

        ac = {
            "var_name": vn,
            "operator": op,
            "compare_value": cv
        }
        actions.append(ac)
        if callable(update_list):
            update_list()
        win.destroy()

    Button(btn_frame, text="OK", width=10, command=_confirm).pack(side="left", padx=(0, 5))
    Button(btn_frame, text="Cancelar", width=10, command=win.destroy).pack(side="right", padx=(5, 0))

    # Centraliza a janela na tela
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
