import tkinter as tk
from tkinter import Toplevel, StringVar, BooleanVar, Label, Entry, Button, messagebox, Canvas, Checkbutton
from PIL import ImageGrab, ImageTk
import pytesseract, os, cv2, numpy as np

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# =============================================================================
# OCR simples – agora com **preview ao vivo** da área selecionada
# =============================================================================

def add_ocr(actions, update_list, tela, listbox=None, *, initial=None):
    # Janela modal
    win = Toplevel(tela)
    win.withdraw()
    win.transient(tela)
    win.title("Adicionar OCR")
    win.resizable(False, False)

    # --- Campo editável para label customizada do bloco -----------
    Label(win, text="Nome do bloco:").pack(pady=(10, 0), anchor='w', padx=10)
    name_var = StringVar(value=initial.get('name', '') if initial else '')
    Entry(win, textvariable=name_var).pack(fill='x', padx=10, pady=(0, 10))

    # --- Variáveis iniciais ---------------------------------------
    txt_expected = StringVar(value=initial.get('text', '') if initial else '')
    vazio_var    = BooleanVar(value=initial.get('verificar_vazio', False) if initial else False)
    coords = {k: initial.get(k, 0) if initial else 0 for k in ('x', 'y', 'w', 'h')}
    job = {'id': None}

    # --- UI principal ---------------------------------------------
    Label(win, text="Texto esperado:").pack(pady=5, anchor='w', padx=10)
    entry_expected = Entry(win, textvariable=txt_expected)
    entry_expected.pack(fill='x', padx=10)
    # desativa/ativa o campo de texto quando verificar vazio
    def _on_vazio_change(*args):
        if vazio_var.get():
            entry_expected.config(state='disabled')
        else:
            entry_expected.config(state='normal')
    vazio_var.trace_add('write', _on_vazio_change)
    # chama uma vez para inicializar
    _on_vazio_change()

    chk = Checkbutton(win, text="Verificar se está vazio", variable=vazio_var)
    chk.pack(pady=5, anchor='w', padx=10)

    btn_sel = Button(win, text="Selecionar área da tela")
    btn_sel.pack(pady=6)

    canvas_prev = Canvas(win, width=220, height=120,
                         highlightthickness=2, highlightbackground='dodger blue')
    canvas_prev.pack()
    lbl_coord = Label(win, text="Área não definida")
    lbl_coord.pack(pady=(4, 8))

    btn_test = Button(win, text="Testar OCR")
    btn_test.pack(pady=3)

    # Botões OK / Cancelar
    frm = tk.Frame(win)
    frm.pack(pady=8)
    Button(frm, text="OK", width=8, command=lambda: _close(True)).pack(side='left', padx=5)
    Button(frm, text="Cancelar", width=8, command=lambda: _close(False)).pack(side='left', padx=5)

    # --- Thumb & preview ------------------------------------------
    thumbs = {}
    def _thumb(img):
        w, h = 220, 120
        im = img.copy(); im.thumbnail((w, h))
        ph = ImageTk.PhotoImage(im)
        canvas_prev.delete('prev')
        canvas_prev.create_image(w//2, h//2, image=ph, anchor='center', tags='prev')
        thumbs['t'] = ph

    def _refresh():
        if coords['w'] <= 0 or coords['h'] <= 0:
            return
        bbox = (coords['x'], coords['y'], coords['x'] + coords['w'], coords['y'] + coords['h'])
        try:
            snap = ImageGrab.grab(bbox=bbox)
            _thumb(snap)
        finally:
            job['id'] = win.after(300, _refresh)

    def _start():
        if job['id'] is None:
            _refresh()

    def _stop():
        if job['id'] is not None:
            win.after_cancel(job['id'])
            job['id'] = None

    # --- Seleção de área -------------------------------------------
        # --- Seleção de área -------------------------------------------
    def selecionar_area():
        win.withdraw()
        ov = Toplevel(win)
        ov.attributes('-fullscreen', True)
        ov.attributes('-alpha', 0.3)
        ov.configure(bg='black')
        # garante que ESC no overlay seja capturado
        ov.grab_set()
        ov.focus_set()

        cvs = tk.Canvas(ov, cursor='cross')
        cvs.pack(fill='both', expand=True)
        rect = [None]
        sx = sy = 0
        def down(e):
            nonlocal sx, sy
            sx, sy = cvs.canvasx(e.x), cvs.canvasy(e.y)
            rect[0] = cvs.create_rectangle(sx, sy, sx, sy, outline='red', width=2)
        def drag(e):
            cvs.coords(rect[0], sx, sy, cvs.canvasx(e.x), cvs.canvasy(e.y))
        def up(e):
            x1, y1, x2, y2 = cvs.coords(rect[0])
            ov.destroy(); win.deiconify()
            coords.update({
                'x': int(min(x1, x2)), 'y': int(min(y1, y2)),
                'w': int(abs(x2 - x1)), 'h': int(abs(y2 - y1))
            })
            lbl_coord.config(text=f"Área: x={coords['x']} y={coords['y']} w={coords['w']} h={coords['h']}")
            _start()
        cvs.bind('<Button-1>', down)
        cvs.bind('<B1-Motion>', drag)
        cvs.bind('<ButtonRelease-1>', up)
        # ESC no overlay cancela seleção e retorna
        ov.bind('<Escape>', lambda e: ov.destroy() or win.deiconify())

    btn_sel.configure(command=selecionar_area)

    # --- Teste de OCR ----------------------------------------------
    def testar():
        if coords['w'] == 0:
            messagebox.showwarning('Área', 'Defina a área.'); return
        bbox = (coords['x'], coords['y'], coords['x'] + coords['w'], coords['y'] + coords['h'])
        img = ImageGrab.grab(bbox=bbox)
        text = pytesseract.image_to_string(img).strip()
        messagebox.showinfo('OCR Detectado', text or '[vazio]')
    btn_test.configure(command=testar)

    # --- Fechar e gravar ação --------------------------------------
    def _close(save):
        _stop()
        if not save:
            win.destroy(); return
        if coords['w'] == 0:
            messagebox.showerror('Erro', 'Área deve ser definida.'); return
        ac = {'type': 'ocr', **coords,
              'text': txt_expected.get(),
              'verificar_vazio': vazio_var.get()}
        nome = name_var.get().strip()
        if nome:
            ac['name'] = nome
        actions.append(ac)
        if callable(update_list):
            update_list()
        win.destroy()

    # --- Preview inicial --------------------------------------------
    if coords['w'] > 0 and coords['h'] > 0:
        lbl_coord.config(text=f"Área: x={coords['x']} y={coords['y']} w={coords['w']} h={coords['h']}")
        _start()

    # --- Centralizar, bloquear resize, foco e atalhos --------------
    win.update_idletasks()
    px, py = tela.winfo_rootx(), tela.winfo_rooty()
    pw, ph = tela.winfo_width(), tela.winfo_height()
    w, h = win.winfo_width(), win.winfo_height()
    x = px + (pw - w) // 2
    y = py + (ph - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")
    win.deiconify()
    win.minsize(w, h); win.maxsize(w, h)
    win.focus_force()
    win.bind("<Escape>", lambda e: win.destroy())
    win.bind("<Return>", lambda e: _close(True))
