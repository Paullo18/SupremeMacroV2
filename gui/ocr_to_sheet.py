# gui/ocr_to_sheet.py

import tkinter as tk
from tkinter import Toplevel, messagebox, Canvas
from tkinter import ttk
from PIL import Image, ImageGrab, ImageTk, Image
import pytesseract
from utils.google_sheet_util import append_next_row

def add_ocr_to_sheet(actions=None, update_list=None, tela=None, *, initial=None):
    # — Cria janela modal —
    win = Toplevel(tela)
    win.title("Capturar Texto → Google Sheets")
    win.transient(tela)
    win.resizable(False, False)
    win.grab_set()
    win.columnconfigure(0, weight=1)

    # — Constantes e estado —
    BASE_W, BASE_H = 220, 120
    coords     = {'x':0,  'y':0,  'w':0,  'h':0}
    refresher  = {'job': None}
    thumbs     = {}
    scale_var  = tk.IntVar(value=1)
    coord_var  = tk.StringVar(value="(não selecionada)")

    # — Helpers internos —
    def _display(img: Image.Image):
        ph = ImageTk.PhotoImage(img)
        canvas_prev.delete('prev')
        if scale_var.get() == 1:
            thumb = img.copy()
            thumb.thumbnail((BASE_W, BASE_H), Image.LANCZOS)
            ph2 = ImageTk.PhotoImage(thumb)
            canvas_prev.config(width=BASE_W, height=BASE_H)
            canvas_prev.create_image(
                BASE_W//2, BASE_H//2,
                image=ph2, tags='prev', anchor='center'
            )
            thumbs['thumb'] = ph2
        else:
            canvas_prev.config(width=img.width, height=img.height)
            canvas_prev.create_image(
                0, 0,
                image=ph, tags='prev', anchor='nw'
            )
            thumbs['full'] = ph

    def _refresh():
        if coords['w']>0 and coords['h']>0:
            x,y,w,h = coords['x'],coords['y'],coords['w'],coords['h']
            snap = ImageGrab.grab(bbox=(x,y,x+w,y+h))
            s = scale_var.get()
            if s>1:
                snap = snap.resize((snap.width*s, snap.height*s), Image.LANCZOS)
            _display(snap)
        refresher['job'] = win.after(300, _refresh)

    def _start_refresh():
        if refresher['job'] is None:
            _refresh()

    def _stop_refresh():
        if refresher['job'] is not None:
            win.after_cancel(refresher['job'])
            refresher['job'] = None

    def on_scale_change(*_):
        """Reinicia preview e redimensiona a janela ao mudar o zoom."""
        _stop_refresh()
        _start_refresh()
        win.update_idletasks()
        rw, rh = win.winfo_reqwidth(), win.winfo_reqheight()
        sw, sh = tela.winfo_screenwidth(), tela.winfo_screenheight()
        win.geometry(f"{rw}x{rh}+{(sw-rw)//2}+{(sh-rh)//2}")

    def selecionar_area():
        """Overlay fullscreen para o usuário definir a região."""
        win.withdraw()
        ov = Toplevel(win)
        ov.attributes('-fullscreen', True)
        ov.attributes('-alpha', 0.3)
        ov.grab_set()
        cvs = Canvas(ov, cursor='cross')
        cvs.pack(fill='both', expand=True)

        rect = [None]
        sx = sy = 0
        def down(e):
            nonlocal sx, sy
            sx, sy = e.x, e.y
            rect[0] = cvs.create_rectangle(sx, sy, sx, sy, outline='red', width=2)
        def drag(e):
            cvs.coords(rect[0], sx, sy, e.x, e.y)
        def up(e):
            x1,y1,x2,y2 = cvs.coords(rect[0])
            ov.destroy()
            win.deiconify()
            coords.update({
                'x':int(min(x1,x2)), 'y':int(min(y1,y2)),
                'w':int(abs(x2-x1)),  'h':int(abs(y2-y1))
            })
            coord_var.set(f"x={coords['x']} y={coords['y']} w={coords['w']} h={coords['h']}")
            _start_refresh()

        cvs.bind('<ButtonPress-1>',    down)
        cvs.bind('<B1-Motion>',        drag)
        cvs.bind('<ButtonRelease-1>',  up)
        ov.bind('<Escape>', lambda e: (ov.destroy(), win.deiconify()))

    def on_test():
        """Mostra o texto extraído sem enviar à planilha."""
        if coords['w']==0:
            messagebox.showwarning("Teste OCR","Selecione primeiro a área.")
            return
        x,y,w,h = coords['x'],coords['y'],coords['w'],coords['h']
        snap = ImageGrab.grab(bbox=(x,y,x+w,y+h))
        s = scale_var.get()
        if s>1:
            snap = snap.resize((snap.width*s, snap.height*s), Image.LANCZOS)
        texto = pytesseract.image_to_string(snap, lang='por').strip()
        messagebox.showinfo("Teste OCR", f"Texto extraído:\n\n{texto}")

    def on_ok():
        """Salva apenas os parâmetros do bloco e fecha a janela."""
        _stop_refresh()
        if coords['w']==0:
            messagebox.showerror("Erro","Selecione uma área primeiro.")
            return
        ac = {
            "type":  "text_to_sheet",
            "x":     coords['x'],
            "y":     coords['y'],
            "w":     coords['w'],
            "h":     coords['h'],
            "scale": scale_var.get()
        }
        actions.append(ac)
        update_list()
        win.destroy()

    def on_cancel():
        _stop_refresh()
        win.destroy()

    # — Layout com ttk e grid —
    # 1) Configurações
    cfg = ttk.Labelframe(win, text="Configurações")
    cfg.grid(row=0, column=0, sticky="ew", padx=15, pady=(15,5))
    cfg.columnconfigure(1, weight=1)

    ttk.Label(cfg, text="Área:").grid(row=0, column=0, sticky="w", pady=2)
    ttk.Label(cfg, textvariable=coord_var).grid(row=0, column=1, sticky="w", pady=2)

    ttk.Label(cfg, text="Zoom:").grid(row=1, column=0, sticky="w", pady=2)
    zoom_spin = ttk.Spinbox(
        cfg, from_=1, to=3,
        textvariable=scale_var,
        width=3, wrap=True, justify="center", state="readonly"
    )
    zoom_spin.grid(row=1, column=1, sticky="w", pady=2)
    scale_var.trace_add('write', on_scale_change)

    # 2) Preview
    prev = ttk.Labelframe(win, text="Visualização")
    prev.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
    canvas_prev = Canvas(prev, width=BASE_W, height=BASE_H,
                         highlightthickness=1, highlightbackground="#999")
    canvas_prev.grid(row=0, column=0, padx=10, pady=10)

    # 3) Botões
    btns = ttk.Frame(win)
    btns.grid(row=2, column=0, sticky="e", padx=15, pady=(5,15))
    ttk.Button(btns, text="Selecionar Área", command=selecionar_area)\
        .grid(row=0, column=0, padx=(0,5))
    ttk.Button(btns, text="Testar OCR", command=on_test)\
        .grid(row=0, column=1, padx=(0,5))
    ttk.Button(btns, text="Cancelar", command=on_cancel)\
        .grid(row=0, column=2, padx=(0,5))
    ttk.Button(btns, text="OK", command=on_ok)\
        .grid(row=0, column=3)

    # — Pré‑carrega se vier initial (reabre com área + zoom) —
    if initial:
        coords.update({
            'x': initial.get('x', 0),
            'y': initial.get('y', 0),
            'w': initial.get('w', 0),
            'h': initial.get('h', 0)
        })
        scale_var.set(initial.get('scale', 1))
        coord_var.set(f"x={coords['x']} y={coords['y']} w={coords['w']} h={coords['h']}")
        win.update_idletasks()
        _start_refresh()
        # reaplica o resize inicial de acordo com zoom
        rw, rh = win.winfo_reqwidth(), win.winfo_reqheight()
        sw, sh = tela.winfo_screenwidth(), tela.winfo_screenheight()
        win.geometry(f"{rw}x{rh}+{(sw-rw)//2}+{(sh-rh)//2}")
    else:
        # primeiro open: centraliza no tamanho base
        win.update_idletasks()
        rw, rh = win.winfo_reqwidth(), win.winfo_reqheight()
        sw, sh = tela.winfo_screenwidth(), tela.winfo_screenheight()
        win.geometry(f"{rw}x{rh}+{(sw-rw)//2}+{(sh-rh)//2}")

    # — Exibe e aguarda fechamento —
    win.deiconify()
    win.focus_force()
    win.bind('<Return>', lambda e: on_ok())
    win.bind('<Escape>', lambda e: on_cancel())
    win.wait_window()
