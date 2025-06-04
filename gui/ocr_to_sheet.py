import tkinter as tk
from tkinter import Toplevel, Canvas
from core import show_error, show_warning
from tkinter import ttk
from PIL import Image, ImageGrab, ImageTk
import pytesseract
from utils.google_sheet_util import get_sheet_tabs
from core.config_manager import ConfigManager
from utils.area_select import pick_area
from utils.live_preview import LivePreview


def add_ocr_to_sheet(actions=None, update_list=None, tela=None, *, initial=None):
    # — Cria janela modal —
    win = Toplevel(tela)
    win.title("Capturar Texto → Google Sheets")
    win.transient(tela)
    win.resizable(False, False)
    win.grab_set()
    win.columnconfigure(0, weight=1)

    # — Funções de mensagens modais seguras —
    def safe_error(title, msg):
        try:
            win.wm_attributes('-disabled', True)
        except Exception:
            pass
        show_error(title, msg, parent=win)
        try:
            win.wm_attributes('-disabled', False)
        except Exception:
            pass

    def safe_warning(title, msg):
        try:
            win.wm_attributes('-disabled', True)
        except Exception:
            pass
        show_warning(title, msg, parent=win)
        try:
            win.wm_attributes('-disabled', False)
        except Exception:
            pass

    # — Constantes e estado —
    BASE_W, BASE_H = 220, 120
    coords = {'x':0, 'y':0, 'w':0, 'h':0}
    thumbs = {}
    scale_var = tk.IntVar(value=1)
    scale_val = 1
    coord_var = tk.StringVar(value="(não selecionada)")

    # — Carrega configurações iniciais —
    cfg = ConfigManager.load()
    sheets_cfg = cfg.get("google_sheets", [])
    sheet_names = [s.get("name", "") for s in sheets_cfg]
    default_sheet = initial.get("sheet") if isinstance(initial, dict) and "sheet" in initial else (sheet_names[0] if sheet_names else "")
    default_column = initial.get("column") if isinstance(initial, dict) and "column" in initial else ""
    default_tab = initial.get("tab") if isinstance(initial, dict) and "tab" in initial else ""

    # Mapeamento title -> id para abas
    tab_map = {}

    # — Helpers internos —
    def _display(img: Image.Image):
        ph = ImageTk.PhotoImage(img)
        canvas_prev.delete('prev')
        if scale_var.get() == 1:
            thumb = img.copy()
            thumb.thumbnail((BASE_W, BASE_H), Image.LANCZOS)
            ph2 = ImageTk.PhotoImage(thumb)
            canvas_prev.config(width=BASE_W, height=BASE_H)
            canvas_prev.create_image(BASE_W//2, BASE_H//2, image=ph2, tags='prev', anchor='center')
            thumbs['thumb'] = ph2
        else:
            canvas_prev.config(width=img.width, height=img.height)
            canvas_prev.create_image(0, 0, image=ph, tags='prev', anchor='nw')
            thumbs['full'] = ph

    def _start_refresh():
        preview.start()

    def _stop_refresh():
        preview.stop()

    def on_scale_change(*_):
        nonlocal scale_val
        scale_val = int(scale_var.get())      # ← captura na UI-thread
        _stop_refresh()
        _start_refresh()
        win.update_idletasks()
        # ------------- centraliza na janela principal -------------
        rw, rh = win.winfo_reqwidth(), win.winfo_reqheight()
        pw, ph = tela.winfo_width(),    tela.winfo_height()
        px, py = tela.winfo_rootx(),    tela.winfo_rooty()
        win.geometry(f"{rw}x{rh}+{px + (pw - rw)//2}+{py + (ph - rh)//2}")

    def selecionar_area():
        pick_area(parent=win,
                  coords_dict=coords,
                  text_target=coord_var,
                  after=_start_refresh)

    def on_test():
        if coords['w']==0:
            safe_warning("Teste OCR", "Selecione primeiro a área.")
            return
        snap = ImageGrab.grab(bbox=(coords['x'], coords['y'], coords['x']+coords['w'], coords['y']+coords['h']))
        if scale_var.get() > 1:
            snap = snap.resize((snap.width*scale_var.get(), snap.height*scale_var.get()), Image.LANCZOS)
        texto = pytesseract.image_to_string(snap, lang='por').strip()
        safe_warning("Teste OCR", f"Texto extraído:\n\n{texto}")

    def on_ok():
        _stop_refresh()
        if coords['w']==0:
            safe_error("Erro", "Selecione uma área primeiro.")
            return
        if not column_var.get().strip():
            safe_error("Erro", "Informe a coluna para popular na planilha.")
            return
        if not tab_var.get().strip():
            safe_error("Erro", "Selecione a aba da planilha.")
            return

        # 1) Faz o snapshot da área selecionada
        bbox = (coords['x'], coords['y'],
                coords['x'] + coords['w'], coords['y'] + coords['h'])
        snap = ImageGrab.grab(bbox=bbox)
        # 2) Aplica zoom, se houver
        if scale_var.get() > 1:
            snap = snap.resize(
                (snap.width * scale_var.get(),
                 snap.height * scale_var.get()),
                Image.LANCZOS
            )
        # 3) Executa OCR
        texto = pytesseract.image_to_string(snap, lang='por').strip()

        tab_id = tab_map.get(tab_var.get().strip())
        # 4) Monta a ação incluindo o texto extraído
        ac = {
            "type": "text_to_sheet",
            "x": coords['x'],
            "y": coords['y'],
            "w": coords['w'],
            "h": coords['h'],
            "scale": scale_var.get(),
            "sheet": sheet_var.get(),
            "column": column_var.get().strip(),
            "tab_id":  tab_id,
            "text":    texto           # ← agora temos o campo esperado
        }
        actions.append(ac)
        update_list()
        win.destroy()

    def on_cancel():
        _stop_refresh()
        win.destroy()

    # — Layout —
    cfg_frame = ttk.Labelframe(win, text="Configurações")
    cfg_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15,5))
    cfg_frame.columnconfigure(1, weight=1)

    ttk.Label(cfg_frame, text="Área:").grid(row=0, column=0, sticky="w", pady=2)
    ttk.Label(cfg_frame, textvariable=coord_var).grid(row=0, column=1, sticky="w", pady=2)

    ttk.Label(cfg_frame, text="Zoom:").grid(row=1, column=0, sticky="w", pady=2)
    zoom_spin = ttk.Spinbox(cfg_frame, from_=1, to=3, textvariable=scale_var,
                             width=3, wrap=True, justify="center", state="readonly")
    zoom_spin.grid(row=1, column=1, sticky="w", pady=2)
    scale_var.trace_add('write', on_scale_change)

    ttk.Label(cfg_frame, text="Planilha:").grid(row=2, column=0, sticky="w", pady=2)
    sheet_var = tk.StringVar(value=default_sheet)
    sheet_combo = ttk.Combobox(cfg_frame, textvariable=sheet_var, values=sheet_names, state="readonly")
    sheet_combo.grid(row=2, column=1, sticky="ew", pady=2)

    ttk.Label(cfg_frame, text="Coluna:").grid(row=3, column=0, sticky="w", pady=2)
    column_var = tk.StringVar(value=default_column)
    column_entry = ttk.Entry(cfg_frame, textvariable=column_var)
    column_entry.grid(row=3, column=1, sticky="ew", pady=2)

    ttk.Label(cfg_frame, text="Aba:").grid(row=4, column=0, sticky="w", pady=2)
    tab_var = tk.StringVar(value="")
    tab_combo = ttk.Combobox(cfg_frame, textvariable=tab_var, state="readonly")
    tab_combo.grid(row=4, column=1, sticky="ew", pady=2)

    def update_tabs(*_):
        try:
            sheet_combo.event_generate('<Escape>')
        except Exception:
            pass
        try:
            tabs_info = get_sheet_tabs(sheet_var.get())
        except Exception as e:
            from gspread.exceptions import SpreadsheetNotFound
            if isinstance(e, SpreadsheetNotFound):
                safe_error("Erro", f"Planilha '{sheet_var.get()}' não encontrada ou sem acesso.")
            else:
                safe_error("Erro inesperado ao listar abas", str(e))
            tabs_info = []
        tab_map.clear()
        titles = []
        for info in tabs_info:
            title = info.get('title')
            tid = info.get('id')
            tab_map[title] = tid
            titles.append(title)
        tab_combo['values'] = titles
        if default_tab in titles:
            tab_combo.set(default_tab)
        else:
            tab_combo.set(titles[0] if titles else "")
    sheet_var.trace_add('write', update_tabs)
    update_tabs()

    prev = ttk.Labelframe(win, text="Visualização")
    prev.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
    canvas_prev = Canvas(prev, width=BASE_W, height=BASE_H,
                         highlightthickness=1, highlightbackground="#999")
    canvas_prev.grid(row=0, column=0, padx=10, pady=10)

    # agora que canvas_prev e scale_var existem, criamos o preview
    preview = LivePreview(
        canvas_prev,
        lambda: (coords['x'], coords['y'],
                 coords['x']+coords['w'], coords['y']+coords['h'])
                 if coords['w'] else None,
        interval=0.30,
        transform=lambda im: im.resize(
            (im.width*scale_val, im.height*scale_val), Image.LANCZOS)
                 if scale_val > 1 else im
    )

    btns = ttk.Frame(win)
    btns.grid(row=2, column=0, sticky="e", padx=15, pady=(5,15))
    ttk.Button(btns, text="Selecionar Área", command=selecionar_area).grid(row=0, column=0, padx=(0,5))
    ttk.Button(btns, text="Testar OCR", command=on_test).grid(row=0, column=1, padx=(0,5))
    ttk.Button(btns, text="Cancelar", command=on_cancel).grid(row=0, column=2, padx=(0,5))
    ttk.Button(btns, text="OK", command=on_ok).grid(row=0, column=3)

    if initial and isinstance(initial, dict):
        coords.update({'x': initial.get('x',0), 'y': initial.get('y',0), 'w': initial.get('w',0), 'h': initial.get('h',0)})
        scale_var.set(initial.get('scale',1))
        coord_var.set(f"x={coords['x']} y={coords['y']} w={coords['w']} h={coords['h']}")
        win.update_idletasks()
        _start_refresh()
        rw, rh = win.winfo_reqwidth(), win.winfo_reqheight()
        pw, ph = tela.winfo_width(),    tela.winfo_height()
        px, py = tela.winfo_rootx(),    tela.winfo_rooty()
        win.geometry(f"{rw}x{rh}+{px + (pw - rw)//2}+{py + (ph - rh)//2}")
    else:
        win.update_idletasks()
        rw, rh = win.winfo_reqwidth(), win.winfo_reqheight()
        pw, ph = tela.winfo_width(),    tela.winfo_height()
        px, py = tela.winfo_rootx(),    tela.winfo_rooty()
        win.geometry(f"{rw}x{rh}+{px + (pw - rw)//2}+{py + (ph - rh)//2}")

    win.deiconify()
    win.focus_force()
    win.bind('<Return>', lambda e: on_ok() or "break")
    # captura ESC no overlay e impede que chegue à janela principal
    def _on_esc(event):
        on_cancel()
        return "break"
    win.bind('<Escape>', _on_esc)
    win.wait_window()