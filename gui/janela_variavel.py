# gui/janela_variavel.py

import tkinter as tk
from tkinter import ttk, Toplevel, Frame, Label, Entry, Button, StringVar, IntVar
from core import show_warning
from utils.live_preview import LivePreview
from utils.area_select import select_area
from PIL import ImageGrab

class RegionSelector(tk.Toplevel):
    """
    Janela transparente fullscreen para o usuário arrastar o mouse
    e selecionar uma região (x1,y1,x2,y2) na tela. Quando soltar,
    salva coords em self.region_attrs e fecha.
    """
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        # Em vez de "-fullscreen", usamos geometry para cobrir toda a tela:
        self.update_idletasks()
        largura = self.winfo_screenwidth()
        altura  = self.winfo_screenheight()
        self.geometry(f"{largura}x{altura}+0+0")
        # torna a janela semitransparente
        self.attributes("-alpha", 0.3)
        self.config(bg="gray")

        # força este toplevel a pegar todos os eventos de mouse/teclado
        self.grab_set()
        # bind para permitir cancelar com Esc
        self.bind("<Escape>", lambda e: self.destroy())

        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.current_bbox = None   # (x1,y1,x2,y2) atualizado em tempo real
        self.region_attrs = None    # vai ficar {"x":..., "y":..., "w":..., "h":...}

        self.canvas = tk.Canvas(self, cursor="cross")  
        self.canvas.pack(fill="both", expand=True)

        # ─── Frame de preview ────────────────────────────────────────────
        # Um pequeno canvas no canto superior direito que mostrará o preview da região
        preview_w, preview_h = 200, 150
        self.preview_canvas = tk.Canvas(self, width=preview_w, height=preview_h, bd=1, relief="solid")
        # Posiciona no canto superior direito (-10px de borda e -10px de topo)
        self.preview_canvas.place(x=self.winfo_screenwidth() - preview_w - 10,
                                  y=10)
        # Cria o LivePreview, dando a função que retorna a caixa atual
        self._preview = LivePreview(
            canvas=self.preview_canvas,
            region_getter=lambda: tuple(self.current_bbox) if self.current_bbox else None,
            interval=0.2,      # atualiza a cada 0.2s
            transform=None
        )

        self.canvas.bind("<ButtonPress-1>", self._on_button_press)
        self.canvas.bind("<B1-Motion>", self._on_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_button_release)
        self.focus_force()

    def _on_button_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        # Se já houver algum retângulo, apaga
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        # Inicializa a bounding box atual para o preview
        self.current_bbox = (self.start_x, self.start_y, self.start_x, self.start_y)
        # Inicia o preview
        self._preview.start()

    def _on_move(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)
        else:
            self.rect_id = self.canvas.create_rectangle(
                self.start_x, self.start_y, cur_x, cur_y,
                outline="red", width=2, dash=(4,2)
            )
        
        # Atualiza a região atual para o preview (sempre x1<=x2, y1<=y2)
        x1 = min(self.start_x, cur_x)
        y1 = min(self.start_y, cur_y)
        x2 = max(self.start_x, cur_x)
        y2 = max(self.start_y, cur_y)
        self.current_bbox = (x1, y1, x2, y2)

    def _on_button_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        x1 = int(min(self.start_x, end_x))
        y1 = int(min(self.start_y, end_y))
        x2 = int(max(self.start_x, end_x))
        y2 = int(max(self.start_y, end_y))
        w = x2 - x1
        h = y2 - y1
        self.region_attrs = {"x": x1, "y": y1, "w": w, "h": h}
        # Para o preview e fecha
        self._preview.stop()
        self.destroy()


def add_variavel(actions, update_list, tela, *, initial=None):
    """
    Abre janela para o usuário definir uma variável de dois modos:
     1) 'manual'   → digita valor no campo Entry
     2) 'ocr_region' → clica em 'Selecionar Região' e arrasta retângulo na tela
    actions: lista onde será feito actions.append({ … })
    update_list: callback para redesenhar o bloco após confirmação
    tela: janela pai (Tk root)
    initial: dict { "mode": "...", "var_name": "...", "var_value": "..."/"region": {...} }
    """
    win = Toplevel(tela)
    win.withdraw()
    win.transient(tela)
    win.title("Editar Variável")
    win.resizable(False, False)
    win.grab_set()
    win.focus_force()

    # Guarda callback e buffer
    act_buffer = actions

    # --- Nome da variável ---
    Label(win, text="Nome da variável:").grid(row=0, column=0, sticky="w", padx=10, pady=(10,2))
    name_var = StringVar(value=(initial.get("var_name", "") if initial else ""))
    Entry(win, textvariable=name_var, width=30).grid(row=0, column=1, padx=10, pady=(10,2))

    # --- Modo: Manual ou Selecionar Texto na Tela ---
    Label(win, text="Modo:").grid(row=1, column=0, sticky="nw", padx=10, pady=(2,2))
    mode_var = IntVar(value=(0 if not initial or initial.get("mode","manual") == "manual" else 1))
    rb_manual = ttk.Radiobutton(
        win, text="Manual", variable=mode_var, value=0, command=lambda: _toggle_mode()
    )
    rb_manual.grid(row=1, column=1, sticky="w", padx=10, pady=(2,0))

    rb_sel = ttk.Radiobutton(
        win, text="Selecionar Texto na Tela", variable=mode_var, value=1, command=lambda: _toggle_mode()
    )
    rb_sel.grid(row=2, column=1, sticky="w", padx=10, pady=(0,8))

    # --- Campo Valor (Manual) ---
    Label(win, text="Valor:").grid(row=3, column=0, sticky="w", padx=10, pady=(2,10))
    val_var = StringVar(value=(initial.get("var_value","") if initial and initial.get("mode","manual")=="manual" else ""))
    entry_val = Entry(win, textvariable=val_var, width=30)
    entry_val.grid(row=3, column=1, padx=10, pady=(2,10))

    # ─── Dicionário que guarda as coordenadas da seleção ──────────────────────
    coords = {
    "x": initial["region"]["x"] if initial and "region" in initial else 0,
    "y": initial["region"]["y"] if initial and "region" in initial else 0,
    "w": initial["region"]["w"] if initial and "region" in initial else 0,
    "h": initial["region"]["h"] if initial and "region" in initial else 0
}

    # --- Botão para selecionar texto na tela (área) ---
    btn_select = Button(win, text="Selecionar Texto na Tela")
    btn_select.grid(row=4, column=0, columnspan=2, pady=(0, 10))

    # --- Canvas de preview (220×120) ---
    canvas_prev = tk.Canvas(win, width=220, height=120,
                            highlightthickness=2, highlightbackground='dodger blue')
    canvas_prev.grid(row=5, column=0, columnspan=2, pady=(0, 10))

    # ─── Instanciação do LivePreview ─────────────────────────────────────────
    preview = LivePreview(
        canvas_prev,
        lambda: (
            (coords["x"], coords["y"],
             coords["x"] + coords["w"], coords["y"] + coords["h"])
            if coords["w"] and coords["h"] else None
        ),
        interval=0.30
    )
    _start_preview = preview.start
    _stop_preview  = preview.stop

    # Preview automático se já vier inicial
    if coords["w"] and coords["h"]:
        btn_select.config(text=f"Região: {coords['x']},{coords['y']} ({coords['w']}×{coords['h']})")
        _start_preview()

    # Função para seleção de área igual OCR
    def _start_region_select():
        win.withdraw()
        area = select_area()
        win.deiconify()
        if area is None:
            return
        x1, y1, x2, y2 = area
        coords.update({
            "x": x1,
            "y": y1,
            "w": x2 - x1,
            "h": y2 - y1
        })
        btn_select.config(text=f"Região: {coords['x']},{coords['y']} ({coords['w']}×{coords['h']})")
        _start_preview()

    btn_select.config(command=_start_region_select)
    
    # (certifique-se que os botões "OK" e "Cancelar" chamam _stop_preview())
    

    # --- Botões OK / Cancelar ---
    btn_frame = Frame(win)
    btn_frame.grid(row=6, column=0, columnspan=2, pady=(0,10))

    def _confirm():
        vn = name_var.get().strip()
        if not vn:
            show_warning("Aviso", "O nome da variável não pode ficar vazio.")
            return

        if mode_var.get() == 0:
            # Modo manual
            vv = val_var.get().strip()
            params = {"mode": "manual",       "var_name": vn, "var_value": vv}
        else:
            # Modo selecionar texto na tela
            if not (coords["w"] and coords["h"]):
                show_warning("Aviso", "Selecione antes uma região na tela.")
                return
            params = {
                "mode": "select_region",
                "var_name": vn,
                "region": {
                    "x": coords["x"],
                    "y": coords["y"],
                    "w": coords["w"],
                    "h": coords["h"]
                }
            }
        # Grava no buffer e atualiza
        act_buffer.append(params)
        if callable(update_list):
            update_list()
        win.destroy()

    Button(btn_frame, text="OK", width=10, command=lambda: (_stop_preview(), _confirm())).pack(side="left", padx=(0,5))
    Button(btn_frame, text="Cancelar", width=10, command=lambda: (_stop_preview(), win.destroy())).pack(side="right", padx=(5,0))
    #Button(btn_frame, text="OK", width=10, command=_confirm).pack(side="left", padx=(0,5))
    #Button(btn_frame, text="Cancelar", width=10, command=win.destroy).pack(side="right", padx=(5,0))

    # Função que habilita/desabilita os widgets conforme modo
    def _toggle_mode():
        if mode_var.get() == 0:  # manual
            entry_val.config(state="normal")
            btn_select.config(state="disabled")
        else:  # ocr_region
            entry_val.config(state="disabled")
            btn_select.config(state="normal")

    # Inicializa o estado dos botões
    _toggle_mode()

    # Inicia seleção de região na tela
    def _start_region_select():
        # Agora, para usar o select_area + LivePreview, fazemos igual ao OCR:
        win.withdraw()
        area = select_area()     # abre overlay para o usuário arrastar
        win.deiconify()
        if area is None:
            return
        # area == (x1,y1,x2,y2)
        x1, y1, x2, y2 = area
        coords.update({
            "x": x1,
            "y": y1,
            "w": x2 - x1,
            "h": y2 - y1
        })
        # atualiza o texto do botão para mostrar coords resumidas
        btn_select.config(text=f"Região: {coords['x']},{coords['y']} ({coords['w']}×{coords['h']})")
        # inicia o preview vivo, capturando a tela continuamente
        _start_preview()

    # Centraliza a janela na tela
    win.update_idletasks()
    px, py = tela.winfo_rootx(), tela.winfo_rooty()
    pw, ph = tela.winfo_width(), tela.winfo_height()
    w, h = win.winfo_width(), win.winfo_height()
    x = px + (pw - w)//2
    y = py + (ph - h)//2
    win.geometry(f"{w}x{h}+{x}+{y}")
    win.deiconify()
    win.focus_force()

    win.bind("<Escape>", lambda e: win.destroy())
    win.bind("<Return>", lambda e: _confirm())
