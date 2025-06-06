import tkinter as tk
from tkinter import (
    Toplevel, StringVar, Label, Entry, Button,
    messagebox, Radiobutton, BooleanVar, Canvas
)
from PIL import ImageGrab, ImageTk
import pytesseract
import cv2, numpy as np


# ================================================================
# OCR Duplo – com dois previews ao vivo das áreas selecionadas
# ================================================================

def add_ocr_duplo(actions, atualizar, tela, listbox=None, *, initial=None):
    """
    Janela de configuração para OCR Duplo.

    Parameters
    ----------
    actions   : list             – buffer onde o dict resultante será anexado
    atualizar : callable         – callback da sua listbox (refresh)
    tela      : tk.Tk | tk.Toplevel
    listbox   : opcional (não usado aqui)
    initial   : dict | None      – dados já existentes, para modo de edição
    """
    win = Toplevel(tela)
    win.title("Adicionar OCR Duplo")
    win.geometry("520x600")
    win.grab_set()

    # ---------------- estado inicial -----------------------------------
    txt1   = StringVar(value=initial.get("text1", "")      if initial else "")
    txt2   = StringVar(value=initial.get("text2", "")      if initial else "")
    cond   = StringVar(value=initial.get("condicao", "and")if initial else "and")
    vazio1 = BooleanVar(value=initial.get("vazio1", False) if initial else False)
    vazio2 = BooleanVar(value=initial.get("vazio2", False) if initial else False)

    # coords1 = {x,y,w,h}  /  coords2 = {x,y,w,h}
    coords1 = {k: initial.get({"x":"x1","y":"y1","w":"w1","h":"h1"}[k], 0)
               if initial else 0 for k in ("x","y","w","h")}
    coords2 = {k: initial.get({"x":"x2","y":"y2","w":"w2","h":"h2"}[k], 0)
               if initial else 0 for k in ("x","y","w","h")}

    # ids de after() para parar o loop
    job1, job2 = {"id": None}, {"id": None}

    # ---------------- layout ------------------------------------------
    top = tk.Frame(win); top.pack(fill="x", pady=6)
    mid = tk.Frame(win); mid.pack(fill="both", expand=True)
    bot = tk.Frame(win); bot.pack(pady=8)

    # texto esperado + checkbox “vazio”
    for txt, vaz in ((txt1, vazio1), (txt2, vazio2)):
        frm = tk.Frame(top); frm.pack(fill="x", padx=10, pady=4)
        Entry(frm, textvariable=txt).pack(side="left", fill="x", expand=True)
        tk.Checkbutton(frm, text="Vazio", variable=vaz).pack(side="left")

    # duas colunas com canvas + rótulo + botão
    left, right = tk.Frame(mid), tk.Frame(mid)
    left.pack(side="left", expand=True, padx=5)
    right.pack(side="left", expand=True, padx=5)

    canvas1 = Canvas(left,  width=220, height=120,
                     highlightthickness=2, highlightbackground="dodger blue")
    canvas1.pack(pady=4)
    lbl1 = Label(left, text="Área 1 não definida"); lbl1.pack()
    btn1 = Button(left, text="Selecionar Área 1"); btn1.pack(pady=4)

    canvas2 = Canvas(right, width=220, height=120,
                     highlightthickness=2, highlightbackground="purple")
    canvas2.pack(pady=4)
    lbl2 = Label(right, text="Área 2 não definida"); lbl2.pack()
    btn2 = Button(right, text="Selecionar Área 2"); btn2.pack(pady=4)

    # condição AND / OR
    tk.Label(mid, text="Condição:").pack(pady=(10, 0))
    Radiobutton(mid, text="Ambos (AND)",   variable=cond, value="and"
               ).pack(anchor="w", padx=20)
    Radiobutton(mid, text="Um ou outro (OR)", variable=cond, value="or"
               ).pack(anchor="w", padx=20)

    # botões OK / Cancelar
    Button(bot, text="OK",      width=8,
           command=lambda: _close(True)).pack(side="left",  padx=6)
    Button(bot, text="Cancelar", width=8,
           command=lambda: _close(False)).pack(side="left", padx=6)

    # --------------- thumbnails & preview ao vivo ----------------------
    thumbs = {}
    def _thumb(img, cvs, tag):
        w, h = 220, 120
        im = img.copy()
        im.thumbnail((w, h))
        ph = ImageTk.PhotoImage(im)
        cvs.delete(tag)
        cvs.create_image(w//2, h//2, image=ph, anchor="center", tags=tag)
        thumbs[tag] = ph      # mantém referência

    def _refresh(coords, cvs, tag, job):
        if coords["w"] == 0:
            return
        bbox = (coords["x"], coords["y"],
                coords["x"] + coords["w"], coords["y"] + coords["h"])
        try:
            snap = ImageGrab.grab(bbox=bbox)
            _thumb(snap, cvs, tag)
        finally:
            job["id"] = win.after(300,
                lambda: _refresh(coords, cvs, tag, job))

    def _start(job, coords, cvs, tag):
        if job["id"] is None:
            _refresh(coords, cvs, tag, job)

    def _stop(job):
        if job["id"] is not None:
            win.after_cancel(job["id"])
            job["id"] = None

    # --------------- seleção de área -----------------------------------
    def _select(coords, lbl, cvs, tag, job, color):
        win.withdraw()
        ov = tk.Toplevel(win)
        ov.attributes("-fullscreen", True)
        ov.attributes("-alpha", 0.30)
        ov.configure(bg="black")

        cvs2 = tk.Canvas(ov, cursor="cross")
        cvs2.pack(fill="both", expand=True)

        rect_id, sx, sy = None, 0, 0

        def down(e):
            nonlocal rect_id, sx, sy
            sx, sy = cvs2.canvasx(e.x), cvs2.canvasy(e.y)
            rect_id = cvs2.create_rectangle(sx, sy, sx, sy,
                                            outline=color, width=2)

        def drag(e):
            cvs2.coords(rect_id, sx, sy, cvs2.canvasx(e.x), cvs2.canvasy(e.y))

        def up(e):
            x1, y1, x2, y2 = cvs2.coords(rect_id)
            ov.destroy(); win.deiconify()
            coords.update({
                "x": int(min(x1, x2)), "y": int(min(y1, y2)),
                "w": int(abs(x2 - x1)), "h": int(abs(y2 - y1))
            })
            lbl.config(text=f"x={coords['x']} y={coords['y']} "
                            f"w={coords['w']} h={coords['h']}")
            _start(job, coords, cvs, tag)

        cvs2.bind("<Button-1>", down)
        cvs2.bind("<B1-Motion>", drag)
        cvs2.bind("<ButtonRelease-1>", up)
        ov.bind("<Escape>", lambda e: ov.destroy() or win.deiconify())

    btn1.configure(command=lambda:
        _select(coords1, lbl1, canvas1, "prev1", job1, "red"))
    btn2.configure(command=lambda:
        _select(coords2, lbl2, canvas2, "prev2", job2, "yellow"))

    # --------------- TESTE ---------------------------------------------
    def _test():
        if coords1["w"] == 0 or coords2["w"] == 0:
            messagebox.showwarning("Áreas", "Defina as duas áreas.")
            return
        bbox1 = (coords1["x"], coords1["y"],
                 coords1["x"] + coords1["w"], coords1["y"] + coords1["h"])
        bbox2 = (coords2["x"], coords2["y"],
                 coords2["x"] + coords2["w"], coords2["y"] + coords2["h"])
        t1 = pytesseract.image_to_string(ImageGrab.grab(bbox=bbox1)).strip()
        t2 = pytesseract.image_to_string(ImageGrab.grab(bbox=bbox2)).strip()
        messagebox.showinfo("OCR Duplo",
            f"Área 1:\n{t1 or '[vazio]'}\n\nÁrea 2:\n{t2 or '[vazio]'}")

    Button(mid, text="Testar OCR", command=_test).pack(pady=6)

    # --------------- FECHAR --------------------------------------------
    def _close(save: bool):
        _stop(job1); _stop(job2)

        if not save:
            win.destroy()
            return

        if coords1["w"] == 0 or coords2["w"] == 0:
            messagebox.showerror("Erro", "Defina ambas as áreas.")
            return

        actions.append({
            "type":   "ocr_duplo",
            "x1": coords1["x"], "y1": coords1["y"],
            "w1": coords1["w"], "h1": coords1["h"],
            "x2": coords2["x"], "y2": coords2["y"],
            "w2": coords2["w"], "h2": coords2["h"],
            "text1": txt1.get(),
            "text2": txt2.get(),
            "condicao": cond.get(),
            "vazio1":  vazio1.get(),
            "vazio2":  vazio2.get()
        })

        # callback para atualizar a lista na UI principal
        if callable(atualizar):
            atualizar()

        win.destroy()

    # --------------- previews iniciais ---------------------------------
    if coords1["w"] > 0:
        lbl1.config(text=f"x={coords1['x']} y={coords1['y']} "
                         f"w={coords1['w']} h={coords1['h']}")
        _start(job1, coords1, canvas1, "prev1")

    if coords2["w"] > 0:
        lbl2.config(text=f"x={coords2['x']} y={coords2['y']} "
                         f"w={coords2['w']} h={coords2['h']}")
        _start(job2, coords2, canvas2, "prev2")
