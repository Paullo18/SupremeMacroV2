import tkinter as tk
from tkinter import ttk, messagebox


def add_texto(actions, update_list, tela, listbox=None):
    """Exibe uma janela para inserir texto que será digitado pela macro.

    Parâmetros
    ----------
    actions : list
        Lista usada pelo chamador para armazenar ações; a função
        acrescenta um dicionário com a estrutura
        ``{"type": "text", "content": <str>}``.
    update_list : Callable
        Callback invocado após adicionar a ação — normalmente refresca a
        Treeview/listbox do editor.
    tela : tk.Tk | tk.Toplevel
        Janela principal (root) — serve como `master` do Toplevel.
    listbox : tk.Listbox | None, opcional
        Fornecido em alguns fluxos para inserir o item na posição correta;
        não é obrigatório.
    """

    # ---------- janela modal ----------
    top = tk.Toplevel(tela)
    top.title("Adicionar Texto")
    top.resizable(False, False)
    top.grab_set()  # força modal

    # ---------- campo de entrada ----------
    ttk.Label(top, text="Texto a digitar:").pack(padx=10, pady=(10, 2), anchor="w")

    texto_var = tk.StringVar()
    entry = ttk.Entry(top, textvariable=texto_var, width=48)
    entry.pack(padx=10, pady=(0, 10), fill="x")
    entry.focus_set()

    # ---------- botões OK / Cancelar ----------
    frame_btn = ttk.Frame(top)
    frame_btn.pack(pady=(0, 10))

    def confirmar(*_):
        conteudo = texto_var.get()
        if not conteudo.strip():
            messagebox.showwarning("Campo vazio", "Digite algum texto antes de confirmar.")
            return

        # adiciona a ação e atualiza a interface do chamador
        actions.append({"type": "text", "content": conteudo})
        if callable(update_list):
            update_list()

        # se listbox foi fornecido, insere na posição adequada (mesma lógica usada por outras janelas)
        if listbox is not None:
            try:
                listbox.insert(tk.END, f'TXT: "{conteudo[:18]}…"' if len(conteudo) > 20 else f'TXT: "{conteudo}"')
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
