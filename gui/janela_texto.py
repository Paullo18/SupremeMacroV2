import tkinter as tk
from tkinter import ttk, messagebox


def add_texto(actions, update_list, tela, listbox=None, *, initial=None):
    # cria janela modal
    top = tk.Toplevel(tela)
    top.withdraw()
    top.transient(tela)
    top.title("Adicionar Texto")
    top.resizable(False, False)

    # --- Campo editável para label customizada do bloco -----------
    ttk.Label(top, text="Nome do bloco:").pack(anchor="w", padx=10, pady=(10, 0))
    name_var = tk.StringVar(value=initial.get('name', '') if initial else '')
    ttk.Entry(top, textvariable=name_var, width=48).pack(fill="x", padx=10, pady=(0, 10))

    # --- Campo de entrada de texto ---------------------------------
    ttk.Label(top, text="Texto a digitar:").pack(padx=10, pady=(0, 2), anchor="w")
    texto_var = tk.StringVar(value=initial.get('content', '') if initial else '')
    entry = ttk.Entry(top, textvariable=texto_var, width=48)
    entry.pack(padx=10, pady=(0, 10), fill="x")
    entry.focus_set()

    # --- Botões OK / Cancelar --------------------------------------
    frame_btn = ttk.Frame(top)
    frame_btn.pack(pady=(0, 10))

    def confirmar(*_):
        conteudo = texto_var.get()
        if not conteudo.strip():
            messagebox.showwarning("Campo vazio", "Digite algum texto antes de confirmar.")
            return
        ac = {"type": "text", "content": conteudo}
        nome = name_var.get().strip()
        if nome:
            ac["name"] = nome
        actions.append(ac)
        if callable(update_list):
            update_list()
        if listbox is not None:
            try:
                preview = (
                    f'TXT: "{conteudo[:18]}…"' if len(conteudo) > 20
                    else f'TXT: "{conteudo}"'
                )
                listbox.insert(tk.END, preview)
            except Exception:
                pass
        top.destroy()

    def cancelar(*_):
        top.destroy()

    ttk.Button(frame_btn, text="OK", command=confirmar).pack(side=tk.LEFT, padx=5)
    ttk.Button(frame_btn, text="Cancelar", command=cancelar).pack(side=tk.LEFT, padx=5)

    # atalhos de teclado
    top.bind("<Return>", confirmar)
    top.bind("<Escape>", cancelar)

    # --- Centralizar, bloquear resize, foco ------------------------
    top.update_idletasks()
    px, py = tela.winfo_rootx(), tela.winfo_rooty()
    pw, ph = tela.winfo_width(), tela.winfo_height()
    w, h = top.winfo_width(), top.winfo_height()
    x = px + (pw - w) // 2
    y = py + (ph - h) // 2
    top.geometry(f"{w}x{h}+{x}+{y}")
    top.deiconify()
    top.minsize(w, h)
    top.maxsize(w, h)
    top.focus_force()
