import tkinter as tk
from tkinter import (
    Toplevel, StringVar, BooleanVar, Label, Entry,
    Button, messagebox, Radiobutton, Canvas
)
from PIL import ImageGrab
import pytesseract
from utils.area_select import select_area
from utils.live_preview import LivePreview

# ================================================================
# OCR Duplo – com dois previews ao vivo das áreas selecionadas
# ================================================================

def add_ocr_duplo(actions, atualizar, tela, listbox=None, *, initial=None):
    # cria janela modal
    win = Toplevel(tela)
    win.withdraw()
    win.transient(tela)
    win.title("Adicionar OCR Duplo")
    win.resizable(False, False)

    # --- Campo editável para label customizada do bloco -----------
    Label(win, text="Nome do bloco:").pack(pady=(10, 0), anchor='w', padx=10)
    name_var = StringVar(value=initial.get('name', '') if initial else '')
    Entry(win, textvariable=name_var).pack(fill='x', padx=10, pady=(0, 10))

    # estado inicial dos campos
    txt1   = StringVar(value=initial.get("text1", "") if initial else "")
    txt2   = StringVar(value=initial.get("text2", "") if initial else "")
    cond   = StringVar(value=initial.get("condicao", "and") if initial else "and")
    vazio1 = BooleanVar(value=initial.get("vazio1", False) if initial else False)
    vazio2 = BooleanVar(value=initial.get("vazio2", False) if initial else False)
    coords1 = {k: initial.get({"x":"x1","y":"y1","w":"w1","h":"h1"}[k], 0)
               if initial else 0 for k in ("x","y","w","h")}
    coords2 = {k: initial.get({"x":"x2","y":"y2","w":"w2","h":"h2"}[k], 0)
               if initial else 0 for k in ("x","y","w","h")}

    # layout
    top = tk.Frame(win); top.pack(fill="x", pady=6)
    mid = tk.Frame(win); mid.pack(fill="both", expand=True)
    bot = tk.Frame(win); bot.pack(pady=8)

    # inputs de texto esperado e vazio
    for idx, (txt, vaz) in enumerate(((txt1, vazio1), (txt2, vazio2))):
        frm = tk.Frame(top); frm.pack(fill="x", padx=10, pady=4)
        Entry(frm, textvariable=txt).pack(side="left", fill="x", expand=True)
        tk.Checkbutton(frm, text="Vazio", variable=vaz).pack(side="left")

    # colunas de preview
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

    # condição AND/OR
    Label(mid, text="Condição:").pack(pady=(10, 0))
    Radiobutton(mid, text="Ambos (AND)",   variable=cond, value="and").pack(anchor="w", padx=20)
    Radiobutton(mid, text="Um ou outro (OR)", variable=cond, value="or").pack(anchor="w", padx=20)

    # botões OK/Cancelar
    Button(bot, text="OK",      width=8, command=lambda: _close(True)).pack(side="left", padx=6)
    Button(bot, text="Cancelar", width=8, command=lambda: _close(False)).pack(side="left", padx=6)

    # previews ao vivo (LivePreview)
    preview1 = LivePreview(
        canvas1,
        lambda: (coords1['x'], coords1['y'],
                 coords1['x'] + coords1['w'], coords1['y'] + coords1['h'])
                 if coords1['w'] else None,
        interval=0.30
    )
    preview2 = LivePreview(
        canvas2,
        lambda: (coords2['x'], coords2['y'],
                 coords2['x'] + coords2['w'], coords2['y'] + coords2['h'])
                 if coords2['w'] else None,
        interval=0.30
    )

    # seleção de áreas
    def _select(coords, lbl, cvs, tag, job, color):
        win.withdraw()
        area = select_area(outline=color)
        win.deiconify()
        if area is None:
            return
        x1, y1, x2, y2 = area
        coords.update({'x': x1, 'y': y1, 'w': x2 - x1, 'h': y2 - y1})
        lbl.config(text=f"x={coords['x']} y={coords['y']} "
                        f"w={coords['w']} h={coords['h']}")
        if tag == "prev1":
            preview1.start()
        else:
            preview2.start()

    btn1.configure(command=lambda: _select(coords1, lbl1, canvas1, "prev1", None, "red"))
    btn2.configure(command=lambda: _select(coords2, lbl2, canvas2, "prev2", None, "yellow"))
    # teste
    def _test():
        if coords1['w']==0 or coords2['w']==0:
            messagebox.showwarning("Áreas", "Defina as duas áreas."); return
        t1 = pytesseract.image_to_string(ImageGrab.grab(bbox=(coords1['x'],coords1['y'],coords1['x']+coords1['w'],coords1['y']+coords1['h']))).strip()
        t2 = pytesseract.image_to_string(ImageGrab.grab(bbox=(coords2['x'],coords2['y'],coords2['x']+coords2['w'],coords2['y']+coords2['h']))).strip()
        messagebox.showinfo("OCR Duplo", f"Área 1:\n{t1 or '[vazio]'}\n\nÁrea 2:\n{t2 or '[vazio]'}")

    Button(mid, text="Testar OCR", command=_test).pack(pady=6)

    # fechar e salvar
    def _close(save: bool):
        preview1.stop(); preview2.stop()
        if not save: win.destroy(); return
        if coords1['w']==0 or coords2['w']==0:
            messagebox.showerror("Erro", "Defina ambas as áreas."); return
        ac = {
            "type":   "ocr_duplo",
            **{"x1":coords1['x'],"y1":coords1['y'],"w1":coords1['w'],"h1":coords1['h']},
            **{"x2":coords2['x'],"y2":coords2['y'],"w2":coords2['w'],"h2":coords2['h']},
            "text1": txt1.get(),
            "text2": txt2.get(),
            "condicao": cond.get(),
            "vazio1":  vazio1.get(),
            "vazio2":  vazio2.get()
        }
        nome = name_var.get().strip()
        if nome: ac["name"] = nome
        actions.append(ac)
        if callable(atualizar): atualizar()
        win.destroy()

    # prévias iniciais
    if coords1['w']>0:
        lbl1.config(text=f"x={coords1['x']} y={coords1['y']} w={coords1['w']} h={coords1['h']}")
        preview1.start()
    if coords2['w']>0:
        lbl2.config(text=f"x={coords2['x']} y={coords2['y']} w={coords2['w']} h={coords2['h']}")
        preview2.start()

    # centralizar, bloquear resize, foco e atalhos
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
