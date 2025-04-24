import tkinter as tk
from tkinter import Toplevel, StringVar, BooleanVar, Label, Entry, Button, messagebox, Canvas, Checkbutton
from PIL import ImageGrab, ImageTk
import pytesseract, os, cv2, numpy as np

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# =============================================================================
# OCR simples – agora com **preview ao vivo** da área selecionada
# =============================================================================

def add_ocr(actions, update_list, tela, listbox=None, *, initial=None):
    win = Toplevel(tela)
    win.title("Adicionar OCR")
    win.geometry("420x320")
    win.grab_set()

    txt_expected = StringVar(value= initial.get('text','') if initial else '')
    vazio_var    = BooleanVar(value= initial.get('verificar_vazio', False) if initial else False)
    coords = {k: initial.get(k,0) if initial else 0 for k in ('x','y','w','h')}
    job = {'id': None}

    # ---------------------- UI ------------------------------------------------
    Label(win, text="Texto esperado:").pack(pady=5)
    Entry(win, textvariable=txt_expected).pack(fill='x', padx=10)
    Checkbutton(win, text="Verificar se está vazio", variable=vazio_var).pack(pady=5)

    btn_sel = Button(win, text="Selecionar área da tela")
    btn_sel.pack(pady=6)

    canvas_prev = Canvas(win, width=220, height=120,
                         highlightthickness=2, highlightbackground='dodger blue')
    canvas_prev.pack()
    lbl_coord = Label(win, text="Área não definida"); lbl_coord.pack(pady=(4,8))

    btn_test = Button(win, text="Testar OCR"); btn_test.pack(pady=3)

    frm = tk.Frame(win); frm.pack(pady=8)
    Button(frm, text="OK", width=8, command=lambda: _close(True)).pack(side='left', padx=5)
    Button(frm, text="Cancelar", width=8, command=lambda: _close(False)).pack(side='left', padx=5)

    thumbs = {}
    def _thumb(img):
        w,h=220,120
        im=img.copy(); im.thumbnail((w,h))
        ph=ImageTk.PhotoImage(im); canvas_prev.delete('prev')
        canvas_prev.create_image(w//2,h//2,image=ph,anchor='center',tags='prev'); thumbs['t']=ph

    # -------------------- live preview ---------------------------------------
    def _refresh():
        if coords['w']<=0 or coords['h']<=0: return
        bbox=(coords['x'],coords['y'],coords['x']+coords['w'],coords['y']+coords['h'])
        try:
            snap=ImageGrab.grab(bbox=bbox); _thumb(snap)
        finally:
            job['id']=win.after(300,_refresh)
    def _start():
        if job['id'] is None: _refresh()
    def _stop():
        if job['id'] is not None:
            win.after_cancel(job['id']); job['id']=None

    # -------------------- selecionar área ------------------------------------
    def selecionar_area():
        win.withdraw(); ov=tk.Toplevel(win)
        ov.attributes('-fullscreen',True); ov.attributes('-alpha',0.3); ov.configure(bg='black')
        cvs=tk.Canvas(ov,cursor='cross'); cvs.pack(fill='both',expand=True)
        rect=[None]; sx=sy=0
        def down(e):
            nonlocal sx,sy; sx,sy=cvs.canvasx(e.x),cvs.canvasy(e.y)
            rect[0]=cvs.create_rectangle(sx,sy,sx,sy,outline='red',width=2)
        def drag(e): cvs.coords(rect[0],sx,sy,cvs.canvasx(e.x),cvs.canvasy(e.y))
        def up(e):
            x1,y1,x2,y2=cvs.coords(rect[0]); ov.destroy(); win.deiconify()
            coords.update({'x':int(min(x1,x2)),'y':int(min(y1,y2)),'w':int(abs(x2-x1)),'h':int(abs(y2-y1))})
            lbl_coord.config(text=f"Área: x={coords['x']} y={coords['y']} w={coords['w']} h={coords['h']}")
            _start()
        cvs.bind('<Button-1>',down); cvs.bind('<B1-Motion>',drag); cvs.bind('<ButtonRelease-1>',up)
        ov.bind('<Escape>', lambda e: ov.destroy() or win.deiconify())

    btn_sel.configure(command=selecionar_area)

    # -------------------- teste ----------------------------------------------
    def testar():
        if coords['w']==0:
            messagebox.showwarning('Área','Defina a área.'); return
        bbox=(coords['x'],coords['y'],coords['x']+coords['w'],coords['y']+coords['h'])
        img=ImageGrab.grab(bbox=bbox)
        text=pytesseract.image_to_string(img).strip()
        messagebox.showinfo('OCR Detectado', text or '[vazio]')
    btn_test.configure(command=testar)

    # -------------------- fechar ---------------------------------------------
    def _close(save):
        _stop()
        if not save:
            win.destroy(); return
        if coords['w']==0:
            messagebox.showerror('Erro','Área deve ser definida.'); return
        actions.append({
            'type':'ocr',
            **coords,
            'text': txt_expected.get(),
            'verificar_vazio': vazio_var.get()
        })
        update_list(); win.destroy()

    # -------------------- inicial --------------------------------------------
    if coords['w']>0 and coords['h']>0:
        lbl_coord.config(text=f"Área: x={coords['x']} y={coords['y']} w={coords['w']} h={coords['h']}")
        _start()