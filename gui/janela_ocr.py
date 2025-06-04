import tkinter as tk
import tkinter as tk
from tkinter import Toplevel, StringVar, BooleanVar, Label, Entry, Button, Canvas, Checkbutton
from core import show_info, show_warning, show_error
from PIL import ImageGrab
import pytesseract
from utils.area_select import select_area
from utils.live_preview import LivePreview

# # ─── Definição dinâmica do caminho do Tesseract ───────────────
# import sys
# if getattr(sys, "frozen", False):
#     # Quando empacotado pelo PyInstaller, tesseract.exe ficará em _MEIPASS
#     base_dir = sys._MEIPASS
# else:
#     # Em modo script, fica ao lado deste .py
#     base_dir = os.path.dirname(__file__)

# # Ajusta o comando para usar o executável incluído no pacote
# pytesseract.pytesseract.tesseract_cmd = os.path.join(base_dir, "tesseract.exe")
# # ────────────────────────────────────────────────────────────

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

    preview = LivePreview(
        canvas_prev,
        lambda: (coords['x'], coords['y'],
                 coords['x']+coords['w'], coords['y']+coords['h'])
                 if coords['w'] else None,
        interval=0.30
    )

    _start = preview.start
    _stop  = preview.stop

    # --- Seleção de área -------------------------------------------
        # --- Seleção de área -------------------------------------------
    def selecionar_area():
        win.withdraw()
        area = select_area()
        win.deiconify()
        if area is None:
            return
        x1, y1, x2, y2 = area
        coords.update({'x': x1, 'y': y1, 'w': x2 - x1, 'h': y2 - y1})
        lbl_coord.config(text=f"Área: x={coords['x']} y={coords['y']} "
                              f"w={coords['w']} h={coords['h']}")
        _start()

    btn_sel.configure(command=selecionar_area)

    # --- Teste de OCR ----------------------------------------------
    def testar():
        if coords['w'] == 0:
            show_warning('Área', 'Defina a área.'); return
        bbox = (coords['x'], coords['y'], coords['x'] + coords['w'], coords['y'] + coords['h'])
        img = ImageGrab.grab(bbox=bbox)
        text = pytesseract.image_to_string(img).strip()
        show_info('OCR Detectado', text or '[vazio]')
    btn_test.configure(command=testar)

    # --- Fechar e gravar ação --------------------------------------
    def _close(save):
        _stop()
        if not save:
            win.destroy(); return
        if coords['w'] == 0:
            show_error('Erro', 'Área deve ser definida.'); return
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
