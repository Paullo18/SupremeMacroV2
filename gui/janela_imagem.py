import tkinter as tk
from tkinter import Toplevel, Label, Button, messagebox, Canvas, Frame, Entry, StringVar
from PIL import ImageGrab, Image, ImageTk
import cv2, numpy as np, os
from datetime import datetime
import pyautogui
import core.storage as storage

# ========================================================================
# Janela "Se Imagem" – agora com **preview ao vivo** da área selecionada
# ========================================================================

def add_imagem(actions, update_list, tela, *, initial=None):
    # janela modal
    win = Toplevel(tela)
    win.withdraw()
    win.transient(tela)
    win.title("Adicionar Reconhecimento de Imagem")
    win.resizable(False, False)

    # --- Campo editável para label customizada do bloco -------------
    Label(win, text="Nome do bloco:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    name_var = StringVar(value=initial.get("name", "") if initial else "")
    Entry(win, textvariable=name_var, width=40).grid(row=0, column=1, padx=5, pady=5)

    # ----------------------------------------------------
    imagem_ref = {"img": None}          # PIL.Image do template
    area_busca = {"x": 0, "y": 0, "w": 0, "h": 0}
    job_area   = {"id": None}           # id do after() p/ cancelar
    novo_template = False
    original_path = initial.get("imagem") if initial else None

    # ---------------------------------------------------- layout
    left, right, bottom = (Frame(win) for _ in range(3))
    left.grid(row=1, column=0, padx=10, pady=10, sticky="ns")
    right.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
    bottom.grid(row=2, column=0, columnspan=2, pady=10)
    win.grid_columnconfigure(1, weight=1)

    btn_img  = Button(left, text="Selecionar imagem (template)")
    btn_area = Button(left, text="Selecionar área de busca")
    btn_test = Button(left, text="Testar presença da imagem")
    btn_img.pack(fill="x", pady=3)
    btn_area.pack(fill="x", pady=3)

    canvas_area = Canvas(left, width=180, height=120,
                         highlightthickness=2, highlightbackground="dodger blue")
    canvas_area.pack(pady=6)
    lbl_coords = Label(left, text="Área não definida")
    lbl_coords.pack(pady=(0,8))
    btn_test.pack(fill="x", pady=3)

    canvas_img = Canvas(right, width=400, height=400,
                        highlightthickness=2, highlightbackground="black")
    canvas_img.pack(expand=True)

    btn_ok     = Button(bottom, text="OK", width=9)
    btn_cancel = Button(bottom, text="Cancelar", width=9, command=lambda: _close(False))
    btn_ok.pack(side="left", padx=6)
    btn_cancel.pack(side="left", padx=6)

    thumbs = {}
    def _thumb(img, cvs, tag):
        w,h = int(cvs['width']), int(cvs['height'])
        im = img.copy(); im.thumbnail((w,h))
        ph = ImageTk.PhotoImage(im)
        cvs.delete(tag)
        cvs.create_image(w//2, h//2, image=ph, anchor='center', tags=tag)
        thumbs[tag] = ph

    # -------------------- captura ao vivo -----------------------------
    def _refresh_area():
        if area_busca['w']<=0 or area_busca['h']<=0:
            return
        try:
            bbox = (
                area_busca['x'],
                area_busca['y'],
                area_busca['x'] + area_busca['w'],
                area_busca['y'] + area_busca['h']
            )
            snap = ImageGrab.grab(bbox=bbox)
            _thumb(snap, canvas_area, 'area')
        finally:
            job_area['id'] = win.after(300, _refresh_area)

    def _start_live_area():
        if job_area['id'] is None:
            _refresh_area()

    def _stop_live_area():
        if job_area['id'] is not None:
            win.after_cancel(job_area['id'])
            job_area['id'] = None

    # -------------------- seleção template ----------------------------
    def selecionar_imagem():
        nonlocal novo_template
        _selecionar_ret(cor='red', cb=_set_template)
        novo_template = True

    def _set_template(x,y,w,h):
        snap = ImageGrab.grab(bbox=(x,y,x+w,y+h))
        imagem_ref['img'] = snap
        _thumb(snap, canvas_img, 'template')

    def _load_template(path):
        try:
            im = Image.open(path)
            imagem_ref['img'] = im
            _thumb(im, canvas_img, 'template')
        except Exception as e:
            print('[Aviso]', e)

    # -------------------- seleção área -------------------------------
    def selecionar_area():
        _selecionar_ret(cor='yellow', overlay='blue', cb=_set_area)

    def _set_area(x,y,w,h):
        area_busca.update({'x':x,'y':y,'w':w,'h':h})
        lbl_coords.config(text=f"Área: x={x} y={y} w={w} h={h}")
        _start_live_area()

    # ---------- ret genérico ----------------------------------------
    def _selecionar_ret(cor, cb, overlay='black'):
        win.withdraw()
        ov = Toplevel(win)
        ov.attributes('-fullscreen', True)
        ov.attributes('-alpha', 0.3)
        ov.configure(bg=overlay)
        ov.grab_set()
        ov.focus_set()

        cvs = tk.Canvas(ov, cursor='cross')
        cvs.pack(fill='both', expand=True)
        rect = [None]
        sx = sy = 0

        def down(e):
            nonlocal sx, sy
            sx, sy = cvs.canvasx(e.x), cvs.canvasy(e.y)
            rect[0] = cvs.create_rectangle(sx, sy, sx, sy, outline=cor, width=2)

        def drag(e):
            cvs.coords(rect[0], sx, sy, cvs.canvasx(e.x), cvs.canvasy(e.y))

        def up(e):
            x1, y1, x2, y2 = cvs.coords(rect[0])
            ov.destroy()
            win.deiconify()
            cb(int(min(x1,x2)), int(min(y1,y2)), int(abs(x2-x1)), int(abs(y2-y1)))

        cvs.bind('<Button-1>', down)
        cvs.bind('<B1-Motion>', drag)
        cvs.bind('<ButtonRelease-1>', up)
        ov.bind('<Escape>', lambda e: ov.destroy() or win.deiconify())

    # -------------------- teste --------------------------------------
    def testar():
        if imagem_ref['img'] is None or area_busca['w']<=0:
            messagebox.showwarning('Dados', 'Defina template e área.')
            return
        bbox = (area_busca['x'], area_busca['y'],
                area_busca['x']+area_busca['w'],
                area_busca['y']+area_busca['h'])
        area = ImageGrab.grab(bbox=bbox)
        res = cv2.matchTemplate(
            cv2.cvtColor(np.array(area), cv2.COLOR_RGB2BGR),
            cv2.cvtColor(np.array(imagem_ref['img']), cv2.COLOR_RGB2BGR),
            cv2.TM_CCOEFF_NORMED
        )
        ok = cv2.minMaxLoc(res)[1] >= 0.8
        messagebox.showinfo('Teste', 'Imagem encontrada!' if ok else 'Imagem NÃO encontrada.')

    btn_img.configure(command=selecionar_imagem)
    btn_area.configure(command=selecionar_area)
    btn_test.configure(command=testar)

    # -------------------- confirmar / fechar -------------------------
    def _close(save):
        _stop_live_area()
        if not save:
            win.destroy()
            return
        if imagem_ref['img'] is None or area_busca['w']<=0:
            messagebox.showwarning('Dados', 'Defina template e área.')
            return
        if not novo_template and original_path:
            fname = original_path
        else:
            os.makedirs('tmp', exist_ok=True)
            fname = f"imagem_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
            imagem_ref['img'].save(os.path.join('tmp', fname))
        ac = {'type':'imagem', **area_busca, 'imagem':fname}
        nome = name_var.get().strip()
        if nome:
            ac['name'] = nome
        actions.append(ac)
        update_list()
        win.destroy()

    btn_ok.configure(command=lambda: _close(True))

    # ------------------- pré-visualização inicial --------------------
    if initial and all(k in initial for k in ('x','y','w','h','imagem')):
        _set_area(initial['x'], initial['y'], initial['w'], initial['h'])
        img_path = initial['imagem']

        # Se não for caminho absoluto, tenta achar em cwd, no macro path e finalmente em tmp/
        if not os.path.isabs(img_path):
            # primeiro tenta mesmo nome no cwd
            if not os.path.exists(img_path):
                # depois tenta pasta tmp/
                tmp_path = os.path.join('tmp', os.path.basename(img_path))
                if os.path.exists(tmp_path):
                    img_path = tmp_path

        _load_template(img_path)
    else:
        _stop_live_area()

    # --- Centralizar, bloquear resize, foco e atalhos -------------
    win.update_idletasks()
    px, py = tela.winfo_rootx(), tela.winfo_rooty()
    pw, ph = tela.winfo_width(), tela.winfo_height()
    w, h   = win.winfo_width(), win.winfo_height()
    x = px + (pw - w) // 2
    y = py + (ph - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")
    win.deiconify()
    win.minsize(w, h)
    win.maxsize(w, h)
    win.focus_force()
    win.bind("<Escape>", lambda e: win.destroy())
    win.bind("<Return>", lambda e: _close(True))