import tkinter as tk
from tkinter import Toplevel, IntVar, StringVar, Label, Entry, Radiobutton, Button
from core.inserir import inserir_acao


def add_loop(actions, update_list, tela, *, initial=None):
    # janela modal
    win = Toplevel(tela)
    win.withdraw()
    win.transient(tela)
    win.title("Adicionar Loop")
    win.resizable(False, False)

    # --- Campo editável para label customizada do bloco -----------
    Label(win, text="Nome do bloco:").pack(pady=(10, 0), anchor='w', padx=10)
    name_var = StringVar(value=initial.get('name', '') if initial else '')
    Entry(win, textvariable=name_var).pack(fill='x', padx=10, pady=(0, 10))

    # --- Escolha de tipo de loop -----------------------------------
    tipo = StringVar(value=initial.get('mode', 'quantidade') if initial else 'quantidade')
    quantidade = IntVar(value=initial.get('count', 1) if initial and initial.get('mode')=='quantidade' else 1)

    Radiobutton(win, text="Loop com quantidade fixa", variable=tipo, value="quantidade").pack(anchor="w", padx=10)
    Entry(win, textvariable=quantidade).pack(padx=10, pady=(0, 10))
    Radiobutton(win, text="Loop infinito", variable=tipo, value="infinito").pack(anchor="w", padx=10)

    # --- Função de confirmação -------------------------------------
    def confirmar():
        if tipo.get() == "quantidade":
            ac = {"type": "loopstart", "mode": "quantidade", "count": quantidade.get()}
        else:
            ac = {"type": "loopstart", "mode": "infinito"}
        nome = name_var.get().strip()
        if nome:
            ac["name"] = nome
        actions.append(ac)
        update_list()
        win.destroy()

    # --- Botões -----------------------------------------------
    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=10)
    Button(btn_frame, text="Confirmar", command=confirmar).pack(side='left', padx=5)
    Button(btn_frame, text="Cancelar", command=win.destroy).pack(side='left')

    # --- Atalhos e centralização ----------------------------------
    win.update_idletasks()
    px, py = tela.winfo_rootx(), tela.winfo_rooty()
    pw, ph = tela.winfo_width(), tela.winfo_height()
    w, h = win.winfo_width(), win.winfo_height()
    win.geometry(f"{w}x{h}+{px + (pw - w)//2}+{py + (ph - h)//2}")
    win.deiconify()
    win.minsize(w, h)
    win.maxsize(w, h)
    win.focus_force()
    win.bind("<Escape>", lambda e: win.destroy())
    win.bind("<Return>", lambda e: confirmar())
