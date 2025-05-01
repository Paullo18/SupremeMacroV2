from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Any

from PIL import Image, ImageTk

# --- diretório base do projeto + pasta de ícones -----------------
BASE_DIR = Path(__file__).resolve().parents[1]
ICON_DIR = BASE_DIR / "assets" / "icons"


def criar_botao(
    *,
    parent: tk.Widget,
    img_file: str,
    callback,
    bg: str = "#ffffff",
    store_dict: dict | None = None,
    key: str | None = None,
    size: tuple[int, int] = (112, 40),
    **pack_opts: Any,              # ← aceita side="left", fill="x", …
) -> tk.Label | None:
    """
    Cria um label-botão com ícone PNG.

    Parameters
    ----------
    parent      : widget onde o botão será adicionado.
    img_file    : nome do PNG dentro de `assets/icons/`.
    callback    : função chamada no <Button-1>.
    bg          : cor de fundo.
    store_dict  : dict onde guardar a PhotoImage (evita GC).
    key         : chave usada nesse dict (default = img_file).
    size        : (largura, altura) em px.
    **pack_opts : opções adicionais para `pack()`, p.ex. side="left".
    """
    caminho = ICON_DIR / img_file
    if not caminho.exists():
        print(f"[Aviso] Ícone '{img_file}' não encontrado em {caminho}.")
        return None

    pil_img = Image.open(caminho).resize(size, Image.Resampling.LANCZOS)
    tk_img  = ImageTk.PhotoImage(pil_img)

    # preserva a referência da imagem em store_dict ou dentro do parent
    if store_dict is not None:
        store_dict[key or img_file] = tk_img
    else:
        parent._img_ref = getattr(parent, "_img_ref", []) + [tk_img]

    lbl = tk.Label(parent, image=tk_img, cursor="hand2", bg=bg)
    lbl.bind("<Button-1>", callback)

    # padding default + extras vindos de **pack_opts
    lbl.pack(padx=5, pady=5, **pack_opts)
    return lbl
