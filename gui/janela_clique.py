from tkinter import Toplevel, IntVar, StringVar, Label, Entry, Button, Frame, Canvas
from tkinter import ttk
from PIL import ImageTk, ImageGrab, Image
import pyautogui, threading, keyboard, os, sys
from utils.area_select import select_area
from utils.live_preview import LivePreview
import tempfile, uuid
from core.executar import _ui_async
#import core.executar
#messagebox = core.executar.messagebox
import thread_safe_patch
from core import show_warning

# Utility to get base_dir for bundled resources
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(__file__)


def add_click(actions, update_list, tela, *, initial=None):
    # --- Cria janela centrada e modal ---
    janela = Toplevel(tela)
    janela.title("Adicionar Clique")
    janela.transient(tela)
    janela.grab_set()
    janela.resizable(False, False)

    _tkvars = []

    # Container de widgets
    container = Frame(janela)
    container.pack(padx=10, pady=10, fill='x')

    # --- Nome do bloco (sempre visível) ---
    Label(container, text="Nome do bloco:").pack(anchor='w')
    label_var = StringVar(value=initial.get('name','') if initial else '')
    _tkvars.append(label_var)
    Entry(container, textvariable=label_var).pack(anchor='w', fill='x', pady=(0,10))

    # --- Dropdown de Modo (combo branco) ---
    Label(container, text="Modo:").pack(anchor='w')
    # mapear código interno → texto no combo
    mode_map = {
        'Simples': 'Simples', 'fixo': 'Simples',
        'aleatorio': 'Aleatório', 'Aleatório': 'Aleatório',
        'imagem': 'Clicar em Imagem', 'Clicar em Imagem': 'Clicar em Imagem'
    }
    init_mode = initial.get('mode') if initial else 'Simples'
    modo_display = mode_map.get(init_mode, 'Simples')
    modo_var = StringVar(value=modo_display)
    _tkvars.append(modo_var)
    modos = ['Simples', 'Aleatório', 'Clicar em Imagem']
    modo_combo = ttk.Combobox(container, textvariable=modo_var, values=modos, state='readonly')
    modo_combo.pack(anchor='w', fill='x', pady=(0,10))
    # quando mudar o combo, troca de frame
    modo_var.trace_add('write', lambda *e: switch_mode())

    # --- Frames para cada modo ---
    simple_frame = Frame(container)
    random_frame = Frame(container)
    image_frame  = Frame(container)

    # placeholders para lembrar seleção ao reabrir
    img_region   = None
    
    # --- Simple Mode Widgets ---
    # Coordenadas X/Y
    Label(simple_frame, text="X:").pack(anchor='w')
    var_x = IntVar(value=initial.get('x',0) if initial else 0)
    _tkvars.append(var_x)
    entry_x = Entry(simple_frame, textvariable=var_x)
    entry_x.pack(anchor='w', fill='x')

    Label(simple_frame, text="Y:").pack(anchor='w', pady=(5,0))
    var_y = IntVar(value=initial.get('y',0) if initial else 0)
    _tkvars.append(var_y)
    entry_y = Entry(simple_frame, textvariable=var_y)
    entry_y.pack(anchor='w', fill='x', pady=(0,10))

    # Captura Manual (F2)
    status_lbl = Label(simple_frame, text="", font=("Arial",9))
    def confirm_manual(event=None):
        stop_live.set()
        x, y = var_x.get(), var_y.get()
        nova_acao = {"type":"click","x":x,"y":y}
        name = label_var.get().strip()
        if name:
            nova_acao["name"] = name
        nova_acao["mode"] = 'Simples'
        if initial is not None:
            initial.update(nova_acao)
        else:
            actions.append(nova_acao)
        update_list()
        _detach_vars()
        janela.destroy()

    # ------------------------------------------------------------------
    # CAPTURA MANUAL  (modo Simples)  —  sem threads
    # ------------------------------------------------------------------
    def monitor_mouse_manual():
        """Atualiza X/Y a cada 20 ms até o usuário pressionar F2."""
        # se a janela já foi fechada, aborta
        if not entry_x.winfo_exists():
            return

        x, y = pyautogui.position()
        var_x.set(x)
        var_y.set(y)

        # F2 captura a posição
        if keyboard.is_pressed('F2'):
            status_lbl.config(text=f"Capturado: ({x}, {y})", fg="green")
            start_btn.config(state='active')
            return        # para o loop

        # agenda a próxima leitura em 20 ms
        janela.after(20, monitor_mouse_manual)

    def start_capture_manual():
        """Inicia a captura; entra no loop via after()."""
        start_btn.config(state='disabled')
        status_lbl.config(text="Aguardando F2...", fg="red")
        status_lbl.pack(anchor='w', pady=(0,10))

        monitor_mouse_manual()          # primeira chamada

    start_btn = Button(simple_frame, text="Iniciar Captura", command=start_capture_manual)
    start_btn.pack(anchor='w', pady=(0,10))
    simple_frame.pack(fill='x')

    # --- Random Mode Widgets ---
    Label(random_frame, text="Região Selecionada:").pack(anchor='w')
    coords_lbl = Label(random_frame, text="Nenhuma região", font=("Arial",9))
    coords_lbl.pack(anchor='w', pady=(0,5))

    live_canvas = Canvas(random_frame, width=200, height=100, bg='black')
    live_canvas.pack(anchor='w', pady=(0,10))

    region = None
    stop_live = threading.Event()
    preview = LivePreview(live_canvas, lambda: region)

    def select_region():
        nonlocal region
        stop_live.set()

        # ---- prepara / solta modalidade ----
        modal = janela.grab_current() is janela
        if modal:
            janela.grab_release()

        janela.withdraw()                # <-- esconde a janela
        region = select_area(parent=janela)   # overlay agora em foco
        janela.deiconify()               # mostra de novo

        if modal:                        # devolve modalidade
            janela.grab_set()

        if region:
            x1, y1, x2, y2 = region
            coords_lbl.config(text=f"({x1},{y1})-({x2},{y2})")
        start_live_preview()

    def start_live_preview():
        preview.start()
    
    def stop_live_preview():
        preview.stop()

    Button(random_frame, text="Selecionar Região", command=select_region).pack(anchor='w', pady=(0,10))

    # --- Image Mode Widgets ---
    Label(image_frame, text="Template (imagem):").pack(anchor='w')
    img_canvas = Canvas(image_frame, width=200, height=100, bg='gray')
    img_canvas.pack(anchor='w', pady=(0,10))
    # se reabrindo com initial, carrega template salvo
    if initial and init_mode == 'imagem':
        path = initial.get('template_path')
        if path and os.path.exists(path):
            pil = Image.open(path)
            img_template = pil
            tkim = ImageTk.PhotoImage(pil)
            img_canvas.create_image(0,0,anchor='nw', image=tkim)
            img_canvas.image = tkim
    def select_template():
        nonlocal img_template
        # seleciona área da tela como template
        bbox = select_area(parent=janela)
        if not bbox:
            return
        x1, y1, x2, y2 = bbox
        # captura screenshot da região
        pil_img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        img_template = pil_img
        tk_img = ImageTk.PhotoImage(pil_img)
        img_canvas.create_image(0,0,anchor='nw', image=tk_img)
        img_canvas.image = tk_img
    Button(image_frame, text="Selecionar Imagem", command=select_template).pack(anchor='w', pady=(0,10))

    Label(image_frame, text="Região de busca (live):").pack(anchor='w')
    reg_canvas = Canvas(image_frame, width=200, height=100, bg='gray')
    reg_canvas.pack(anchor='w', pady=(0,10))
    # placeholders para região e preview
    img_region = None
    img_preview = None
    # se reabrindo com modo 'imagem', restaura região e inicia live preview
    if initial and init_mode == 'imagem':
        x, y = initial.get('x',0), initial.get('y',0)
        w, h = initial.get('w',0), initial.get('h',0)
        if w > 0 and h > 0:
            img_region = (x, y, x+w, y+h)
            img_preview = LivePreview(reg_canvas, lambda: img_region)
            img_preview.start()
    def select_region_live():
        nonlocal img_region, img_preview
        # seleciona área da tela para busca
        region = select_area(parent=janela)
        if not region:
            return
        img_region = region
        if img_preview:
            img_preview.stop()
        img_preview = LivePreview(reg_canvas, lambda: img_region)
        img_preview.start()
    Button(image_frame, text="Selecionar Região", command=select_region_live).pack(anchor='w', pady=(0,10))

    # --- Atualiza visibilidade de frames conforme modo ---
    def switch_mode(*args):
        mode = modo_var.get()
        # esconde todos os frames
        simple_frame.forget()
        random_frame.forget()
        image_frame.forget()
        # mostra apenas o frame ativo
        if mode == 'Simples':
            simple_frame.pack(fill='x')
        elif mode == 'Aleatório':
            random_frame.pack(fill='x')
        else:  # 'Clicar em Imagem'
            image_frame.pack(fill='x')
    modo_var.trace_add('write', switch_mode)
    switch_mode()

    # --- Restaura seleção anterior em Aleatório ---
    if initial and initial.get('mode') == 'Aleatório':
        # monta região salva
        x1 = initial.get('x', 0)
        y1 = initial.get('y', 0)
        w  = initial.get('w', 0)
        h  = initial.get('h', 0)
        region = (x1, y1, x1 + w, y1 + h)
        # atualiza label e pré‑visualização
        coords_lbl.config(text=f"({x1},{y1})-({x1+w},{y1+h})")
        start_live_preview()

    # --- Botões OK e Cancelar ---
    def _detach_vars():
        # ➋ quebra o vínculo Tcl → evita RuntimeError no __del__
        for v in _tkvars:
            v._tk = None

    def on_cancel():
        stop_live.set()
        stop_live_preview() 
        _detach_vars()
        janela.destroy()
    btn_frame = Frame(janela)
    btn_frame.pack(fill='x', padx=10, pady=(0,10))
    
    # Função de confirmação para o modo Aleatório
    def confirm_random(event=None):
        stop_live.set()
        stop_live_preview()
        if not region:
            thread_safe_patch._ui_async(show_warning, "Atenção", "Selecione antes a região.")
            return
        x1, y1, x2, y2 = region
        w, h = x2 - x1, y2 - y1
        nova_acao = {
            "type": "click",
            "mode": "aleatorio",
            "x": x1, "y": y1,
            "w": w, "h": h,
        }
        name = label_var.get().strip()
        if name:
            nova_acao["name"] = name
        if initial is not None:
            initial.update(nova_acao)
        else:
            actions.append(nova_acao)
        update_list()
        _detach_vars()
        janela.destroy()

    # --- Função de confirmação para o modo “Clicar em Imagem” ---
    def confirm_image(event=None):
        # interrompe qualquer preview ativo
        stop_live.set()
        try:
            stop_live_preview()
        except NameError:
            pass
        # valida se template e região foram escolhidos
        if img_template is None or img_region is None:
            _ui_async(show_warning, "Atenção", "Selecione antes o template e a região de busca.")
            return
        # salva o template num arquivo temporário
        tmpdir = tempfile.gettempdir()
        fname = f"template_{uuid.uuid4().hex}.png"
        template_path = os.path.join(tmpdir, fname)
        img_template.save(template_path)

        x1, y1, x2, y2 = img_region
        w, h = x2 - x1, y2 - y1
        nova_acao = {
            "type":          "click",
            "mode":          "imagem",
            "template_path": template_path,
            "x":             x1,
            "y":             y1,
            "w":             w,
            "h":             h,
        }
        name = label_var.get().strip()
        if name:
            nova_acao["name"] = name
        if initial is not None:
            initial.update(nova_acao)
        else:
            actions.append(nova_acao)
        update_list()
        _detach_vars()
        janela.destroy()

    # mostra o frame correto logo na abertura
    switch_mode()
    # Substitui o handler do OK conforme o modo selecionado
    def on_ok(event=None):
        modo = modo_var.get()
        if modo == 'Simples':
            confirm_manual()
        elif modo == 'Aleatório':
            confirm_random()
        else:  # 'Clicar em Imagem'
            confirm_image()

    Button(btn_frame, text="Cancelar", width=10, command=on_cancel).pack(side='right', padx=(5,0))
    Button(btn_frame, text="OK",       width=10, command=on_ok).pack(side='right')

    # --- Global hotkeys ---
    janela.bind("<Return>", lambda e: on_ok() or "break")
    # captura ESC no overlay e impede que chegue à janela principal
    def _on_esc(event):
        on_cancel()
        return "break"
    janela.bind("<Escape>", _on_esc)

    # --- Centralizar janela ---
    def _recentralizar():
        janela.update_idletasks()
        w = janela.winfo_width()
        h = janela.winfo_height()
        rx = tela.winfo_rootx()
        ry = tela.winfo_rooty()
        rw = tela.winfo_width()
        rh = tela.winfo_height()
        x = rx + (rw - w)//2
        y = ry + (rh - h)//2
        janela.geometry(f"+{x}+{y}")
    _recentralizar()
    janela.focus_force()
