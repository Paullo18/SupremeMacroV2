"""
utils.area_select
-----------------
Função utilitária para selecionar uma área retangular na tela.

Exemplo de uso:
    from utils.area_select import select_area
    box = select_area()            # (x1, y1, x2, y2)  |  None se Esc / cancelar
"""

import tkinter as tk


def select_area(parent=None,
                alpha: float = 0.30,
                outline: str = "red",
                line_width: int = 2):
    """Abre um overlay translúcido em tela-cheia; retorna
       (x1, y1, x2, y2) ou None se o usuário cancelar com Esc."""
    result = {"coords": None}

    # --- Janela overlay -------------------------------------------
    # se houver janela chamadora, usamos um Toplevel; caso contrário,
    # caímos no fallback de criar um Tk independente.
    if parent is not None:
        root = tk.Toplevel(parent)
    else:
        root = tk.Tk()
    root.withdraw()                       # evita flash antes de configurar
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", alpha)
    root.configure(bg="black")
    root.overrideredirect(True)           # sem borda/decoração
    root.lift()
    root.attributes("-topmost", True)
    root.deiconify()

    # força o foco de teclado no overlay
    root.focus_force()     # pede o foco ao Window Manager
    root.update()          # garante que o pedido seja processado

    # --- Canvas para desenhar seleção -----------------------------
    cvs = tk.Canvas(
        root,
        cursor="cross",
        highlightthickness=0,
        bg=root["bg"]        # usa o mesmo fundo ("black")
    )
    cvs.pack(fill="both", expand=True)

    start = {}
    rect_id = None

    # --------------------------------------------------------------
    def _cancel(_evt=None):
        """Esc → cancelar seleção / fechar overlay."""
        result["coords"] = None
        root.quit()

    def _mouse_down(evt):
        nonlocal rect_id
        start["x"], start["y"] = cvs.canvasx(evt.x), cvs.canvasy(evt.y)
        rect_id = cvs.create_rectangle(
            start["x"], start["y"], start["x"], start["y"],
            outline=outline, width=line_width
        )

    def _mouse_drag(evt):
        if rect_id:
            cvs.coords(rect_id,
                       start["x"], start["y"],
                       cvs.canvasx(evt.x), cvs.canvasy(evt.y))

    def _mouse_up(evt):
        if rect_id:
            x1, y1, x2, y2 = map(int, cvs.coords(rect_id))
            result["coords"] = (min(x1, x2), min(y1, y2),
                                max(x1, x2), max(y1, y2))
        root.quit()

    # --- Bindings --------------------------------------------------
    cvs.bind("<ButtonPress-1>", _mouse_down)
    cvs.bind("<B1-Motion>",      _mouse_drag)
    cvs.bind("<ButtonRelease-1>", _mouse_up)

    cvs.bind("<Escape>", _cancel)       # Esc antes/depois do clique
    root.bind("<Escape>", _cancel)      # extra
    root.bind_all("<Escape>", _cancel)  # pega Esc vindo de qualquer widget

    cvs.focus_set()     # recebe imediatamente teclado
    try:
        root.grab_set() # captura eventos até root.quit()
    except tk.TclError:
        pass            # continua sem o grab explícito     

    # --- Loop modal -----------------------------------------------
    root.mainloop()
    root.destroy()

    # devolve foco/posição ao chamador, se fornecido
    if parent is not None and parent.winfo_exists():
        try:
            parent.deiconify()
            parent.lift()
            parent.focus_force()
        except tk.TclError:
            pass
    return result["coords"]
# ----------------------------------------------------------------------
def pick_area(parent,
              coords_dict: dict,
              text_target=None,          # tk.StringVar OU widget com .config(text=…)
              after=None,                # callback a executar se ⇢ área escolhida
              outline="red",
              fmt="x={x} y={y} w={w} h={h}"):
    """
    Seleciona área na tela e aplica resultado.
    • parent .......... janela que chamou
    • coords_dict ..... dict com chaves 'x','y','w','h' (será atualizado)
    • text_target ..... StringVar OU widget (Label, ttk.Label …) para mostrar coords
    • after ........... função a chamar quando a seleção for bem-sucedida
    """
    # Se a janela era modal, liberamos o grab temporariamente
    modal = parent.grab_current() is parent
    if modal:
        parent.grab_release()

    parent.withdraw()
    area = select_area(parent=parent, outline=outline)
    parent.deiconify()

    if modal:
        parent.grab_set()          # devolve modalidade

    if area is None:
        return None

    x1, y1, x2, y2 = area
    coords_dict.update({'x': x1, 'y': y1,
                        'w': x2 - x1, 'h': y2 - y1})

    if text_target is not None:
        text = fmt.format(**coords_dict)
        if hasattr(text_target, "set"):          # StringVar
            text_target.set(text)
        else:                                   # Label-like
            text_target.config(text=text)

    if callable(after):
        after()

    return area
