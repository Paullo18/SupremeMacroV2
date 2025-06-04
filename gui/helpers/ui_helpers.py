"""
Helpers de UI para FlowchartApp
"""

import tkinter as tk
from PIL import Image, ImageTk


def centralizar_janela(window, largura, altura):
    """
    Centraliza a janela 'window' na tela com as dimensões especificadas.

    Args:
        window: instância de tk.Tk ou tk.Toplevel.
        largura (int): largura desejada da janela.
        altura (int): altura desejada da janela.
    """
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    pos_x = (screen_w - largura) // 2
    pos_y = (screen_h - altura) // 2
    window.geometry(f"{largura}x{altura}+{pos_x}+{pos_y}")


def criar_menubar(root, menus):
    """
    Cria uma menubar a partir de um dicionário de configurações.

    Args:
        root: janela principal (tk.Tk).
        menus: dict com label->submenu, onde submenu é uma lista de tuples (label, callback) ou 'separator'.
    Returns:
        menubar: objeto tk.Menu configurado.
    """
    menubar = tk.Menu(root)
    for menu_label, items in menus.items():
        submenu = tk.Menu(menubar, tearoff=0)
        for item in items:
            if item == "separator":
                submenu.add_separator()
            else:
                label, cmd = item
                submenu.add_command(label=label, command=cmd)
        menubar.add_cascade(label=menu_label, menu=submenu)
    root.config(menu=menubar)
    return menubar


def carregar_icone(path, size):
    """
    Carrega e redimensiona uma imagem para uso como ícone.

    Args:
        path (str): caminho para o arquivo de imagem.
        size (tuple): (largura, altura) em pixels.
    Returns:
        PhotoImage: ícone pronto para usar em widgets.
    """
    img = Image.open(path).resize(size, Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def adicionar_botao(frame, icone, callback, **pack_opts):
    """
    Adiciona um Label com imagem ao frame e configura evento de clique.

    Args:
        frame: container Tkinter.
        icone: PhotoImage para exibir.
        callback: função a chamar no clique.
        pack_opts: opções para layout .pack() (e.g., side, padx, pady).
    Returns:
        widget: o Label criado.
    """
    btn = tk.Label(frame, image=icone, cursor="hand2")
    btn.pack(**pack_opts)
    btn.bind("<Button-1>", callback)
    return btn
